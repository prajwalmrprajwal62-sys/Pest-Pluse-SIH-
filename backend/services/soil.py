"""
PestPulse — Soil Intelligence Service (SoilGrids ISRIC adapter)
Fetches soil properties from the free SoilGrids REST API v2.0.
No API key required.

Properties fetched:
  phh2o  - soil pH in water
  soc    - soil organic carbon (g/kg) → fertility proxy
  nitrogen - total nitrogen (cg/kg)
  clay   - clay fraction %
  sand   - sand fraction %
  bdod   - bulk density (cg/cm³) → compaction
"""
import time
import httpx

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
CACHE: dict = {}
CACHE_TTL = 3600  # 1 hour — soil doesn't change fast

FIXTURE_SOIL = {
    "source":        "FIXTURE",
    "freshness":     "DEMO",
    "phh2o":         6.1,
    "soc":           12.4,
    "nitrogen":      110,
    "clay_pct":      28,
    "sand_pct":      35,
    "bulk_density":  1.35,
    "warnings":      ["Soil data unavailable — using demo fixture for Bengaluru region."],
}

# ── Soil type classifier ──────────────────────────────────────────────────────
def classify_soil(clay: float, sand: float) -> str:
    silt = max(0, 100 - clay - sand)
    if clay >= 40:                          return "heavy_clay"
    if clay >= 28 and silt >= 15:          return "clay_loam"
    if sand >= 70:                         return "sandy"
    if sand >= 50 and clay < 18:          return "sandy_loam"
    if silt >= 50:                         return "silty_loam"
    return "loam"

SOIL_LABELS = {
    "heavy_clay": {"en": "Heavy Clay",   "kn": "ಭಾರ ಜೇಡಿ ಮಣ್ಣು", "hi": "भारी चिकनी मिट्टी"},
    "clay_loam":  {"en": "Clay Loam",    "kn": "ಜೇಡಿ-ಲೋಮ್",      "hi": "चिकनी दोमट"},
    "sandy":      {"en": "Sandy",        "kn": "ಮರಳು ಮಣ್ಣು",      "hi": "बलुई मिट्टी"},
    "sandy_loam": {"en": "Sandy Loam",   "kn": "ಮರಳು-ಲೋಮ್",      "hi": "बलुई दोमट"},
    "silty_loam": {"en": "Silty Loam",   "kn": "ಹೂಳು-ಲೋಮ್",      "hi": "गाद दोमट"},
    "loam":       {"en": "Loam",         "kn": "ಲೋಮ್ ಮಣ್ಣು",     "hi": "दोमट मिट्टी"},
}

# ── Fertility scorer (0–100) ──────────────────────────────────────────────────
def score_fertility(ph: float, soc: float, nitrogen: float) -> int:
    ph_score = max(0, 100 - abs(ph - 6.5) * 25)   # ideal pH 6.5
    soc_score = min(100, soc * 4)                   # 25 g/kg = perfect
    n_score   = min(100, nitrogen / 2)              # 200 cg/kg = perfect
    return int((ph_score * 0.3 + soc_score * 0.5 + n_score * 0.2))

def fertility_label(score: int) -> dict:
    if score >= 75: return {"en": "High",    "kn": "ಹೆಚ್ಚು",   "hi": "उच्च",   "color": "#00e676"}
    if score >= 45: return {"en": "Medium",  "kn": "ಮಧ್ಯಮ",    "hi": "मध्यम",  "color": "#f59e0b"}
    return            {"en": "Low",      "kn": "ಕಡಿಮೆ",    "hi": "कम",     "color": "#ef4444"}

# ── Crop recommendation engine ────────────────────────────────────────────────
# Based on ICAR Karnataka crop-soil-pH compatibility matrix
def recommend_crops(ph: float, soil_type: str, temp_c: float = 27.0, precip_mm: float = 0.0) -> list:
    recs = []

    # pH-based suitability ranges (ICAR data)
    # Format: (name_en, name_kn, name_hi, min_ph, max_ph, soil_types, icon)
    CROP_RULES = [
        ("Tomato",      "ಟೊಮೇಟೊ",        "टमाटर",         5.5, 7.0, ["loam","clay_loam","sandy_loam"], "🍅"),
        ("Potato",      "ಆಲೂಗಡ್ಡೆ",       "आलू",           5.0, 6.5, ["loam","sandy_loam","sandy"],      "🥔"),
        ("Ragi",        "ರಾಗಿ",           "रागी",           4.5, 8.0, ["loam","clay_loam","sandy_loam"], "🌾"),
        ("Jowar",       "ಜೋಳ",            "ज्वार",          5.5, 8.5, ["loam","clay_loam","heavy_clay"], "🌾"),
        ("Cotton",      "ಹತ್ತಿ",           "कपास",           6.0, 8.0, ["heavy_clay","clay_loam"],        "🌿"),
        ("Maize",       "ಮೆಕ್ಕೆಜೋಳ",       "मक्का",          5.5, 7.5, ["loam","sandy_loam","clay_loam"], "🌽"),
        ("Groundnut",   "ಕಡಲೆ",           "मूंगफली",        5.5, 7.0, ["sandy_loam","sandy","loam"],      "🥜"),
        ("Sunflower",   "ಸೂರ್ಯಕಾಂತಿ",      "सूरजमुखी",       5.7, 8.0, ["loam","clay_loam"],               "🌻"),
        ("Paddy/Rice",  "ಭತ್ತ",            "धान",            5.0, 7.0, ["heavy_clay","clay_loam"],         "🌾"),
        ("Soybean",     "ಸೋಯಾಬೀನ್",        "सोयाबीन",        6.0, 7.5, ["loam","clay_loam"],               "🫘"),
        ("Onion",       "ಈರುಳ್ಳಿ",         "प्याज़",          6.0, 7.5, ["loam","sandy_loam"],              "🧅"),
        ("Chilli",      "ಮೆಣಸಿನಕಾಯಿ",      "मिर्च",          5.5, 7.0, ["loam","sandy_loam","clay_loam"], "🌶️"),
        ("Grape",       "ದ್ರಾಕ್ಷಿ",         "अंगूर",           6.0, 7.5, ["sandy_loam","loam"],              "🍇"),
        ("Sugarcane",   "ಕಬ್ಬು",           "गन्ना",          6.0, 8.0, ["loam","clay_loam"],               "🎋"),
    ]

    for (en, kn, hi, ph_min, ph_max, soils, icon) in CROP_RULES:
        ph_ok   = ph_min <= ph <= ph_max
        soil_ok = soil_type in soils
        if ph_ok and soil_ok:
            score = 100
            if not ph_ok:  score -= 30
            # Temperature bonus for Karnataka
            if 20 <= temp_c <= 35: score = min(100, score + 5)
            recs.append({
                "name": {"en": en, "kn": kn, "hi": hi},
                "icon": icon,
                "suitability": score,
                "ph_range": f"{ph_min}–{ph_max}",
            })

    # Sort by suitability, return top 6
    recs.sort(key=lambda x: x["suitability"], reverse=True)
    return recs[:6]

# ── Disease risk heuristics from soil + weather ───────────────────────────────
def soil_disease_risks(ph: float, clay_pct: float, temp_c: float, humidity_pct: float, precip_mm: float) -> list:
    risks = []
    if humidity_pct > 70 and temp_c > 22:
        risks.append({"disease": "Late Blight", "risk": "HIGH",   "color": "#ef4444",
                       "reason": f"High humidity ({humidity_pct}%) + warm temps favour Phytophthora spread"})
    if precip_mm > 5:
        risks.append({"disease": "Leaf Spot diseases", "risk": "MEDIUM", "color": "#f59e0b",
                       "reason": "Recent rainfall increases fungal spore germination"})
    if clay_pct > 40:
        risks.append({"disease": "Root Rot (Pythium)", "risk": "MEDIUM", "color": "#f59e0b",
                       "reason": f"Heavy clay ({clay_pct:.0f}%) traps water — poor drainage favours root pathogens"})
    if ph < 5.5:
        risks.append({"disease": "Fusarium Wilt", "risk": "MEDIUM", "color": "#f59e0b",
                       "reason": f"Acidic soil (pH {ph:.1f}) weakens plant immunity and favours Fusarium"})
    if ph > 7.5:
        risks.append({"disease": "Chlorosis / Nutrient lockout", "risk": "LOW", "color": "#6366f1",
                       "reason": f"Alkaline soil (pH {ph:.1f}) locks out Fe/Mn, causing yellowing"})
    if not risks:
        risks.append({"disease": "No major risk", "risk": "LOW", "color": "#00e676",
                       "reason": "Soil conditions look favourable. Keep monitoring."})
    return risks


# ── Main fetch function ───────────────────────────────────────────────────────
async def get_soil_data(lat: float, lon: float, temp_c: float = 27.0,
                        humidity_pct: float = 65.0, precip_mm: float = 0.0) -> dict:
    cache_key = f"{lat:.3f},{lon:.3f}"
    now = time.time()

    if cache_key in CACHE and (now - CACHE[cache_key]["ts"]) < CACHE_TTL:
        return _enrich(CACHE[cache_key]["data"], temp_c, humidity_pct, precip_mm)

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(SOILGRIDS_URL, params={
                "lat":      lat,
                "lon":      lon,
                "property": ["phh2o", "soc", "nitrogen", "clay", "sand", "bdod"],
                "depth":    "0-5cm",
                "value":    "mean",
            })
            r.raise_for_status()
            raw = r.json()

        props = {}
        for layer in raw.get("properties", {}).get("layers", []):
            name = layer.get("name")
            val  = layer.get("depths", [{}])[0].get("values", {}).get("mean")
            if val is not None:
                props[name] = val

        # SoilGrids returns scaled values — convert to SI
        ph       = (props.get("phh2o", 61))  / 10.0    # stored as pH*10
        soc      = (props.get("soc",   124)) / 10.0    # dg/kg → g/kg
        nitrogen = props.get("nitrogen", 110)           # cg/kg
        clay     = (props.get("clay",   280)) / 10.0   # g/kg → %
        sand     = (props.get("sand",   350)) / 10.0
        bdod     = (props.get("bdod",  1350)) / 100.0  # cg/cm³ → g/cm³

        data = {
            "source":       "SOILGRIDS",
            "freshness":    "LIVE",
            "phh2o":        round(ph, 2),
            "soc":          round(soc, 1),
            "nitrogen":     round(nitrogen, 1),
            "clay_pct":     round(clay, 1),
            "sand_pct":     round(sand, 1),
            "bulk_density": round(bdod, 2),
            "warnings":     [],
        }
        CACHE[cache_key] = {"data": data, "ts": now}
        return _enrich(data, temp_c, humidity_pct, precip_mm)

    except Exception as e:
        print(f"[Soil] SoilGrids failed: {e} — using fixture")
        fixture = {**FIXTURE_SOIL, "warnings": [f"Soil fetch failed: {e}"]}
        return _enrich(fixture, temp_c, humidity_pct, precip_mm)


def _enrich(base: dict, temp_c: float, humidity_pct: float, precip_mm: float) -> dict:
    """Add derived fields: soil type, fertility, crops, disease risks."""
    ph       = base.get("phh2o", 6.1)
    soc      = base.get("soc", 12.4)
    nitrogen = base.get("nitrogen", 110)
    clay     = base.get("clay_pct", 28)
    sand     = base.get("sand_pct", 35)

    soil_type = classify_soil(clay, sand)
    fert_score = score_fertility(ph, soc, nitrogen)

    return {
        **base,
        "soil_type":        soil_type,
        "soil_type_label":  SOIL_LABELS.get(soil_type, SOIL_LABELS["loam"]),
        "fertility_score":  fert_score,
        "fertility_label":  fertility_label(fert_score),
        "recommended_crops": recommend_crops(ph, soil_type, temp_c, precip_mm),
        "disease_risks":    soil_disease_risks(ph, clay, temp_c, humidity_pct, precip_mm),
        "water_retention":  "High" if clay > 35 else ("Low" if sand > 60 else "Medium"),
    }

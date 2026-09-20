"""
PestPulse — AgriTools static data tables
ICAR Karnataka recommended N/P/K, pesticide dosages, and farming economics.
All values from publicly available ICAR / KAU / CIB&RC research tables.
No API key needed — pure lookup.
"""

# ── N/P/K recommendations (kg/ha) per crop per growth stage ──────────────────
# Source: ICAR, UAS Dharwad Karnataka Package of Practices 2023
NPK = {
    "tomato": {
        "seedling":    {"N": 30,  "P": 60,  "K": 50},
        "vegetative":  {"N": 60,  "P": 30,  "K": 50},
        "flowering":   {"N": 30,  "P": 30,  "K": 50},
        "fruiting":    {"N": 30,  "P": 0,   "K": 50},
        "maturity":    {"N": 0,   "P": 0,   "K": 25},
    },
    "potato": {
        "seedling":    {"N": 50,  "P": 100, "K": 80},
        "vegetative":  {"N": 80,  "P": 50,  "K": 80},
        "flowering":   {"N": 40,  "P": 25,  "K": 60},
        "fruiting":    {"N": 20,  "P": 0,   "K": 60},
        "maturity":    {"N": 0,   "P": 0,   "K": 30},
    },
    "corn_maize": {
        "seedling":    {"N": 40,  "P": 75,  "K": 40},
        "vegetative":  {"N": 80,  "P": 40,  "K": 40},
        "flowering":   {"N": 40,  "P": 0,   "K": 40},
        "fruiting":    {"N": 20,  "P": 0,   "K": 40},
        "maturity":    {"N": 0,   "P": 0,   "K": 0},
    },
    "grape": {
        "seedling":    {"N": 40,  "P": 60,  "K": 40},
        "vegetative":  {"N": 80,  "P": 30,  "K": 80},
        "flowering":   {"N": 40,  "P": 30,  "K": 80},
        "fruiting":    {"N": 20,  "P": 0,   "K": 80},
        "maturity":    {"N": 0,   "P": 0,   "K": 40},
    },
    "bell_pepper": {
        "seedling":    {"N": 30,  "P": 60,  "K": 50},
        "vegetative":  {"N": 60,  "P": 30,  "K": 50},
        "flowering":   {"N": 30,  "P": 30,  "K": 50},
        "fruiting":    {"N": 30,  "P": 0,   "K": 50},
        "maturity":    {"N": 0,   "P": 0,   "K": 25},
    },
    "strawberry": {
        "seedling":    {"N": 20,  "P": 40,  "K": 40},
        "vegetative":  {"N": 50,  "P": 20,  "K": 40},
        "flowering":   {"N": 30,  "P": 20,  "K": 40},
        "fruiting":    {"N": 20,  "P": 0,   "K": 40},
        "maturity":    {"N": 0,   "P": 0,   "K": 20},
    },
    "orange": {
        "seedling":    {"N": 30,  "P": 50,  "K": 40},
        "vegetative":  {"N": 60,  "P": 30,  "K": 60},
        "flowering":   {"N": 30,  "P": 20,  "K": 60},
        "fruiting":    {"N": 20,  "P": 0,   "K": 60},
        "maturity":    {"N": 0,   "P": 0,   "K": 30},
    },
    "soybean": {
        "seedling":    {"N": 20,  "P": 60,  "K": 30},
        "vegetative":  {"N": 20,  "P": 30,  "K": 30},
        "flowering":   {"N": 0,   "P": 20,  "K": 30},
        "fruiting":    {"N": 0,   "P": 0,   "K": 30},
        "maturity":    {"N": 0,   "P": 0,   "K": 0},
    },
    "apple": {
        "seedling":    {"N": 40,  "P": 60,  "K": 40},
        "vegetative":  {"N": 70,  "P": 35,  "K": 70},
        "flowering":   {"N": 35,  "P": 25,  "K": 70},
        "fruiting":    {"N": 20,  "P": 0,   "K": 70},
        "maturity":    {"N": 0,   "P": 0,   "K": 35},
    },
    "other": {
        "seedling":    {"N": 40,  "P": 60,  "K": 40},
        "vegetative":  {"N": 60,  "P": 30,  "K": 40},
        "flowering":   {"N": 30,  "P": 20,  "K": 40},
        "fruiting":    {"N": 20,  "P": 0,   "K": 40},
        "maturity":    {"N": 0,   "P": 0,   "K": 0},
    },
}

# Application method per stage
NPK_APPLICATION = {
    "seedling":   "Basal application — broadcast + incorporate before transplanting.",
    "vegetative": "Top-dress at 25–30 DAT. Apply near root zone, avoid leaf contact.",
    "flowering":  "Foliar spray (micronutrients) + soil top-dress at flower initiation.",
    "fruiting":   "Fertigation or banding near root zone. Avoid high N at this stage.",
    "maturity":   "Minimal inputs needed. Focus on K to improve fruit quality.",
}

# Fertilizer source conversion: kg pure nutrient → kg commercial product
# Urea=46%N, SSP=16%P, MOP=60%K
FERTILIZER_PRODUCTS = {
    "N": {"name": "Urea",  "purity_pct": 46, "price_per_kg": 6.5,  "unit": "kg",
          "buy_query": "urea+fertilizer+50kg"},
    "P": {"name": "DAP",   "purity_pct": 46, "price_per_kg": 27.0, "unit": "kg",
          "buy_query": "DAP+fertilizer+50kg"},
    "K": {"name": "MOP",   "purity_pct": 60, "price_per_kg": 18.5, "unit": "kg",
          "buy_query": "MOP+potash+fertilizer+25kg"},
}

# Area conversions to hectares
AREA_TO_HA = {
    "acre":    0.4047,
    "hectare": 1.0,
    "gunta":   0.0101,
}


# ── Pesticide recommendations per disease ─────────────────────────────────────
# Source: ICAR, CIB&RC registration data, TNAU crop protection guide
# dosage_per_ha: ml or g per hectare (per spray application)
# dilution_per_L: ml or g per litre of water
# pump_size_L: standard knapsack sprayer = 16L

PESTICIDES = {
    # ── Tomato diseases ──
    "early_blight": [
        {"product": "Mancozeb 75% WP",    "dosage_per_ha": 2000, "unit": "g",
         "dilution_per_L": 2.5, "safety_days": 5,
         "apply_on": "Spray on both leaf surfaces. Cover undersides thoroughly.",
         "buy_query": "mancozeb+75+WP+fungicide"},
        {"product": "Copper Oxychloride 50% WP", "dosage_per_ha": 3000, "unit": "g",
         "dilution_per_L": 3.0, "safety_days": 7,
         "apply_on": "Full plant coverage. Avoid spraying in rain.",
         "buy_query": "copper+oxychloride+fungicide"},
        {"product": "Azoxystrobin 23% SC", "dosage_per_ha": 1000, "unit": "ml",
         "dilution_per_L": 1.0, "safety_days": 3,
         "apply_on": "Preventive spray at disease onset. 2 sprays, 10 days apart.",
         "buy_query": "azoxystrobin+fungicide+amistar"},
    ],
    "late_blight": [
        {"product": "Metalaxyl 8% + Mancozeb 64% WP", "dosage_per_ha": 2500, "unit": "g",
         "dilution_per_L": 2.5, "safety_days": 7,
         "apply_on": "Spray early morning. Cover all plant surfaces.",
         "buy_query": "metalaxyl+mancozeb+ridomil+fungicide"},
        {"product": "Cymoxanil 8% + Mancozeb 64% WP", "dosage_per_ha": 2000, "unit": "g",
         "dilution_per_L": 2.5, "safety_days": 5,
         "apply_on": "Curative spray. 2–3 applications at 7-day intervals.",
         "buy_query": "cymoxanil+mancozeb+curzate+fungicide"},
    ],
    "leaf_mold": [
        {"product": "Chlorothalonil 75% WP", "dosage_per_ha": 2000, "unit": "g",
         "dilution_per_L": 2.0, "safety_days": 7,
         "apply_on": "Focus on underside of leaves. Good air circulation helps.",
         "buy_query": "chlorothalonil+fungicide"},
    ],
    "septoria_leaf_spot": [
        {"product": "Mancozeb 75% WP",    "dosage_per_ha": 2000, "unit": "g",
         "dilution_per_L": 2.5, "safety_days": 5,
         "apply_on": "Spray at first sign. Remove heavily infected leaves before spraying.",
         "buy_query": "mancozeb+75+WP+fungicide"},
    ],
    "bacterial_spot": [
        {"product": "Copper Oxychloride 50% WP", "dosage_per_ha": 3000, "unit": "g",
         "dilution_per_L": 3.0, "safety_days": 7,
         "apply_on": "Bactericide spray. Avoid during high temperature (>32°C).",
         "buy_query": "copper+oxychloride+bactericide"},
        {"product": "Streptomycin 90% + Tetracycline 10%", "dosage_per_ha": 150, "unit": "g",
         "dilution_per_L": 0.15, "safety_days": 10,
         "apply_on": "Mix with water. Spray in early morning or evening.",
         "buy_query": "streptomycin+tetracycline+agrimycin+bactericide"},
    ],
    "mosaic_virus": [
        {"product": "Imidacloprid 17.8% SL (vector control)", "dosage_per_ha": 125, "unit": "ml",
         "dilution_per_L": 0.5, "safety_days": 14,
         "apply_on": "Controls aphid vectors. Do NOT use near pollinators during flowering.",
         "buy_query": "imidacloprid+confidor+insecticide"},
    ],
    "spider_mites": [
        {"product": "Abamectin 1.8% EC", "dosage_per_ha": 750, "unit": "ml",
         "dilution_per_L": 1.0, "safety_days": 7,
         "apply_on": "Spray undersides of leaves. Two applications 7 days apart.",
         "buy_query": "abamectin+vertimec+miticide"},
        {"product": "Wettable Sulphur 80% WP", "dosage_per_ha": 3000, "unit": "g",
         "dilution_per_L": 3.0, "safety_days": 3,
         "apply_on": "Organic-compatible. Avoid when temp >32°C (phytotoxic).",
         "buy_query": "wettable+sulphur+miticide+fungicide"},
    ],
    # ── General / fallback ──
    "leaf_spots": [
        {"product": "Mancozeb 75% WP",    "dosage_per_ha": 2000, "unit": "g",
         "dilution_per_L": 2.5, "safety_days": 5,
         "apply_on": "Broad-spectrum contact fungicide. Apply preventively.",
         "buy_query": "mancozeb+75+WP+fungicide"},
        {"product": "Propiconazole 25% EC", "dosage_per_ha": 500, "unit": "ml",
         "dilution_per_L": 0.5, "safety_days": 7,
         "apply_on": "Systemic fungicide. Highly effective on leaf spots.",
         "buy_query": "propiconazole+tilt+fungicide"},
    ],
    "yellowing": [
        {"product": "Ferrous Sulphate (foliar)", "dosage_per_ha": 2000, "unit": "g",
         "dilution_per_L": 2.0, "safety_days": 0,
         "apply_on": "Spray on leaves. Check soil pH first. Repeat in 15 days if needed.",
         "buy_query": "ferrous+sulphate+fertilizer+iron"},
    ],
    "wilting": [
        {"product": "Carbendazim 50% WP (soil drench)", "dosage_per_ha": 1000, "unit": "g",
         "dilution_per_L": 1.0, "safety_days": 5,
         "apply_on": "Root zone drench. 5L solution per plant. Repeat in 10 days.",
         "buy_query": "carbendazim+bavistin+fungicide"},
    ],
    "powder": [
        {"product": "Wettable Sulphur 80% WP", "dosage_per_ha": 3000, "unit": "g",
         "dilution_per_L": 3.0, "safety_days": 3,
         "apply_on": "Full plant coverage. Best in cool, dry weather.",
         "buy_query": "wettable+sulphur+80+WP"},
        {"product": "Hexaconazole 5% EC", "dosage_per_ha": 1000, "unit": "ml",
         "dilution_per_L": 1.0, "safety_days": 7,
         "apply_on": "Systemic. Two sprays 14 days apart at disease onset.",
         "buy_query": "hexaconazole+contaf+fungicide"},
    ],
    "stem_rot": [
        {"product": "Carbendazim 50% WP", "dosage_per_ha": 1000, "unit": "g",
         "dilution_per_L": 1.0, "safety_days": 5,
         "apply_on": "Drench at base of stem. Remove infected plant material first.",
         "buy_query": "carbendazim+bavistin+fungicide"},
    ],
    "holes": [
        {"product": "Chlorpyrifos 20% EC", "dosage_per_ha": 1500, "unit": "ml",
         "dilution_per_L": 2.5, "safety_days": 14,
         "apply_on": "Spray in evening. Targets caterpillars and chewing insects.",
         "buy_query": "chlorpyrifos+dursban+insecticide"},
        {"product": "Neem Oil 1500 ppm",   "dosage_per_ha": 5000, "unit": "ml",
         "dilution_per_L": 5.0, "safety_days": 0,
         "apply_on": "Organic option. Repeat every 7 days. Use with a spreader-sticker.",
         "buy_query": "neem+oil+1500+ppm+biopesticide"},
    ],
}

# Pump size and water requirement per ha (standard)
KNAPSACK_PUMP_L = 16      # litres per refill
WATER_PER_HA_L  = 500     # litres of spray solution per hectare (standard high-volume)


# ── Crop economics (₹ per kg MSP / market price, Karnataka 2024) ─────────────
# Source: Karnataka APMC, eNAM portal, 2024 estimates
CROP_ECONOMICS = {
    "tomato":     {"price_per_kg": 22, "cost_per_ha": 85000,  "yield_t_ha": 25, "season_days": 120},
    "potato":     {"price_per_kg": 18, "cost_per_ha": 70000,  "yield_t_ha": 22, "season_days": 90},
    "corn_maize": {"price_per_kg": 21, "cost_per_ha": 35000,  "yield_t_ha": 6,  "season_days": 100},
    "grape":      {"price_per_kg": 60, "cost_per_ha": 200000, "yield_t_ha": 15, "season_days": 180},
    "bell_pepper":{"price_per_kg": 45, "cost_per_ha": 90000,  "yield_t_ha": 18, "season_days": 120},
    "strawberry": {"price_per_kg": 90, "cost_per_ha": 150000, "yield_t_ha": 12, "season_days": 150},
    "orange":     {"price_per_kg": 35, "cost_per_ha": 80000,  "yield_t_ha": 10, "season_days": 270},
    "soybean":    {"price_per_kg": 40, "cost_per_ha": 25000,  "yield_t_ha": 2,  "season_days": 100},
    "apple":      {"price_per_kg": 80, "cost_per_ha": 180000, "yield_t_ha": 10, "season_days": 240},
    "other":      {"price_per_kg": 25, "cost_per_ha": 50000,  "yield_t_ha": 8,  "season_days": 120},
}

# Marketplace redirect base URLs (search-based, no API or affiliate key needed)
MARKETPLACE_LINKS = {
    "agribazaar": "https://www.agribazaar.com/search?q=",
    "amazon":     "https://www.amazon.in/s?k=",
    "indiaMart":  "https://www.indiamart.com/search.mp?ss=",
}

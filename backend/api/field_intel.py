"""
PestPulse — Field Intelligence & Hotspot API
GET  /api/v1/field-intelligence   — soil + weather + crop recs for a lat/lon
GET  /api/v1/hotspots             — disease hotspot clusters from DB
"""
from fastapi import APIRouter
from backend.services.soil import get_soil_data
from backend.services.weather import get_weather
from backend.db import get_db

router = APIRouter(prefix="/api/v1")


# ── Field Intelligence (Farmer "My Field" view) ───────────────────────────────
@router.get("/field-intelligence")
async def field_intelligence(lat: float = 12.97, lon: float = 77.59):
    """
    Combines live weather + SoilGrids soil data → returns:
    - Soil type, pH, fertility score, water retention
    - Top crop recommendations (ICAR rules)
    - Disease risk heuristics from soil+weather
    """
    weather = await get_weather(lat, lon)
    cur     = weather.get("current", {})
    temp    = cur.get("temperature_c",        27.0) or 27.0
    humid   = cur.get("relative_humidity_pct", 65.0) or 65.0
    precip  = cur.get("precipitation_mm",       0.0) or 0.0

    soil = await get_soil_data(lat, lon, temp_c=temp, humidity_pct=humid, precip_mm=precip)

    return {
        "lat":      lat,
        "lon":      lon,
        "weather":  weather,
        "soil":     soil,
    }


# ── Regional Hotspots ─────────────────────────────────────────────────────────
@router.get("/hotspots")
def get_hotspots(district: str = None, days: int = 30, top: int = 10):
    """
    Aggregates observations from the DB grouped by district + crop + symptom.
    Returns hotspot clusters sorted by case count descending.
    """
    db  = get_db()
    sql = """
        SELECT
            district,
            location_cell,
            crop,
            symptom_group,
            severity,
            COUNT(*)          AS case_count,
            SUM(review_required) AS urgent_count,
            MAX(created_at)   AS latest_report,
            AVG(triage_score) AS avg_score
        FROM observations
        WHERE created_at >= datetime('now', ? )
    """
    args = [f"-{days} days"]
    if district:
        sql  += " AND district = ?"
        args.append(district)

    sql += """
        GROUP BY district, crop, symptom_group
        ORDER BY case_count DESC, avg_score DESC
        LIMIT ?
    """
    args.append(top)

    rows = db.execute(sql, args).fetchall()

    # District summary for officer map
    dist_sql = """
        SELECT district, COUNT(*) as total,
               SUM(review_required) as urgent,
               MAX(created_at) as latest
        FROM observations
        WHERE created_at >= datetime('now', ?)
        GROUP BY district
        ORDER BY total DESC
    """
    dist_rows = db.execute(dist_sql, [f"-{days} days"]).fetchall()
    db.close()

    # Risk level per cluster
    def risk_level(count, urgent, avg_score):
        if urgent > 0 or avg_score > 70:  return {"label": "HIGH",   "color": "#ef4444"}
        if count  > 2 or avg_score > 40:  return {"label": "MEDIUM", "color": "#f59e0b"}
        return                                    {"label": "LOW",    "color": "#00e676"}

    clusters = []
    for r in rows:
        d = dict(r)
        d["risk"] = risk_level(d["case_count"], d["urgent_count"] or 0, d["avg_score"] or 0)
        clusters.append(d)

    return {
        "clusters":         clusters,
        "district_summary": [dict(r) for r in dist_rows],
        "days_window":      days,
        "total_clusters":   len(clusters),
    }


# ── Nearby cases (farmer view — show what's happening near me) ────────────────
@router.get("/nearby-cases")
def get_nearby_cases(district: str = "", days: int = 14):
    """Returns recent confirmed cases near the farmer's district."""
    db  = get_db()
    sql = """
        SELECT crop, symptom_group, severity, status,
               district, created_at
        FROM observations
        WHERE created_at >= datetime('now', ?)
          AND status IN ('resolved','review_required','monitor')
    """
    args = [f"-{days} days"]
    if district:
        sql  += " AND district = ?"
        args.append(district)
    sql += " ORDER BY created_at DESC LIMIT 20"

    rows = db.execute(sql, args).fetchall()
    db.close()
    return {"cases": [dict(r) for r in rows], "days_window": days}

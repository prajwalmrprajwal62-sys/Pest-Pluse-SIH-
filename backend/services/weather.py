"""
PestPulse — Weather Service (Open-Meteo adapter with cache)
"""
import time
import httpx
from backend.config import (
    OPEN_METEO_ENABLED, OPEN_METEO_TIMEOUT_SECONDS,
    WEATHER_CACHE_MINUTES, DEFAULT_LAT, DEFAULT_LON,
)

_cache: dict = {}

FIXTURE_WEATHER = {
    "source": "FIXTURE",
    "freshness": "DEMO",
    "latitude": DEFAULT_LAT,
    "longitude": DEFAULT_LON,
    "current": {
        "temperature_c": 28.5,
        "relative_humidity_pct": 72,
        "precipitation_mm": 1.2,
    },
    "warnings": ["Weather data unavailable — using demo fixture."],
}


async def get_weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> dict:
    cache_key = f"{lat:.2f},{lon:.2f}"
    now = time.time()

    if cache_key in _cache:
        entry = _cache[cache_key]
        age_minutes = (now - entry["fetched_at"]) / 60
        if age_minutes < WEATHER_CACHE_MINUTES:
            entry["data"]["freshness"] = "LIVE" if age_minutes < 5 else "STALE"
            return entry["data"]

    if not OPEN_METEO_ENABLED:
        return FIXTURE_WEATHER

    try:
        async with httpx.AsyncClient(timeout=OPEN_METEO_TIMEOUT_SECONDS) as client:
            r = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,precipitation",
                    "forecast_days": 1,
                    "timezone": "auto",
                }
            )
            r.raise_for_status()
            raw = r.json()
            cur = raw.get("current", {})
            data = {
                "source": "OPEN_METEO",
                "freshness": "LIVE",
                "latitude": lat,
                "longitude": lon,
                "current": {
                    "temperature_c":        cur.get("temperature_2m"),
                    "relative_humidity_pct": cur.get("relative_humidity_2m"),
                    "precipitation_mm":      cur.get("precipitation", 0),
                },
                "warnings": [],
            }
            _cache[cache_key] = {"data": data, "fetched_at": now}
            return data
    except Exception as e:
        print(f"[Weather] Open-Meteo failed: {e}")
        return {**FIXTURE_WEATHER, "warnings": [f"Weather fetch failed: {e}"]}

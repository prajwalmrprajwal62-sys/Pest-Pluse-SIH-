"""
PestPulse — Provider / health / config endpoints
"""
import time
from fastapi import APIRouter
from backend.services.weather import get_weather
from backend.services.inference import get_model_status
from backend.config import (
    SUPPORTED_CROPS, CROP_DISPLAY, OUTPUT_STATES, KVK_CONTACTS,
    MARKET_PRICES, RULE_VERSION, APP_VERSION, DEMO_MODE, GRADIO_URL,
)

router = APIRouter(prefix="/api/v1")


@router.get("/health/providers")
async def provider_health():
    weather = await get_weather()
    return {
        "model":       get_model_status(),
        "weather":     {"source": weather.get("source"), "freshness": weather.get("freshness")},
        "bhashini":    {"state": "VOICE_FIXTURE"},
        "database":    {"state": "CONNECTED"},
        "rule_version": RULE_VERSION,
        "app_version":  APP_VERSION,
        "demo_mode":    DEMO_MODE,
    }


@router.get("/weather")
async def weather_endpoint(lat: float = 12.97, lon: float = 77.59):
    return await get_weather(lat, lon)


@router.get("/config")
def get_config(lang: str = "en"):
    safe_lang = lang if lang in ("en", "kn", "hi") else "en"
    return {
        "supported_crops": [
            {"key": k, "label": CROP_DISPLAY.get(safe_lang, {}).get(k, k)}
            for k in SUPPORTED_CROPS
        ],
        "output_states": {
            k: v.get(safe_lang, v.get("en","")) for k, v in OUTPUT_STATES.items()
        },
        "kvk_contacts":  KVK_CONTACTS,
        "market_prices": MARKET_PRICES,
        "gradio_configured": bool(GRADIO_URL),
        "demo_mode":    DEMO_MODE,
    }


@router.get("/market/prices")
def market_prices(lang: str = "en"):
    """Dedicated market prices endpoint used by officer dashboard."""
    return {
        "prices":  MARKET_PRICES,
        "updated": "Live demo data",
        "source":  "Karnataka APMC (demo fixture)",
    }


@router.get("/kvk")
def kvk_contacts(district: str = ""):
    """KVK contact list — filterable by district."""
    contacts = KVK_CONTACTS
    if district:
        contacts = [c for c in contacts if district.lower() in c.get("district","").lower()]
    return {"contacts": contacts, "total": len(contacts)}


@router.post("/quality")
async def quality_compat():
    """Backward-compat stub — old farmer.html called this. Returns pass-through."""
    return {"status": "ok", "message": "Use /api/v1/quick-infer for image quality check."}


@router.get("/farmer/history")
async def farmer_history(phone: str = "", limit: int = 20):
    """Return recent observations for a farmer (demo: returns last N from DB)."""
    from backend.db import get_db
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT id, crop, growth_stage, symptom_group, severity, status, triage_score, created_at "
            "FROM observations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return {
            "history": [dict(r) for r in rows],
            "total":   len(rows),
        }
    except Exception as e:
        return {"history": [], "total": 0, "error": str(e)}


@router.get("/hotspots")
def get_hotspots():
    """Coarse aggregate hotspot data (demo fixtures)."""
    return {
        "evidence_state": "DEMO",
        "time_window": "last_7_days",
        "cells": [
            {"cell_id": "BLR-N", "label": "Bengaluru North",  "case_count": 12, "confirmed": 3, "review_count": 4, "top_crop": "tomato"},
            {"cell_id": "TUM-C", "label": "Tumkur Central",   "case_count": 8,  "confirmed": 2, "review_count": 2, "top_crop": "potato"},
            {"cell_id": "KLR-E", "label": "Kolar East",       "case_count": 6,  "confirmed": 1, "review_count": 3, "top_crop": "corn_maize"},
        ],
    }

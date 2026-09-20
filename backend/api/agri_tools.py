"""
PestPulse — AgriTools API
GET  /api/v1/tools/fertilizer   — NPK calculator
GET  /api/v1/tools/pesticide    — Pesticide dosage calculator
GET  /api/v1/tools/economics    — Farm profitability calculator
GET  /api/v1/tools/marketplace  — Buy-link resolver for a disease
"""
import math
from fastapi import APIRouter
from backend.services.agri_tables import (
    NPK, NPK_APPLICATION, FERTILIZER_PRODUCTS, AREA_TO_HA,
    PESTICIDES, KNAPSACK_PUMP_L, WATER_PER_HA_L,
    CROP_ECONOMICS, MARKETPLACE_LINKS,
)

router = APIRouter(prefix="/api/v1/tools")


# ── 1. Fertilizer Calculator ───────────────────────────────────────────────────
@router.get("/fertilizer")
def fertilizer_calc(
    crop: str  = "tomato",
    stage: str = "vegetative",
    area: float = 1.0,
    unit: str   = "acre",     # acre | hectare | gunta
):
    ha_factor = AREA_TO_HA.get(unit, 0.4047)
    area_ha   = area * ha_factor

    crop_npk  = NPK.get(crop) or NPK["other"]
    stage_key = stage if stage in crop_npk else "vegetative"
    npk       = crop_npk[stage_key]

    results = {}
    total_cost = 0.0
    for nutrient, kg_per_ha in npk.items():
        prod = FERTILIZER_PRODUCTS[nutrient]
        # kg pure nutrient needed → kg commercial product
        pure_kg    = kg_per_ha * area_ha
        product_kg = round(pure_kg / (prod["purity_pct"] / 100), 1)
        cost_inr   = round(product_kg * prod["price_per_kg"], 0)
        total_cost += cost_inr
        results[nutrient] = {
            "nutrient":       nutrient,
            "pure_kg":        round(pure_kg, 1),
            "product":        prod["name"],
            "product_kg":     product_kg,
            "price_per_kg":   prod["price_per_kg"],
            "cost_inr":       int(cost_inr),
            "buy_links":      _buy_links(prod["buy_query"]),
        }

    return {
        "crop":         crop,
        "stage":        stage_key,
        "area":         area,
        "unit":         unit,
        "area_ha":      round(area_ha, 3),
        "nutrients":    results,
        "total_cost_inr": int(total_cost),
        "application_note": NPK_APPLICATION.get(stage_key, ""),
        "source": "ICAR UAS Dharwad Karnataka Package of Practices 2023",
    }


# ── 2. Pesticide Calculator ────────────────────────────────────────────────────
@router.get("/pesticide")
def pesticide_calc(
    disease: str  = "leaf_spots",
    area: float   = 1.0,
    unit: str     = "acre",
    product_idx: int = 0,      # which product from the disease list
):
    ha_factor = AREA_TO_HA.get(unit, 0.4047)
    area_ha   = area * ha_factor

    prods = PESTICIDES.get(disease) or PESTICIDES["leaf_spots"]
    idx   = min(product_idx, len(prods) - 1)
    p     = prods[idx]

    total_product    = p["dosage_per_ha"] * area_ha
    water_needed_L   = WATER_PER_HA_L * area_ha
    dose_per_pump    = round(p["dilution_per_L"] * KNAPSACK_PUMP_L, 1)
    pump_refills     = math.ceil(water_needed_L / KNAPSACK_PUMP_L)
    total_product_ml = round(total_product, 1)
    cost_estimate    = round(total_product_ml * 0.08, 0)  # ~₹80/L average

    return {
        "disease":      disease,
        "area":         area,
        "unit":         unit,
        "area_ha":      round(area_ha, 3),
        "product":      p["product"],
        "unit_type":    p["unit"],
        "total_product": total_product_ml,
        "dose_per_pump": dose_per_pump,
        "pump_refills":  pump_refills,
        "water_needed_L": round(water_needed_L, 0),
        "safety_days":   p["safety_days"],
        "apply_on":      p["apply_on"],
        "cost_estimate_inr": int(cost_estimate),
        "buy_links":     _buy_links(p["buy_query"]),
        "all_products":  [
            {"idx": i, "name": pr["product"], "unit": pr["unit"]}
            for i, pr in enumerate(prods)
        ],
        "source": "CIB&RC / ICAR registered pesticide dosages",
    }


# ── 3. Farm Economics Calculator ──────────────────────────────────────────────
@router.get("/economics")
def economics_calc(
    crop: str         = "tomato",
    area: float       = 1.0,
    unit: str         = "acre",
    sell_price: float = 0,      # ₹/kg (0 = use default)
    extra_cost: float = 0,      # ₹ additional input cost
    yield_t: float    = 0,      # expected yield tonnes (0 = use default)
):
    ha_factor  = AREA_TO_HA.get(unit, 0.4047)
    area_ha    = area * ha_factor
    econ       = CROP_ECONOMICS.get(crop, CROP_ECONOMICS["other"])

    price_kg   = sell_price if sell_price > 0 else econ["price_per_kg"]
    base_cost  = econ["cost_per_ha"] * area_ha + extra_cost
    exp_yield  = (yield_t if yield_t > 0 else econ["yield_t_ha"]) * area_ha   # tonnes
    exp_yield_kg = exp_yield * 1000

    revenue     = round(exp_yield_kg * price_kg, 0)
    profit      = round(revenue - base_cost, 0)
    breakeven_price = round(base_cost / exp_yield_kg, 2) if exp_yield_kg else 0
    req_yield_kg    = round(base_cost / price_kg, 0) if price_kg else 0
    max_input_budget = round(revenue * 0.45, 0)   # rule-of-thumb: inputs ≤ 45% revenue
    roi_pct     = round((profit / base_cost) * 100, 1) if base_cost else 0

    return {
        "crop":               crop,
        "area":               area,
        "unit":               unit,
        "area_ha":            round(area_ha, 3),
        "expected_yield_kg":  int(exp_yield_kg),
        "sell_price_per_kg":  price_kg,
        "total_cost_inr":     int(base_cost),
        "total_revenue_inr":  int(revenue),
        "net_profit_inr":     int(profit),
        "roi_pct":            roi_pct,
        "breakeven_price_per_kg": breakeven_price,
        "required_yield_kg":  int(req_yield_kg),
        "max_input_budget_inr": int(max_input_budget),
        "season_days":        econ["season_days"],
        "source":             "Karnataka APMC / eNAM 2024 estimates",
    }


# ── 4. Marketplace / buy-links for a given disease ────────────────────────────
@router.get("/marketplace")
def marketplace(disease: str = "leaf_spots"):
    prods = PESTICIDES.get(disease) or PESTICIDES["leaf_spots"]
    items = []
    for p in prods[:3]:   # max 3 cards
        items.append({
            "product":   p["product"],
            "buy_links": _buy_links(p["buy_query"]),
            "apply_on":  p["apply_on"],
            "safety_days": p["safety_days"],
        })
    return {"disease": disease, "products": items}


# ── Helper ────────────────────────────────────────────────────────────────────
def _buy_links(query: str) -> dict:
    q = query.replace(" ", "+")
    return {
        "agribazaar": f"{MARKETPLACE_LINKS['agribazaar']}{q}",
        "amazon":     f"{MARKETPLACE_LINKS['amazon']}{q}",
        "indiaMart":  f"{MARKETPLACE_LINKS['indiaMart']}{q}",
    }

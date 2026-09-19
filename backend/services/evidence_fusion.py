"""
PestPulse — Evidence Fusion Engine
Combines all evidence signals into a single triage score and output state.
"""
from backend.config import (
    WEIGHTS, SYMPTOM_SIGNAL, STAGE_VULNERABILITY,
    MONITOR_THRESHOLD, REVIEW_THRESHOLD, CONFIDENCE_REVIEW_BELOW,
    ACTIONS, RULE_VERSION,
)


def _weather_signal(weather: dict | None) -> float:
    """High humidity + recent rain = higher disease risk."""
    if not weather:
        return 0.5  # neutral when unavailable
    humidity = weather.get("relative_humidity_pct", 50)
    precip   = weather.get("precipitation_mm", 0)
    h_score  = min(humidity / 100, 1.0)
    p_score  = min(precip / 10.0, 1.0)
    return round(0.6 * h_score + 0.4 * p_score, 3)


def _severity_signal(severity: str) -> float:
    return {"almost_all": 0.95, "many": 0.70, "few": 0.35, "unknown": 0.50}.get(severity, 0.5)


def _trap_signal(trap_count: int | None) -> float:
    if trap_count is None:
        return 0.5
    if trap_count <= 0:   return 0.05
    if trap_count <= 5:   return 0.30
    if trap_count <= 20:  return 0.60
    return 0.90


def _nearby_signal(nearby_count: int) -> float:
    if nearby_count <= 0: return 0.10
    if nearby_count <= 2: return 0.40
    if nearby_count <= 5: return 0.65
    return 0.85


def fuse(
    *,
    symptom_group: str,
    growth_stage: str,
    severity: str,
    weather: dict | None,
    trap_count: int | None,
    nearby_count: int = 0,
    model_confidence: float | None = None,
    model_decision: str | None = None,
    language: str = "en",
) -> dict:
    """
    Returns a full result dict:
      status, triage_score, decision, human_action, reasoning,
      review_required, evidence_breakdown, rule_version
    """
    symptom_s  = SYMPTOM_SIGNAL.get(symptom_group, 0.5)
    stage_s    = STAGE_VULNERABILITY.get(growth_stage, 0.5)
    weather_s  = _weather_signal(weather)
    severity_s = _severity_signal(severity)
    trap_s     = _trap_signal(trap_count)
    nearby_s   = _nearby_signal(nearby_count)

    active = dict(WEIGHTS)
    total_weight = sum(active.values())

    raw_score = (
        active["symptom"]  * symptom_s  +
        active["stage"]    * stage_s    +
        active["weather"]  * weather_s  +
        active["severity"] * severity_s +
        active["trap"]     * trap_s     +
        active["nearby"]   * nearby_s
    ) / total_weight

    score = round(raw_score, 3)

    # Model confidence can force REVIEW state
    force_review = (
        model_decision == "REVIEW_REQUIRED" or
        (model_confidence is not None and model_confidence < CONFIDENCE_REVIEW_BELOW)
    )

    if score < MONITOR_THRESHOLD and not force_review:
        status   = "monitor"
        decision = "monitor_and_resample"
    elif score < REVIEW_THRESHOLD and not force_review:
        status   = "low_risk_action"
        decision = _pick_low_risk_action(symptom_group)
    else:
        status   = "review_required"
        decision = "refer_to_expert"

    review_required = status == "review_required"
    action_key      = decision
    action_text     = ACTIONS.get(action_key, {}).get(language, ACTIONS.get(action_key, {}).get("en", ""))

    # Build reasoning string
    missing = []
    if trap_count is None:   missing.append("trap_count")
    if not nearby_count:     missing.append("nearby_report_count")
    if not weather:          missing.append("weather_data")

    reasoning = (
        f"Score {score:.2f}: {symptom_group} at {growth_stage} stage. "
        f"Humidity signal: {round(weather_s*100)}%. Severity: {severity}. "
        f"Components: [symptom={symptom_s}, stage={stage_s}, weather={weather_s}, severity={severity_s}]. "
    )
    if missing:
        reasoning += f"Missing: {', '.join(missing)}."

    return {
        "status":         status,
        "triage_score":   score,
        "decision":       decision,
        "human_action":   action_text,
        "reasoning":      reasoning,
        "review_required": review_required,
        "rule_version":   RULE_VERSION,
        "evidence_breakdown": {
            "symptom":  {"score": symptom_s,  "weight": active["symptom"]},
            "stage":    {"score": stage_s,    "weight": active["stage"]},
            "weather":  {"score": weather_s,  "weight": active["weather"]},
            "severity": {"score": severity_s, "weight": active["severity"]},
            "trap":     {"score": trap_s,     "weight": active["trap"]},
            "nearby":   {"score": nearby_s,   "weight": active["nearby"]},
        },
        "missing_evidence": missing,
    }


def _pick_low_risk_action(symptom_group: str) -> str:
    drainage_triggers = {"wilting", "yellowing", "leaf_curling"}
    if symptom_group in drainage_triggers:
        return "improve_drainage"
    return "inspect_and_remove"

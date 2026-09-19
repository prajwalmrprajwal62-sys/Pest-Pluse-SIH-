"""
PestPulse — Observations API
POST /api/v1/observations     — create case
GET  /api/v1/observations     — list all (latest first)
GET  /api/v1/observations/:id — full case detail
"""
import uuid, json, hashlib, os, shutil
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from backend.db import get_db
from backend.config import UPLOAD_DIR, RULE_VERSION, ACTIONS, OUTPUT_STATES
from backend.services.quality_gate import check_quality
from backend.services.inference import run_inference
from backend.services.evidence_fusion import fuse
from backend.services.weather import get_weather

router = APIRouter(prefix="/api/v1")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.post("/observations")
async def create_observation(
    crop:          str  = Form(...),
    growth_stage:  str  = Form(...),
    symptom_group: str  = Form(...),
    severity:      str  = Form(...),
    affected_area: str  = Form("unknown"),
    recent_rain:   str  = Form("unknown"),
    trap_count:    int  = Form(None),
    district:      str  = Form(""),
    taluka:        str  = Form(""),
    lat:           float= Form(12.97),
    lon:           float= Form(77.59),
    language:      str  = Form("en"),
    client_event_id: str = Form(None),
    image: UploadFile = File(None),
):
    obs_id   = str(uuid.uuid4())
    ev_id    = client_event_id or str(uuid.uuid4())
    now_str  = _now()
    db       = get_db()

    # ── Idempotency ─────────────────────────────────────────────────────────
    existing = db.execute(
        "SELECT id FROM observations WHERE client_event_id=?", (ev_id,)
    ).fetchone()
    if existing:
        db.close()
        return JSONResponse({"observation_id": existing["id"], "duplicate": True})

    # ── Image handling ───────────────────────────────────────────────────────
    quality_result   = {"passed": True, "quality_state": "NO_IMAGE", "message": "No image submitted."}
    media_id         = None
    image_bytes      = None

    if image and image.filename:
        image_bytes = await image.read()
        mime        = image.content_type or "image/jpeg"
        quality_result = check_quality(image_bytes, mime)

        if quality_result["passed"]:
            sha  = hashlib.sha256(image_bytes).hexdigest()
            ext  = mime.split("/")[-1].replace("jpeg","jpg")
            fname= f"{obs_id}.{ext}"
            path = os.path.join(UPLOAD_DIR, fname)
            with open(path, "wb") as f:
                f.write(image_bytes)

            media_id = str(uuid.uuid4())
            db.execute(
                """INSERT INTO media_assets
                   (id,observation_id,relative_path,sha256,mime_type,width,height,quality_state,blur_score,brightness,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (media_id, obs_id, fname, sha, mime,
                 quality_result.get("width"), quality_result.get("height"),
                 quality_result["quality_state"],
                 quality_result.get("blur_score"), quality_result.get("brightness"),
                 now_str)
            )

    # ── Invalid image ────────────────────────────────────────────────────────
    if image_bytes and not quality_result["passed"]:
        db.execute(
            """INSERT INTO observations
               (id,client_event_id,created_at,updated_at,district,taluka,lat,lon,crop,growth_stage,
                symptom_group,severity,affected_area,recent_rain,trap_count,language,status,
                review_required,triage_score,decision,human_action,reasoning,rule_version,created_source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (obs_id, ev_id, now_str, now_str, district, taluka, lat, lon, crop, growth_stage,
             symptom_group, severity, affected_area, recent_rain, trap_count, language,
             "invalid_input", 0, 0.0, "retake_image",
             ACTIONS["retake_image"].get(language, ACTIONS["retake_image"]["en"]),
             quality_result["message"], RULE_VERSION, "LIVE")
        )
        db.commit()
        db.close()
        return _build_response(obs_id, "invalid_input", 0.0, "retake_image",
                                ACTIONS["retake_image"].get(language, ACTIONS["retake_image"]["en"]),
                                quality_result["message"], False, quality_result, {}, language)

    # ── AI Inference ──────────────────────────────────────────────────────────
    model_result = {"provider": "NO_IMAGE", "confidence": None, "decision": None,
                    "review_required": False, "top_k": []}
    if image_bytes and quality_result["passed"]:
        model_result = await run_inference(image_bytes)

    # ── Weather ───────────────────────────────────────────────────────────────
    weather = await get_weather(lat, lon)

    # ── Evidence Fusion ───────────────────────────────────────────────────────
    fusion = fuse(
        symptom_group=symptom_group,
        growth_stage=growth_stage,
        severity=severity,
        weather=weather.get("current"),
        trap_count=trap_count,
        model_confidence=model_result.get("confidence"),
        model_decision=model_result.get("decision"),
        language=language,
    )

    status        = fusion["status"]
    triage_score  = fusion["triage_score"]
    decision      = fusion["decision"]
    human_action  = fusion["human_action"]
    reasoning     = fusion["reasoning"]
    review_req    = 1 if fusion["review_required"] else 0

    # ── Persist observation ───────────────────────────────────────────────────
    db.execute(
        """INSERT INTO observations
           (id,client_event_id,created_at,updated_at,district,taluka,lat,lon,crop,growth_stage,
            symptom_group,severity,affected_area,recent_rain,trap_count,language,status,
            review_required,triage_score,decision,human_action,reasoning,rule_version,
            model_version,created_source)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (obs_id, ev_id, now_str, now_str, district, taluka, lat, lon, crop, growth_stage,
         symptom_group, severity, affected_area, recent_rain, trap_count, language,
         status, review_req, triage_score, decision, human_action, reasoning,
         RULE_VERSION, model_result.get("model_version", "none"), "LIVE")
    )

    # ── Persist model prediction ──────────────────────────────────────────────
    if model_result.get("provider") not in ("NO_IMAGE",):
        db.execute(
            """INSERT INTO model_predictions
               (id,observation_id,provider,model_version,top_k_json,confidence,decision,review_required,generated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), obs_id,
             model_result.get("provider","FIXTURE"),
             model_result.get("model_version","?"),
             json.dumps(model_result.get("top_k",[])),
             model_result.get("confidence"),
             model_result.get("decision"),
             1 if model_result.get("review_required") else 0,
             now_str)
        )

    # ── Audit ─────────────────────────────────────────────────────────────────
    db.execute(
        "INSERT INTO audit_events (id,entity_type,entity_id,event_type,actor_role,payload_json,created_at) VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "observation", obs_id, "CREATED", "farmer",
         json.dumps({"status": status, "score": triage_score}), now_str)
    )
    db.commit()
    db.close()

    return _build_response(obs_id, status, triage_score, decision, human_action,
                           reasoning, fusion["review_required"],
                           quality_result, model_result, language,
                           weather=weather, fusion=fusion)


@router.get("/observations/{obs_id}")
def get_observation(obs_id: str):
    db  = get_db()
    row = db.execute("SELECT * FROM observations WHERE id=?", (obs_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "Observation not found")

    media = db.execute("SELECT * FROM media_assets WHERE observation_id=?", (obs_id,)).fetchone()
    pred  = db.execute("SELECT * FROM model_predictions WHERE observation_id=? ORDER BY generated_at DESC LIMIT 1", (obs_id,)).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE observation_id=? ORDER BY created_at DESC", (obs_id,)).fetchall()
    followups = db.execute("SELECT * FROM followups WHERE observation_id=? ORDER BY created_at DESC", (obs_id,)).fetchall()
    audits = db.execute("SELECT * FROM audit_events WHERE entity_id=? ORDER BY created_at", (obs_id,)).fetchall()
    db.close()

    return {
        "observation":  dict(row),
        "media":        dict(media) if media else None,
        "prediction":   dict(pred)  if pred  else None,
        "reviews":      [dict(r) for r in reviews],
        "followups":    [dict(f) for f in followups],
        "audit_trail":  [dict(a) for a in audits],
    }


@router.get("/observations")
def list_observations(limit: int = 20, offset: int = 0):
    db   = get_db()
    rows = db.execute(
        "SELECT id,created_at,crop,status,triage_score,district,review_required FROM observations ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    total = db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    db.close()
    return {"total": total, "items": [dict(r) for r in rows]}


def _build_response(obs_id, status, score, decision, action, reasoning,
                    review_req, quality, model, language,
                    weather=None, fusion=None):
    return {
        "observation_id":  obs_id,
        "status":          status,
        "triage_score":    score,
        "decision":        decision,
        "human_action":    action,
        "reasoning":       reasoning,
        "review_required": review_req,
        "language_used":   language,
        "image_quality":   quality,
        "model_result":    model,
        "weather":         weather,
        "evidence_breakdown": fusion.get("evidence_breakdown") if fusion else {},
        "missing_evidence":   fusion.get("missing_evidence", []) if fusion else [],
    }

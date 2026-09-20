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

# ── Input whitelists ──────────────────────────────────────────────────────────
VALID_CROPS = {
    'tomato','potato','apple','corn_maize','grape','bell_pepper',
    'cherry','orange','peach','strawberry','blueberry','raspberry',
    'soybean','squash','other',
}
VALID_STAGES    = {'seedling','vegetative','flowering','fruiting','maturity'}
VALID_SYMPTOMS  = {
    'leaf_spots','yellowing','leaf_curling','holes_or_chewing',
    'wilting','powder_coating','none_visible','stem_rot','holes',
}
VALID_SEVERITIES = {'almost_all','many','few','unknown'}

# ── Model scope metadata (read from manifest once) ────────────────────────────
_MODEL_SCOPE = {
    "crop_scope":       "Tomato",
    "num_classes":      4,
    "test_accuracy":    0.795,        # real held-out 88-image set
    "release_status":   "BENCHMARK_OR_DEMO_ONLY",
    "field_validation": "not_performed",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.post("/observations")
async def create_observation(
    crop:           str   = Form(...),
    growth_stage:   str   = Form(...),
    symptom_group:  str   = Form(...),
    severity:       str   = Form(...),
    affected_area:  str   = Form("unknown"),
    recent_rain:    str   = Form("unknown"),
    trap_count:     int   = Form(None),
    nearby_count:   int   = Form(0),      # NEW: real nearby-report count
    district:       str   = Form(""),
    taluka:         str   = Form(""),
    lat:            float = Form(12.97),
    lon:            float = Form(77.59),
    language:       str   = Form("en"),
    client_event_id: str  = Form(None),
    image: UploadFile = File(None),
):
    # ── Server-side validation ────────────────────────────────────────────────
    if crop not in VALID_CROPS:
        raise HTTPException(422, f"Invalid crop '{crop}'. Supported: {', '.join(sorted(VALID_CROPS))}")
    if growth_stage not in VALID_STAGES:
        raise HTTPException(422, f"Invalid growth_stage '{growth_stage}'.")
    if symptom_group not in VALID_SYMPTOMS:
        raise HTTPException(422, f"Invalid symptom_group '{symptom_group}'.")
    if severity not in VALID_SEVERITIES:
        raise HTTPException(422, f"Invalid severity '{severity}'.")

    obs_id   = str(uuid.uuid4())
    ev_id    = client_event_id or str(uuid.uuid4())
    now_str  = _now()
    db       = get_db()

    try:
        # ── Idempotency ──────────────────────────────────────────────────────
        existing = db.execute(
            "SELECT id FROM observations WHERE client_event_id=?", (ev_id,)
        ).fetchone()
        if existing:
            return JSONResponse({"observation_id": existing["id"], "duplicate": True})

        # ── Image handling ────────────────────────────────────────────────────
        quality_result = {"passed": True, "quality_state": "NO_IMAGE", "message": "No image submitted."}
        media_id       = None
        image_bytes    = None
        media_row      = None

        if image and image.filename:
            image_bytes = await image.read()
            mime        = image.content_type or "image/jpeg"
            quality_result = check_quality(image_bytes, mime)

            if quality_result["passed"]:
                sha   = hashlib.sha256(image_bytes).hexdigest()
                ext   = mime.split("/")[-1].replace("jpeg", "jpg")
                fname = f"{obs_id}.{ext}"
                path  = os.path.join(UPLOAD_DIR, fname)
                with open(path, "wb") as f:
                    f.write(image_bytes)
                media_id  = str(uuid.uuid4())
                media_row = (media_id, obs_id, fname, sha, mime,
                             quality_result.get("width"), quality_result.get("height"),
                             quality_result["quality_state"],
                             quality_result.get("blur_score"), quality_result.get("brightness"),
                             now_str)

        # ── Invalid image bail ────────────────────────────────────────────────
        if image_bytes and not quality_result["passed"]:
            db.execute(
                """INSERT INTO observations
                   (id,client_event_id,created_at,updated_at,district,taluka,lat,lon,
                    crop,growth_stage,symptom_group,severity,affected_area,recent_rain,
                    trap_count,nearby_count,language,status,review_required,triage_score,
                    decision,human_action,reasoning,rule_version,weather_json,created_source)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (obs_id, ev_id, now_str, now_str, district, taluka, lat, lon,
                 crop, growth_stage, symptom_group, severity, affected_area, recent_rain,
                 trap_count, nearby_count, language, "invalid_input", 0, 0.0, "retake_image",
                 ACTIONS["retake_image"].get(language, ACTIONS["retake_image"]["en"]),
                 quality_result["message"], RULE_VERSION, '{}', "LIVE")
            )
            db.commit()
            return _build_response(obs_id, "invalid_input", 0.0, "retake_image",
                                   ACTIONS["retake_image"].get(language, ACTIONS["retake_image"]["en"]),
                                   quality_result["message"], False, quality_result, {}, language)

        # ── AI Inference ──────────────────────────────────────────────────────
        model_result = {"provider": "NO_IMAGE", "confidence": None, "decision": None,
                        "review_required": False, "top_k": []}
                        
        if crop != "tomato":
            # For upcoming crops, bypass model completely and force review
            model_result = {
                "provider": "BYPASSED_UNSUPPORTED_CROP", 
                "confidence": 0.0, 
                "decision": "Unknown",
                "review_required": True, 
                "top_k": []
            }
        elif image_bytes and quality_result["passed"]:
            model_result = await run_inference(image_bytes)

        # ── Weather ───────────────────────────────────────────────────────────
        weather = await get_weather(lat, lon)
        weather_json_str = json.dumps(weather) if weather else '{}'

        # ── Evidence Fusion ───────────────────────────────────────────────────
        fusion = fuse(
            symptom_group=symptom_group,
            growth_stage=growth_stage,
            severity=severity,
            weather=weather.get("current") if weather else None,
            trap_count=trap_count,
            nearby_count=nearby_count,          # NOW WIRED LIVE
            model_confidence=model_result.get("confidence"),
            model_decision=model_result.get("decision"),
            language=language,
        )

        status       = fusion["status"]
        triage_score = fusion["triage_score"]
        decision     = fusion["decision"]
        human_action = fusion["human_action"]
        reasoning    = fusion["reasoning"]
        review_req   = 1 if (fusion["review_required"] or model_result.get("review_required")) else 0
        
        if crop != "tomato":
            status = "expert"
            review_req = 1
            triage_score = 1.0
            
            # Use English fallback base strings - these will be translated by the UI's 'speak.text' 
            # if we wanted them completely translated, but we can just provide clear English here.
            human_action = ACTIONS["refer_to_expert"].get(language, ACTIONS["refer_to_expert"]["en"])
            reasoning = "Automatic AI screening is currently optimized for Tomato. Your observation has been flagged for manual review by a local agricultural officer."

        # ── Persist observation ───────────────────────────────────────────────
        db.execute(
            """INSERT INTO observations
               (id,client_event_id,created_at,updated_at,district,taluka,lat,lon,
                crop,growth_stage,symptom_group,severity,affected_area,recent_rain,
                trap_count,nearby_count,language,status,review_required,triage_score,
                decision,human_action,reasoning,rule_version,model_version,
                weather_json,created_source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (obs_id, ev_id, now_str, now_str, district, taluka, lat, lon,
             crop, growth_stage, symptom_group, severity, affected_area, recent_rain,
             trap_count, nearby_count, language, status, review_req, triage_score,
             decision, human_action, reasoning, RULE_VERSION,
             model_result.get("model_version", "none"),
             weather_json_str, "LIVE")
        )

        # ── Media asset (FK to observations now satisfied) ────────────────────
        if media_row:
            db.execute(
                """INSERT INTO media_assets
                   (id,observation_id,relative_path,sha256,mime_type,width,height,
                    quality_state,blur_score,brightness,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                media_row
            )

        # ── Model prediction ──────────────────────────────────────────────────
        if model_result.get("provider") not in ("NO_IMAGE",):
            db.execute(
                """INSERT INTO model_predictions
                   (id,observation_id,provider,model_version,top_k_json,confidence,
                    decision,review_required,generated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), obs_id,
                 model_result.get("provider", "FIXTURE"),
                 model_result.get("model_version", "?"),
                 json.dumps(model_result.get("top_k", [])),
                 model_result.get("confidence"),
                 model_result.get("decision"),
                 1 if model_result.get("review_required") else 0,
                 now_str)
            )

        # ── Evidence items — full audit trail per signal ──────────────────────
        evidence_breakdown = fusion.get("evidence_breakdown", {})
        for ev_type, ev_data in evidence_breakdown.items():
            db.execute(
                """INSERT INTO evidence_items
                   (id,observation_id,evidence_type,value_json,source,
                    fetched_at,freshness_state,signal_score,available)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), obs_id, ev_type,
                 json.dumps({"score": ev_data.get("score"), "weight": ev_data.get("weight")}),
                 "computed", now_str, "fresh", ev_data.get("score"), 1)
            )

        # ── Audit event ───────────────────────────────────────────────────────
        db.execute(
            "INSERT INTO audit_events (id,entity_type,entity_id,event_type,actor_role,payload_json,created_at) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), "observation", obs_id, "CREATED", "farmer",
             json.dumps({"status": status, "score": triage_score}), now_str)
        )
        db.commit()

        return _build_response(obs_id, status, triage_score, decision, human_action,
                               reasoning, fusion["review_required"],
                               quality_result, model_result, language,
                               weather=weather, fusion=fusion)

    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        try:
            db.close()
        except Exception:
            pass


@router.get("/observations/{obs_id}")
def get_observation(obs_id: str):
    db  = get_db()
    row = db.execute("SELECT * FROM observations WHERE id=?", (obs_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "Observation not found")

    media     = db.execute("SELECT * FROM media_assets WHERE observation_id=?", (obs_id,)).fetchone()
    pred      = db.execute("SELECT * FROM model_predictions WHERE observation_id=? ORDER BY generated_at DESC LIMIT 1", (obs_id,)).fetchone()
    reviews   = db.execute("SELECT * FROM reviews WHERE observation_id=? ORDER BY created_at DESC", (obs_id,)).fetchall()
    followups = db.execute("SELECT * FROM followups WHERE observation_id=? ORDER BY created_at DESC", (obs_id,)).fetchall()
    audits    = db.execute("SELECT * FROM audit_events WHERE entity_id=? ORDER BY created_at", (obs_id,)).fetchall()
    ev_items  = db.execute("SELECT * FROM evidence_items WHERE observation_id=? ORDER BY evidence_type", (obs_id,)).fetchall()
    db.close()

    obs      = dict(row)
    lang     = obs.get("language", "en")
    score    = obs.get("triage_score") or 0.0
    symptom  = obs.get("symptom_group", "")
    stage    = obs.get("growth_stage", "")
    severity = obs.get("severity", "")

    # ── Restore weather from persisted JSON ───────────────────────────────────
    try:
        obs["weather"] = json.loads(obs.get("weather_json") or "{}")
    except Exception:
        obs["weather"] = {}

    # ── Reconstruct evidence — prefer stored evidence_items, fall back to signal fns
    from backend.services.evidence_fusion import (
        _weather_signal, _severity_signal, _trap_signal, _nearby_signal,
    )
    from backend.config import SYMPTOM_SIGNAL, STAGE_VULNERABILITY

    if ev_items:
        # Use actually-stored evidence scores (exact values used at decision time)
        ev_map = {r["evidence_type"]: r["signal_score"] for r in ev_items}
        evidence = {
            "symptom":  round(ev_map.get("symptom",  SYMPTOM_SIGNAL.get(symptom, 0.5)), 2),
            "stage":    round(ev_map.get("stage",    STAGE_VULNERABILITY.get(stage, 0.5)), 2),
            "weather":  round(ev_map.get("weather",  0.5), 2),
            "severity": round(ev_map.get("severity", _severity_signal(severity)), 2),
            "trap":     round(ev_map.get("trap",     _trap_signal(obs.get("trap_count"))), 2),
            "nearby":   round(ev_map.get("nearby",   _nearby_signal(obs.get("nearby_count", 0))), 2),
        }
    else:
        # Legacy rows — reconstruct from stored fields
        wx_json = obs.get("weather", {})
        wx_curr = wx_json.get("current") if isinstance(wx_json, dict) else None
        wx_s    = _weather_signal(wx_curr) if wx_curr else 0.5
        evidence = {
            "symptom":  round(SYMPTOM_SIGNAL.get(symptom, 0.5), 2),
            "stage":    round(STAGE_VULNERABILITY.get(stage, 0.5), 2),
            "weather":  round(wx_s, 2),
            "severity": round(_severity_signal(severity), 2),
            "trap":     round(_trap_signal(obs.get("trap_count")), 2),
            "nearby":   round(_nearby_signal(obs.get("nearby_count", 0)), 2),
        }

    # ── Build rich report content ──────────────────────────────────────────────
    from backend.config import ACTIONS
    decision    = obs.get("decision", "")
    action_text = obs.get("human_action") or ACTIONS.get(decision, {}).get(lang, "")

    SEV_MAP = {
        "en": {"almost_all":"Almost All Plants","many":"Many Plants","few":"A Few Plants","unknown":"Unknown"},
        "kn": {"almost_all":"ಬಹುತೇಕ ಎಲ್ಲ ಸಸ್ಯಗಳು","many":"ಹೆಚ್ಚು ಸಸ್ಯಗಳು","few":"ಕೆಲವು ಸಸ್ಯಗಳು","unknown":"ಗೊತ್ತಿಲ್ಲ"},
        "hi": {"almost_all":"लगभग सभी पौधे","many":"बहुत से पौधे","few":"कुछ पौधे","unknown":"अज्ञात"},
    }
    STAGE_MAP = {
        "en": {"seedling":"Seedling","vegetative":"Vegetative","flowering":"Flowering","fruiting":"Fruiting","maturity":"Maturity"},
        "kn": {"seedling":"ಮೊಳಕೆ","vegetative":"ಸಸ್ಯ ಬೆಳವಣಿಗೆ","flowering":"ಹೂ ಬಿಡುವ","fruiting":"ಕಾಯಿ ಕಟ್ಟುವ","maturity":"ಮಾಗಿದ"},
        "hi": {"seedling":"अंकुर","vegetative":"पत्ते बढ़ना","flowering":"फूल आना","fruiting":"फल लगना","maturity":"कटाई"},
    }
    CROP_MAP = {
        "en": {"tomato":"Tomato","potato":"Potato","corn_maize":"Corn","grape":"Grape",
               "bell_pepper":"Bell Pepper","strawberry":"Strawberry","orange":"Orange",
               "soybean":"Soybean","apple":"Apple","other":"Other"},
        "kn": {"tomato":"ಟೊಮೇಟೊ","potato":"ಆಲೂಗಡ್ಡೆ","corn_maize":"ಮೆಕ್ಕೆ ಜೋಳ","grape":"ದ್ರಾಕ್ಷಿ",
               "bell_pepper":"ಕ್ಯಾಪ್ಸಿಕಂ","strawberry":"ಸ್ಟ್ರಾಬೆರಿ","orange":"ಕಿತ್ತಳೆ",
               "soybean":"ಸೋಯಾಬೀನ್","apple":"ಸೇಬು","other":"ಇತರೆ"},
        "hi": {"tomato":"टमाटर","potato":"आलू","corn_maize":"मक्का","grape":"अंगूर",
               "bell_pepper":"शिमला मिर्च","strawberry":"स्ट्रॉबेरी","orange":"संतरा",
               "soybean":"सोयाबीन","apple":"सेब","other":"अन्य"},
    }
    SYM_MAP = {
        "en": {"leaf_spots":"Leaf Spots","yellowing":"Yellowing","wilting":"Wilting",
               "leaf_curling":"Leaf Curling","holes":"Holes/Eaten","powder_coating":"White Powder",
               "stem_rot":"Stem Rot","holes_or_chewing":"Holes/Chewing","none_visible":"None Visible"},
        "kn": {"leaf_spots":"ಎಲೆ ಕಲೆ","yellowing":"ಹಳದಿ ಆಗುವಿಕೆ","wilting":"ಬಾಡುವಿಕೆ",
               "leaf_curling":"ಎಲೆ ಸುರುಳಿ","holes":"ರಂಧ್ರ","powder_coating":"ಬಿಳಿ ಹಿಟ್ಟು",
               "stem_rot":"ಕಾಂಡ ಕೊಳೆ","holes_or_chewing":"ರಂಧ್ರ / ತಿಂದ","none_visible":"ಕಾಣದು"},
        "hi": {"leaf_spots":"पत्ती धब्बे","yellowing":"पीला पड़ना","wilting":"मुरझाना",
               "leaf_curling":"पत्ती मुड़ना","holes":"छेद","powder_coating":"सफेद चूर्ण",
               "stem_rot":"तने का सड़ना","holes_or_chewing":"छेद / खाया","none_visible":"कोई नहीं"},
    }

    crop_name  = CROP_MAP.get(lang, CROP_MAP["en"]).get(obs.get("crop",""), obs.get("crop",""))
    stage_name = STAGE_MAP.get(lang, STAGE_MAP["en"]).get(stage, stage)
    sev_name   = SEV_MAP.get(lang, SEV_MAP["en"]).get(severity, severity)
    sym_name   = SYM_MAP.get(lang, SYM_MAP["en"]).get(symptom, symptom)

    STEPS = {
        "en": [
            "🔍 Isolate affected plants to prevent spread",
            "✂️ Remove and bag infected leaves immediately — do NOT compost",
            "💧 Avoid overhead watering — use drip or base watering only",
            "🧪 Apply the recommended fungicide/pesticide as per dosage",
            "📋 Monitor daily for 7 days and record changes",
            "📞 Contact your local KVK officer if symptoms worsen",
        ],
        "kn": [
            "🔍 ಹರಡುವಿಕೆ ತಡೆಯಲು ಬಾಧಿತ ಸಸ್ಯಗಳನ್ನು ಬೇರ್ಪಡಿಸಿ",
            "✂️ ರೋಗಪೀಡಿತ ಎಲೆಗಳನ್ನು ತಕ್ಷಣ ತೆಗೆದು ಚೀಲದಲ್ಲಿ ಹಾಕಿ — ಗೊಬ್ಬರ ಮಾಡಬೇಡಿ",
            "💧 ಮೇಲಿಂದ ನೀರು ಹಾಕಬೇಡಿ — ತೊಟ್ಟಿ ನೀರಾವರಿ ಅಥವಾ ಬೇರಿನ ಬಳಿ ನೀರು ಹಾಕಿ",
            "🧪 ಶಿಫಾರಸು ಮಾಡಿದ ಪ್ರಮಾಣದಲ್ಲಿ ಶಿಲೀಂಧ್ರ/ಕೀಟ ನಾಶಕ ಸಿಂಪಡಿಸಿ",
            "📋 7 ದಿನ ಪ್ರತಿದಿನ ಗಮನಿಸಿ ಮತ್ತು ಬದಲಾವಣೆ ದಾಖಲಿಸಿ",
            "📞 ರೋಗ ಹೆಚ್ಚಿದರೆ ಸ್ಥಳೀಯ KVK ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ",
        ],
        "hi": [
            "🔍 फैलाव रोकने के लिए प्रभावित पौधों को अलग करें",
            "✂️ संक्रमित पत्तियों को तुरंत हटाएं और बैग में बंद करें — खाद न बनाएं",
            "💧 ऊपर से पानी न दें — ड्रिप या जड़ के पास पानी दें",
            "🧪 अनुशंसित मात्रा में कवकनाशी/कीटनाशक का छिड़काव करें",
            "📋 7 दिन रोज़ निगरानी करें और बदलाव दर्ज करें",
            "📞 लक्षण बिगड़ने पर स्थानीय KVK अधिकारी से संपर्क करें",
        ],
    }

    PREVENTION = {
        "en": [
            "🌿 Rotate crops every season to break disease cycles",
            "🌅 Water in the morning — wet leaves overnight cause fungal growth",
            "📏 Maintain plant spacing (30-45 cm) for good air circulation",
            "🌱 Use certified disease-free seeds from trusted suppliers",
            "🪲 Scout your field weekly — check underside of leaves for pests",
        ],
        "kn": [
            "🌿 ರೋಗ ಚಕ್ರ ಮುರಿಯಲು ಪ್ರತಿ ಹಂಗಾಮಿನಲ್ಲಿ ಬೆಳೆ ತಿರುಗಿಸಿ",
            "🌅 ಬೆಳಿಗ್ಗೆ ನೀರು ಹಾಕಿ — ರಾತ್ರಿ ತೇವ ಶಿಲೀಂಧ್ರ ಬೆಳೆಸುತ್ತದೆ",
            "📏 ಉತ್ತಮ ಗಾಳಿ ಸಂಚಾರಕ್ಕೆ ಸಸ್ಯ ಅಂತರ (30-45 ಸೆಮಿ) ಕಾಪಾಡಿ",
            "🌱 ವಿಶ್ವಾಸಾರ್ಹ ಮೂಲದಿಂದ ಪ್ರಮಾಣಿತ ರೋಗ-ಮುಕ್ತ ಬೀಜ ಬಳಸಿ",
            "🪲 ವಾರಕ್ಕೊಮ್ಮೆ ಜಮೀನು ತಪಾಸಣೆ ಮಾಡಿ — ಎಲೆ ಹಿಂಭಾಗ ಪರೀಕ್ಷಿಸಿ",
        ],
        "hi": [
            "🌿 बीमारी के चक्र को तोड़ने के लिए हर मौसम में फसल बदलें",
            "🌅 सुबह पानी दें — रात में गीली पत्तियाँ फफूंद को बढ़ावा देती हैं",
            "📏 अच्छी हवा के लिए पौधों के बीच 30-45 सेमी की दूरी रखें",
            "🌱 विश्वसनीय स्रोत से प्रमाणित रोग-मुक्त बीज उपयोग करें",
            "🪲 हर सप्ताह खेत की जांच करें — पत्तियों के नीचे कीट देखें",
        ],
    }

    # Model scope disclaimer (always show in result)
    crop_val = obs.get("crop", "")
    is_tomato = crop_val == "tomato"
    model_scope = {
        "crop_scope":       _MODEL_SCOPE["crop_scope"],
        "test_accuracy_pct": int(_MODEL_SCOPE["test_accuracy"] * 100),
        "release_status":   _MODEL_SCOPE["release_status"],
        "field_validation": _MODEL_SCOPE["field_validation"],
        "scope_match":      is_tomato,   # True = crop matches trained scope
        "warning":          None if is_tomato else
            f"⚠️ Model trained on Tomato only — results for '{crop_val}' are forwarded to expert review.",
    }

    rich = {
        "crop_display":    crop_name,
        "stage_display":   stage_name,
        "severity_display": sev_name,
        "symptom_display": sym_name,
        "steps_to_take":   STEPS.get(lang, STEPS["en"]),
        "prevention_tips": PREVENTION.get(lang, PREVENTION["en"]),
        "evidence":        evidence,
        "location":        obs.get("location_label") or f"{obs.get('lat',0):.4f}°N, {obs.get('lon',0):.4f}°E",
        "model_scope":     model_scope,
        "evidence_items":  [dict(e) for e in ev_items],  # actual DB audit rows
    }

    return {
        "observation":  obs,
        "media":        dict(media) if media else None,
        "prediction":   dict(pred)  if pred  else None,
        "reviews":      [dict(r) for r in reviews],
        "followups":    [dict(f) for f in followups],
        "audit_trail":  [dict(a) for a in audits],
        "rich":         rich,
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

"""
PestPulse — Officer API
GET   /api/v1/officer/queue                             — paginated case queue
PATCH /api/v1/officer/observations/{id}/review          — officer review action
POST  /api/v1/followups                                 — record follow-up
"""
import uuid, json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.db import get_db

router = APIRouter(prefix="/api/v1")


def _now():
    return datetime.now(timezone.utc).isoformat()


# ── Officer queue ─────────────────────────────────────────────────────────────
@router.get("/officer/queue")
def get_queue(
    status:    str = None,
    district:  str = None,
    crop:      str = None,
    severity:  str = None,
    page:      int = 1,
    page_size: int = 20,
):
    db   = get_db()
    sql  = "SELECT * FROM observations WHERE 1=1"
    args = []
    if status:   sql += " AND status=?";   args.append(status)
    if district: sql += " AND district=?"; args.append(district)
    if crop:     sql += " AND crop=?";     args.append(crop)
    if severity: sql += " AND severity=?"; args.append(severity)
    sql += " ORDER BY review_required DESC, triage_score DESC, created_at ASC"
    sql += f" LIMIT {page_size} OFFSET {(page-1)*page_size}"

    rows  = db.execute(sql, args).fetchall()
    total = db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    db.close()
    return {"total": total, "page": page, "items": [dict(r) for r in rows]}


# ── Officer stats summary ─────────────────────────────────────────────────────
@router.get("/officer/stats")
def get_stats():
    db = get_db()
    needs_review = db.execute("SELECT COUNT(*) FROM observations WHERE review_required=1 AND status != 'resolved'").fetchone()[0]
    severe       = db.execute("SELECT COUNT(*) FROM observations WHERE severity IN ('almost_all','many') AND review_required=1").fetchone()[0]
    followup_due = db.execute("SELECT COUNT(*) FROM followups WHERE outcome IS NULL AND due_at < ?", (_now(),)).fetchone()[0]
    total        = db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    db.close()
    return {
        "needs_review":  needs_review,
        "severe_cases":  severe,
        "followup_due":  followup_due,
        "total_cases":   total,
    }


# ── Officer review action ─────────────────────────────────────────────────────
class ReviewRequest(BaseModel):
    decision:          str
    corrected_symptom: str = None
    action_code:       str = None
    referral_target:   str = None
    note:              str = ""
    followup_due_days: int = 3
    idempotency_key:   str = None


@router.patch("/officer/observations/{obs_id}/review")
def submit_review(obs_id: str, body: ReviewRequest):
    db  = get_db()
    row = db.execute("SELECT * FROM observations WHERE id=?", (obs_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "Observation not found")

    # Check idempotency
    if body.idempotency_key:
        existing = db.execute(
            "SELECT id FROM reviews WHERE observation_id=? AND id=?",
            (obs_id, body.idempotency_key)
        ).fetchone()
        if existing:
            db.close()
            return JSONResponse({"duplicate": True, "observation_id": obs_id})

    rev_id  = body.idempotency_key or str(uuid.uuid4())
    now_str = _now()

    # Determine new status
    new_status = {
        "CONFIRM_MONITOR":   "monitor",
        "LOW_RISK_ACTION":   "low_risk_action",
        "CONFIRM_REVIEW":    "review_required",
        "REFER":             "review_required",
        "RESOLVED":          "resolved",
    }.get(body.decision, "review_required")

    db.execute(
        """INSERT INTO reviews
           (id,observation_id,reviewer_role,decision,corrected_symptom,action_code,
            referral_target,note,followup_days,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (rev_id, obs_id, "officer", body.decision,
         body.corrected_symptom, body.action_code,
         body.referral_target, body.note,
         body.followup_due_days, now_str)
    )
    db.execute("UPDATE observations SET status=?, updated_at=?, review_required=? WHERE id=?",
               (new_status, now_str, 0, obs_id))

    # Auto-create follow-up record
    if body.followup_due_days > 0:
        due = (datetime.now(timezone.utc) + timedelta(days=body.followup_due_days)).isoformat()
        db.execute(
            "INSERT INTO followups (id,observation_id,due_at,created_at) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), obs_id, due, now_str)
        )

    db.execute(
        "INSERT INTO audit_events (id,entity_type,entity_id,event_type,actor_role,payload_json,created_at) VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "observation", obs_id, "REVIEWED", "officer",
         json.dumps(body.model_dump()), now_str)
    )
    db.commit()
    db.close()
    return {"observation_id": obs_id, "new_status": new_status, "review_id": rev_id}


# ── Follow-up ─────────────────────────────────────────────────────────────────
class FollowupRequest(BaseModel):
    observation_id: str
    outcome:        str   # IMPROVED | STABLE | WORSE | UNCLEAR
    note:           str = ""


@router.post("/followups")
def record_followup(body: FollowupRequest):
    db  = get_db()
    row = db.execute("SELECT id FROM observations WHERE id=?", (body.observation_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "Observation not found")

    now_str = _now()
    fid = str(uuid.uuid4())
    db.execute(
        "INSERT OR IGNORE INTO followups (id,observation_id,due_at,outcome,note,created_at) VALUES (?,?,?,?,?,?)",
        (fid, body.observation_id, now_str, body.outcome, body.note, now_str)
    )
    new_status = "resolved" if body.outcome in ("IMPROVED","STABLE") else "unresolved"
    db.execute("UPDATE observations SET status=?, updated_at=? WHERE id=?",
               (new_status, now_str, body.observation_id))
    db.execute(
        "INSERT INTO audit_events (id,entity_type,entity_id,event_type,actor_role,payload_json,created_at) VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), "followup", body.observation_id, "FOLLOWUP_RECORDED", "farmer",
         json.dumps({"outcome": body.outcome}), now_str)
    )
    db.commit()
    db.close()
    return {"followup_id": fid, "new_status": new_status}

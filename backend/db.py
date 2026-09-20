"""
PestPulse — Database setup (SQLite via sqlite3 directly, no ORM needed for demo)
"""
import sqlite3
import os
from backend.config import DATABASE_URL

DB_PATH = DATABASE_URL.replace("sqlite:///", "")

def get_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")   # wait up to 10s if locked
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS observations (
        id              TEXT PRIMARY KEY,
        client_event_id TEXT UNIQUE,
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL,
        farmer_label    TEXT DEFAULT 'Anonymous',
        district        TEXT,
        taluka          TEXT,
        location_label  TEXT,
        lat             REAL,
        lon             REAL,
        crop            TEXT,
        growth_stage    TEXT,
        symptom_group   TEXT,
        severity        TEXT,
        affected_area   TEXT,
        trap_count      INTEGER,
        nearby_count    INTEGER DEFAULT 0,
        recent_rain     TEXT,
        language        TEXT DEFAULT 'en',
        status          TEXT DEFAULT 'monitor',
        review_required INTEGER DEFAULT 0,
        triage_score    REAL,
        decision        TEXT,
        human_action    TEXT,
        reasoning       TEXT,
        rule_version    TEXT,
        model_version   TEXT,
        created_source  TEXT DEFAULT 'LIVE',
        weather_json    TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS media_assets (
        id              TEXT PRIMARY KEY,
        observation_id  TEXT REFERENCES observations(id),
        relative_path   TEXT,
        sha256          TEXT,
        mime_type       TEXT,
        width           INTEGER,
        height          INTEGER,
        quality_state   TEXT,
        blur_score      REAL,
        brightness      REAL,
        created_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS model_predictions (
        id                   TEXT PRIMARY KEY,
        observation_id       TEXT REFERENCES observations(id),
        provider             TEXT,
        model_version        TEXT,
        top_k_json           TEXT,
        confidence           REAL,
        decision             TEXT,
        review_required      INTEGER DEFAULT 0,
        generated_at         TEXT
    );

    CREATE TABLE IF NOT EXISTS evidence_items (
        id              TEXT PRIMARY KEY,
        observation_id  TEXT REFERENCES observations(id),
        evidence_type   TEXT,
        value_json      TEXT,
        source          TEXT,
        fetched_at      TEXT,
        freshness_state TEXT,
        signal_score    REAL,
        available       INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id              TEXT PRIMARY KEY,
        observation_id  TEXT REFERENCES observations(id),
        reviewer_role   TEXT,
        decision        TEXT,
        corrected_symptom TEXT,
        action_code     TEXT,
        referral_target TEXT,
        note            TEXT,
        followup_days   INTEGER DEFAULT 3,
        created_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS followups (
        id              TEXT PRIMARY KEY,
        observation_id  TEXT REFERENCES observations(id),
        due_at          TEXT,
        outcome         TEXT,
        note            TEXT,
        created_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS audit_events (
        id              TEXT PRIMARY KEY,
        entity_type     TEXT,
        entity_id       TEXT,
        event_type      TEXT,
        actor_role      TEXT,
        payload_json    TEXT,
        created_at      TEXT
    );
    """)
    conn.commit()
    conn.close()
    print("[DB] Tables ready.")

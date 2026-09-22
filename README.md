# 🌿 PestPulse

> **Evidence-led crop disease triage for smallholder farmers.**  
> Snap a leaf photo. Get a risk score, recommended action, and expert routing — in your language, in seconds.

[![Python](https://img.shields.io/badge/Python-3.11.8-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-CPU-orange?logo=tensorflow)](https://www.tensorflow.org/)
[![Deployed on Render](https://img.shields.io/badge/Deployed-Render-46E3B7?logo=render)](https://render.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 The Problem

India's smallholder farmers lose **₹90,000 crore+** annually to preventable crop diseases. By the time symptoms are visible, damage is often widespread. The existing advisory chain — farmer → village agent → KVK officer — is too slow, too expensive, and inaccessible in regional languages.

**PestPulse** bridges this gap with an AI-first, evidence-fused triage system that:
- Gives an instant risk verdict from a single leaf photo
- Combines visual AI with on-ground evidence (weather, growth stage, trap counts, nearby cases)
- Routes uncertain cases directly to the right expert officer
- Works in **English, Kannada, and Hindi** — with voice output

---

## ✨ Key Features

### 🧠 Dual-Layer Intelligence
| Layer | What it does |
|---|---|
| **Computer Vision (TF SavedModel)** | Classifies leaf image against 4 trained tomato disease classes with confidence score |
| **Evidence Fusion Engine** | Combines symptom group, growth stage, weather (Open-Meteo live API), trap counts, nearby cases, and model confidence into a single weighted triage score |

### 📋 3-Step Farmer Workflow
1. **Snap** — Upload or capture a leaf photo. Image quality gate rejects blurry/dark/overexposed images before wasting inference.
2. **Confirm** — AI auto-fills crop, symptom, and severity. Farmer ticks ✅ to accept or corrects manually.
3. **Submit** — Full evidence-fused report with risk score, recommended action, and reasoning.

### 🎯 Triage Outcomes
| Score | Status | Action |
|---|---|---|
| < 0.45 | 🟢 Monitor | Re-check in 3 days |
| 0.45–0.70 | 🟡 Low-Risk Action | Inspect, isolate, improve drainage |
| > 0.70 | 🔴 Expert Review | Auto-routed to KVK / agriculture officer |

### 👮 Officer Dashboard
- Real-time queue of pending expert reviews
- Evidence breakdown per case (symptom, stage, weather, AI result)
- Approve / Close / Escalate workflow
- District-level aggregated alerts

### 🔊 Multilingual Voice Reports
- Full report read-aloud using **gTTS** (Google Translate TTS) as primary
- **Bhashini** (India's national AI translation platform) as optional upgrade
- Proper Kannada and Hindi pronunciation — not browser Web Speech
- One-tap Listen / Stop on the result page

### 📍 Field Intelligence
- **Live weather** pulled from Open-Meteo (no API key required) at submission coordinates
- **Soil data** (type, pH, texture) for agronomic context
- **Nearby cases counter** — number of disease reports within 10 km, factored into risk score

### 🌐 Localization
| Feature | en | kn | hi |
|---|:---:|:---:|:---:|
| Full UI | ✅ | ✅ | ✅ |
| Voice TTS | ✅ | ✅ | ✅ |
| Crop names | ✅ | ✅ | ✅ |
| Actions | ✅ | ✅ | ✅ |

### 📱 Progressive Web App
- Installable on mobile homescreen (PWA manifest + service worker)
- Separate **📸 Take Photo** and **🖼 Upload from Gallery** buttons — no forced camera-only on mobile
- Responsive UI — works identically on desktop and phone browser

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────┐
│                  FRONTEND                     │
│  index.html  ─  Landing / Login               │
│  farmer.html ─  3-Step Observation Wizard     │
│  result.html ─  Evidence Report + TTS         │
│  officer.html ─ Review Dashboard              │
│  static/app.js ─ Shared API client + ASR/TTS  │
└────────────────────┬─────────────────────────┘
                     │  REST API (FastAPI)
┌────────────────────▼─────────────────────────┐
│                  BACKEND                      │
│                                               │
│  api/observations.py  POST  /api/v1/obs       │
│  api/quick_infer.py   POST  /api/v1/quick-infer│
│  api/voice.py         POST  /api/v1/voice/tts │
│  api/officer.py       GET   /api/v1/officer/* │
│  api/field_intel.py   GET   /api/v1/field/*   │
│  api/agri_tools.py    GET   /api/v1/agri/*    │
│                                               │
│  services/inference.py    ─ TF model runner   │
│  services/evidence_fusion.py ─ Score engine   │
│  services/quality_gate.py ─ Image validation  │
│  services/weather.py      ─ Open-Meteo fetch  │
│  services/soil.py         ─ Soil lookup       │
│  services/agri_tables.py  ─ Pesticide DB      │
│                                               │
│  db.py  ─  SQLite (local) / PostgreSQL (prod) │
└──────────────────────────────────────────────┘
```

---

## 🤖 AI Model

| Property | Value |
|---|---|
| Architecture | CNN (TensorFlow SavedModel) |
| Trained on | PlantVillage dataset subset |
| Active classes | Tomato — Bacterial Spot, Early Blight, Septoria Leaf Spot, Target Spot |
| Input | 224×224 RGB leaf image |
| Output | Class probabilities + top-K predictions |
| Inference chain | Local TF model → Gradio remote session (fallback) |
| Quality gate | Blur detection (Laplacian variance), brightness check, resolution check |

> **Crop scope note:** The trained model is currently optimized for Tomato disease detection. Submissions for other crops are automatically routed to expert review without running the model, preventing false confidence on unsupported classes. Additional crops are planned for future training cycles (see [Roadmap](#-roadmap)).

---

## 🗂️ Project Structure

```
PestPulse/
├── backend/
│   ├── api/
│   │   ├── observations.py    # Core POST/GET for farmer submissions
│   │   ├── quick_infer.py     # Step-1 instant AI preview (before form submit)
│   │   ├── voice.py           # TTS (gTTS + Bhashini) and ASR endpoints
│   │   ├── officer.py         # Officer dashboard API
│   │   ├── field_intel.py     # Weather, soil, nearby-cases intelligence
│   │   ├── agri_tools.py      # Pesticide / input advisory lookup
│   │   └── providers.py       # External service status
│   ├── services/
│   │   ├── inference.py       # TF model loader and runner
│   │   ├── evidence_fusion.py # Weighted triage scoring engine
│   │   ├── quality_gate.py    # Image pre-validation
│   │   ├── weather.py         # Open-Meteo integration
│   │   ├── soil.py            # Soil data service
│   │   └── agri_tables.py     # Crop/pest/pesticide database
│   ├── model/active/          # TF SavedModel + manifest + labels
│   ├── data/                  # SQLite DB + uploaded images
│   ├── config.py              # All thresholds, crop lists, translations
│   ├── db.py                  # Database init and schema
│   ├── main.py                # FastAPI app entry point
│   └── requirements.txt
├── frontend/
│   ├── index.html             # Landing page
│   ├── farmer.html            # Farmer observation wizard
│   ├── result.html            # Evidence report with TTS
│   ├── officer.html           # Officer review dashboard
│   ├── login.html             # Login screen
│   ├── sw.js                  # Service worker (PWA offline cache)
│   └── static/
│       ├── app.js             # Shared API client, TTS, ASR, i18n
│       ├── farmer.js          # Farmer wizard logic
│       ├── officer.js         # Officer dashboard logic
│       ├── style.css          # Design system (dark theme)
│       └── manifest.json      # PWA manifest
├── .python-version            # Pins Python 3.11.8 for Render
├── render.yaml                # Render Blueprint config
└── .env.example               # Environment variable reference
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.11.x
- Git

### 1. Clone and install
```bash
git clone https://github.com/prajwalmrprajwal62-sys/Pest-Pluse-SIH-.git
cd Pest-Pluse-SIH-

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r backend/requirements.txt
```

### 2. Configure environment (optional)
```bash
cp .env.example .env
# Edit .env to set any keys you have
```

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./backend/data/pestpulse.db` | SQLite local or PostgreSQL prod |
| `DEMO_MODE` | `true` | Disables auth for demo testing |
| `OPEN_METEO_ENABLED` | `true` | Live weather fetch |
| `BHASHINI_API_KEY` | _(empty)_ | Optional — gTTS is used when not set |
| `BHASHINI_USER_ID` | _(empty)_ | Optional |
| `GRADIO_URL` | _(empty)_ | Optional remote model session |

### 3. Run
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 5001 --reload
```

Open `http://localhost:5001` in your browser.

Interactive API docs available at `http://localhost:5001/docs`.

---

## ☁️ Deployment (Render)

The project is configured for single-click deployment using Render Blueprints.

1. Fork this repo.
2. Go to [Render Dashboard](https://dashboard.render.com) → **New → Blueprint**.
3. Connect your fork.
4. Render reads `render.yaml` and auto-configures the service with Python 3.11.8.
5. Click **Apply**.

> **Important:** TensorFlow requires Python 3.11. The `.python-version` file and `PYTHON_VERSION` env var in `render.yaml` both pin this. If you redeploy after a failed build, use **"Clear build cache & deploy"** to avoid Render reusing a stale Python 3.13 environment.

---

## 📡 API Reference

All routes are prefixed `/api/v1/`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/observations` | Submit a full farmer observation |
| `GET` | `/observations/{id}` | Fetch result by ID |
| `POST` | `/quick-infer` | Step-1 AI preview (image only, no DB write) |
| `POST` | `/voice/tts` | Text-to-speech (gTTS / Bhashini) |
| `POST` | `/voice/asr` | Speech-to-text (Bhashini) |
| `GET` | `/voice/status` | Voice service health |
| `GET` | `/officer/queue` | Pending review cases |
| `POST` | `/officer/{id}/action` | Approve / escalate a review |
| `GET` | `/field/weather` | Live weather at lat/lon |
| `GET` | `/field/soil` | Soil data for coordinates |
| `GET` | `/agri/recommendations/{crop}/{disease}` | Pesticide/input advisory |

Full interactive documentation: `/docs` (Swagger UI)

---

## 🗺️ Roadmap

### ✅ Built (Current)
- [x] 3-step farmer observation wizard with AI auto-fill
- [x] TF CNN inference — 4 Tomato disease classes (PlantVillage)
- [x] Evidence Fusion Engine — 6-signal weighted triage score
- [x] Image quality gate (blur + brightness + resolution)
- [x] Live weather context from Open-Meteo (free, no API key)
- [x] Officer review dashboard with escalation workflow
- [x] Multilingual UI — English, Kannada, Hindi
- [x] Voice TTS — gTTS backend (proper regional language pronunciation)
- [x] Bhashini ASR/TTS integration (ready, optional API key)
- [x] PWA — installable on mobile, offline cache
- [x] Mobile camera + gallery upload (separate buttons)
- [x] Nearby cases counter in risk calculation
- [x] Pesticide / agrochemical advisory lookup
- [x] Soil data context
- [x] Render cloud deployment with auto-deploy on GitHub push

### 🔜 Upcoming Crops (Model Training)
- [ ] Potato — Late Blight, Early Blight
- [ ] Corn / Maize — Common Rust, Northern Leaf Blight
- [ ] Grape — Black Rot
- [ ] Rice, Wheat (Phase 2)

### 🔧 Planned Software
- [ ] PostgreSQL migration for multi-tenant production
- [ ] Push notifications to officer when new review arrives
- [ ] Farmer history — view all past scans
- [ ] Crop calendar integration
- [ ] Geospatial heatmap of disease spread by district

### 🔩 Hardware Integration (Future Scope)
The architecture is designed to accept data from physical IoT sensors as additional evidence signals. Planned integrations:

| Sensor | Purpose | Evidence Signal |
|---|---|---|
| **IoT Pheromone Trap** | Automatic pest count detection via camera | `trap_count` |
| **Soil Moisture Sensor** | Real-time root zone moisture | Weather/drainage context |
| **Leaf Wetness Sensor** | Fungal infection risk predictor | Weather signal boost |
| **Raspberry Pi / ESP32 Edge Node** | On-device inference at field with no internet | Offline TF Lite model |
| **LoRa Gateway** | Low-power long-range data from remote fields | Field-level telemetry |

The `trap_count` field in the observation schema is already live and feeds the Evidence Fusion Engine — any hardware that can POST a count to `/api/v1/observations` integrates immediately.

---

## 🧩 Evidence Fusion — How the Score Works

```
triage_score = Σ (signal × weight)

Signals:
  symptom_signal   × 0.25   (leaf_spots=0.75, yellowing=0.55, wilting=0.65 …)
  stage_signal     × 0.20   (flowering=0.80, seedling=0.70, maturity=0.40 …)
  weather_signal   × 0.20   (humidity% + precipitation_mm from Open-Meteo)
  trap_signal      × 0.15   (0 traps=0.05 → >20 traps=0.90)
  severity_signal  × 0.10   (few=0.35, many=0.70, almost_all=0.95)
  nearby_signal    × 0.10   (0 cases=0.10 → >5 cases=0.85)

AI model confidence overrides:
  confidence < 0.80  → forces review_required = True
  crop != tomato     → bypasses model, forces expert routing
```

All weights and thresholds live in `backend/config.py` — adjustable without touching business logic.

---

## 👥 Team

**Team Paryavaran** · Team ID: 159209

| Role | Member |
|---|---|
| Team Lead | Prajwal M R |
| Development | Team Paryavaran |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ for Indian farmers · PestPulse by Team Paryavaran</sub>
</div>

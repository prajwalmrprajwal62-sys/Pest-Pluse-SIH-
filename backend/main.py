"""
PestPulse — FastAPI main entry point
Serves API + static frontend from a single process (Render-friendly)
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.db import init_db
from backend.api.observations import router as obs_router
from backend.api.officer import router as officer_router
from backend.api.providers import router as provider_router
from backend.api.quick_infer import router as infer_router
from backend.api.voice import router as voice_router
from backend.api.field_intel import router as field_router

app = FastAPI(
    title="PestPulse",
    description="Evidence-led crop disease triage API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register API routers ───────────────────────────────────────────────────────
app.include_router(obs_router)
app.include_router(officer_router)
app.include_router(provider_router)
app.include_router(infer_router)
app.include_router(voice_router)
app.include_router(field_router)

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    os.makedirs("./backend/data/uploads", exist_ok=True)
    init_db()
    print("[PestPulse] Ready.")

# ── Serve uploaded media ───────────────────────────────────────────────────────
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./backend/data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")

# ── Serve frontend static files ───────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
STATIC_DIR   = os.path.join(FRONTEND_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ── Frontend HTML routes ───────────────────────────────────────────────────────
def _html(name: str):
    path = os.path.join(FRONTEND_DIR, name)
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/",               include_in_schema=False)
def home():            return _html("index.html")

@app.get("/farmer",         include_in_schema=False)
@app.get("/farmer.html",    include_in_schema=False)
def farmer():          return _html("farmer.html")

@app.get("/result",         include_in_schema=False)
@app.get("/result.html",    include_in_schema=False)
def result():          return _html("result.html")

@app.get("/login",          include_in_schema=False)
@app.get("/login.html",     include_in_schema=False)
def login():           return _html("login.html")

@app.get("/officer",        include_in_schema=False)
@app.get("/officer.html",   include_in_schema=False)
def officer():         return _html("officer.html")

@app.get("/sw.js",          include_in_schema=False)
def sw():              return FileResponse(os.path.join(FRONTEND_DIR, "sw.js"),
                                           media_type="application/javascript")

@app.get("/manifest.json",  include_in_schema=False)
def manifest():        return FileResponse(os.path.join(FRONTEND_DIR, "static", "manifest.json"),
                                           media_type="application/json")

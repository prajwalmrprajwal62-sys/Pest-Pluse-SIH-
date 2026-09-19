"""
PestPulse — Voice API Proxy
TTS priority:  gTTS (Google Translate, free, no key) → Web Speech API (browser)
ASR priority:  Bhashini (when key set) → Web Speech API (browser, en-IN continuous)

Bhashini slot is preserved — add BHASHINI_API_KEY to .env to enable it.
"""
import base64, io, logging
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from backend.config import (
    BHASHINI_API_KEY, BHASHINI_USER_ID,
    BHASHINI_PIPELINE_ID, BHASHINI_ENABLED,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/voice")

# ── Language codes ────────────────────────────────────────────
GTTS_LANG   = {"en": "en", "kn": "kn", "hi": "hi"}
BHASHINI_INFERENCE = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
BHASHINI_ASR_MODELS = {
    "kn": "ai4bharat/conformer-multilingual-dravidian-gpu--t4",
    "hi": "ai4bharat/conformer-hi-gpu--t4",
    "en": "whisper-medium-en--gpu--t4",
}
BHASHINI_TTS_MODELS = {
    "kn": "ai4bharat/indic-tts-coqui-dravidian-gpu--t4",
    "hi": "ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4",
    "en": "ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4",
}


# ─────────────────────────────────────────────────────────────
@router.get("/status")
def voice_status():
    return {
        "bhashini_enabled":   BHASHINI_ENABLED,
        "gtts_enabled":       True,
        "web_speech_fallback": True,
        "supported_langs":    ["en", "kn", "hi"],
        "tts_provider":       "Bhashini" if BHASHINI_ENABLED else "gTTS (Google Translate, free)",
        "asr_provider":       "Bhashini" if BHASHINI_ENABLED else "Web Speech API (browser, en-IN)",
        "note": "" if BHASHINI_ENABLED else (
            "Using gTTS for TTS (free). "
            "Set BHASHINI_API_KEY to upgrade to Bhashini for better Kannada/Hindi quality."
        ),
    }


# ─────────────────────────────────────────────────────────────
# TTS — Text → Audio
# ─────────────────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str
    lang: str = "kn"


@router.post("/tts")
async def tts(body: TTSRequest):
    """
    Convert text to speech audio (MP3 base64).
    Uses Bhashini if key set, otherwise gTTS (free, no key).
    """
    text = body.text.strip()
    lang = body.lang if body.lang in ("en", "kn", "hi") else "kn"

    if not text:
        raise HTTPException(400, "text is required")

    # ── Try Bhashini TTS first (if configured) ──────────────
    if BHASHINI_ENABLED:
        try:
            audio_b64 = await _bhashini_tts(text, lang)
            if audio_b64:
                return {
                    "audio_b64": audio_b64,
                    "format":    "wav",
                    "lang":      lang,
                    "provider":  "BHASHINI",
                }
        except Exception as e:
            log.warning("Bhashini TTS failed: %s — falling back to gTTS", e)

    # ── gTTS fallback (Google Translate TTS, free) ──────────
    audio_b64 = await _gtts_tts(text, lang)
    return {
        "audio_b64": audio_b64,
        "format":    "mp3",
        "lang":      lang,
        "provider":  "gTTS",
    }


async def _gtts_tts(text: str, lang: str) -> str:
    """Use gTTS (wraps Google Translate TTS). Returns MP3 as base64."""
    from gtts import gTTS
    lc  = GTTS_LANG.get(lang, "kn")
    tts = gTTS(text=text, lang=lc, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


async def _bhashini_tts(text: str, lang: str) -> str | None:
    """Bhashini TTS — returns WAV as base64, or None on failure."""
    payload = {
        "pipelineTasks": [{
            "taskType": "tts",
            "config": {
                "language":  {"sourceLanguage": lang},
                "serviceId": BHASHINI_TTS_MODELS.get(lang, BHASHINI_TTS_MODELS["kn"]),
                "gender":    "female",
            }
        }],
        "inputData": {"input": [{"source": text}]},
    }
    headers = {
        "Authorization": BHASHINI_API_KEY,
        "userID":        BHASHINI_USER_ID,
        "ulcaApiKey":    BHASHINI_API_KEY,
        "Content-Type":  "application/json",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(BHASHINI_INFERENCE, json=payload, headers=headers)
        r.raise_for_status()
        data  = r.json()
        audio = (data.get("pipelineResponse", [{}])[0]
                    .get("audio", [{}])[0]
                    .get("audioContent", ""))
        return audio or None


# ─────────────────────────────────────────────────────────────
# ASR — Audio → Transcript (Bhashini only; Web Speech handled client-side)
# ─────────────────────────────────────────────────────────────

@router.post("/asr")
async def asr(audio: UploadFile = File(...), lang: str = "kn"):
    """
    Bhashini ASR: audio file → transcript.
    Returns 503 if Bhashini not configured (use Web Speech API client-side).
    """
    if not BHASHINI_ENABLED:
        raise HTTPException(
            503,
            detail={
                "message": "Bhashini not configured. Use Web Speech API on client (already active).",
                "set_env":  "BHASHINI_API_KEY + BHASHINI_USER_ID",
            }
        )

    audio_bytes = await audio.read()
    audio_b64   = base64.b64encode(audio_bytes).decode()
    lang_code   = lang if lang in ("en", "kn", "hi") else "kn"
    model_id    = BHASHINI_ASR_MODELS.get(lang_code, BHASHINI_ASR_MODELS["kn"])

    payload = {
        "pipelineTasks": [{
            "taskType": "asr",
            "config": {
                "language":     {"sourceLanguage": lang_code},
                "serviceId":    model_id,
                "audioFormat":  "wav",
                "samplingRate": 16000,
            }
        }],
        "inputData": {"audio": [{"audioContent": audio_b64}]},
    }
    headers = {
        "Authorization": BHASHINI_API_KEY,
        "userID":        BHASHINI_USER_ID,
        "ulcaApiKey":    BHASHINI_API_KEY,
        "Content-Type":  "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.post(BHASHINI_INFERENCE, json=payload, headers=headers)
            r.raise_for_status()
            data       = r.json()
            transcript = (data.get("pipelineResponse", [{}])[0]
                              .get("output", [{}])[0]
                              .get("source", ""))
            return {"transcript": transcript, "lang": lang_code, "provider": "BHASHINI"}
    except Exception as e:
        raise HTTPException(502, f"Bhashini ASR error: {e}")

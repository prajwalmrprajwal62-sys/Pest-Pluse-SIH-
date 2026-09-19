"""
PestPulse — Inference Service
Priority: 1) Local TF SavedModel  2) Gradio live session  3) Fixture
"""
import os, json, logging
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

MODEL_DIR   = os.getenv("MODEL_DIR", "./backend/model/active")
GRADIO_URL  = os.getenv("GRADIO_URL", "")
DEMO_MODE   = os.getenv("DEMO_MODE", "true").lower() == "true"

# ── Label map for this model (4 tomato classes) ─────────────────────────────
_LABEL_MAP = None  # Loaded lazily

# ── TF model (loaded once) ───────────────────────────────────────────────────
_tf_model    = None
_tf_manifest = None
_model_state = "NOT_LOADED"

# Disease → auto_fill mapping (crop + symptom + severity)
_DISEASE_AUTOFILL = {
    "Tomato___Bacterial_spot":    {"crop": "tomato", "symptom_group": "leaf_spots",    "severity": "many"},
    "Tomato___Early_blight":      {"crop": "tomato", "symptom_group": "leaf_spots",    "severity": "many"},
    "Tomato___Septoria_leaf_spot":{"crop": "tomato", "symptom_group": "leaf_spots",    "severity": "few"},
    "Tomato___Target_Spot":       {"crop": "tomato", "symptom_group": "leaf_spots",    "severity": "few"},
    "Potato___Early_Blight":      {"crop": "potato", "symptom_group": "leaf_spots",    "severity": "many"},
    "Potato___Late_blight":       {"crop": "potato", "symptom_group": "leaf_spots",    "severity": "almost_all"},
    "Potato___healthy":           {"crop": "potato", "symptom_group": "none_visible",  "severity": "unknown"},
    "Tomato___healthy":           {"crop": "tomato", "symptom_group": "none_visible",  "severity": "unknown"},
    "Corn___Common_rust_":        {"crop": "corn_maize","symptom_group":"powder_coating","severity":"many"},
    "Corn___Northern_Leaf_Blight":{"crop": "corn_maize","symptom_group":"leaf_spots",  "severity":"many"},
    "Grape___Black_rot":          {"crop": "grape",  "symptom_group": "leaf_spots",    "severity": "many"},
}

_DISPLAY_NAMES = {
    "Tomato___Bacterial_spot":     "Tomato — Bacterial Spot",
    "Tomato___Early_blight":       "Tomato — Early Blight",
    "Tomato___Septoria_leaf_spot": "Tomato — Septoria Leaf Spot",
    "Tomato___Target_Spot":        "Tomato — Target Spot",
    "Tomato___healthy":            "Tomato — Healthy",
    "Potato___Early_Blight":       "Potato — Early Blight",
    "Potato___Late_blight":        "Potato — Late Blight",
    "Potato___healthy":            "Potato — Healthy",
    "Corn___Common_rust_":         "Corn — Common Rust",
    "Corn___Northern_Leaf_Blight": "Corn — Northern Leaf Blight",
    "Grape___Black_rot":           "Grape — Black Rot",
}


def _load_model():
    global _tf_model, _tf_manifest, _model_state, _LABEL_MAP
    if _model_state != "NOT_LOADED":
        return

    saved_model_dir = os.path.join(MODEL_DIR, "model_saved_model")
    manifest_path   = os.path.join(MODEL_DIR, "model_manifest.json")
    labels_path     = os.path.join(MODEL_DIR, "labels.json")

    if not os.path.isdir(saved_model_dir):
        log.warning("TF model not found at %s — using FIXTURE", saved_model_dir)
        _model_state = "FIXTURE"
        return

    try:
        import tensorflow as tf
        log.info("Loading TF SavedModel from %s …", saved_model_dir)
        _tf_model    = tf.saved_model.load(saved_model_dir)
        _tf_manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
        _LABEL_MAP   = json.load(open(labels_path))   if os.path.exists(labels_path) else {}
        _model_state = "TF_LOCAL"
        log.info("✅ TF model loaded — classes: %s", _tf_manifest.get("class_names", []))
    except Exception as e:
        log.warning("TF load failed: %s — using FIXTURE", e)
        _model_state = "FIXTURE"


def _preprocess_image(img_bytes: bytes):
    """Preprocess to (1,224,224,3) float32 using MobileNetV2 scaling."""
    import io
    import tensorflow as tf
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB").resize((224, 224), Image.BILINEAR)
    arr = np.array(img, dtype=np.float32)
    # MobileNetV2 preprocess: scale [0,255] → [-1,1]
    arr = (arr / 127.5) - 1.0
    return tf.constant(arr[np.newaxis], dtype=tf.float32)


def _run_tf(img_bytes: bytes) -> dict:
    """Run TF SavedModel inference. Returns top-1 result dict."""
    import tensorflow as tf
    tensor  = _preprocess_image(img_bytes)
    infer   = _tf_model.signatures["serving_default"]
    result  = infer(image=tensor)
    logits  = list(result.values())[0].numpy()[0]
    probs   = tf.nn.softmax(logits).numpy()
    top_i   = int(np.argmax(probs))
    classes = _tf_manifest.get("class_names", [])
    top_class = classes[top_i] if top_i < len(classes) else "unknown"
    return {
        "class_id":     top_class,
        "display_name": _DISPLAY_NAMES.get(top_class, top_class.replace("___"," — ")),
        "confidence":   float(probs[top_i]),
        "top_k": [
            {
                "class_id":     classes[i],
                "display_name": _DISPLAY_NAMES.get(classes[i], classes[i]),
                "confidence":   float(probs[i]),
            }
            for i in np.argsort(probs)[::-1][:3] if i < len(classes)
        ],
        "provider": "TF_LOCAL",
    }


async def _run_gradio(img_bytes: bytes, url: str) -> dict | None:
    """Try the Gradio live endpoint. Returns None if unavailable."""
    import base64, httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            b64 = base64.b64encode(img_bytes).decode()
            r   = await client.post(url, json={"data": [b64]})
            r.raise_for_status()
            data = r.json()
            return data.get("data", [None])[0]
    except Exception:
        return None


FIXTURE_RESULT = {
    "class_id":     "Tomato___Early_blight",
    "display_name": "Tomato — Early Blight",
    "confidence":   0.72,
    "top_k": [
        {"class_id":"Tomato___Early_blight",       "display_name":"Tomato — Early Blight",        "confidence":0.72},
        {"class_id":"Tomato___Bacterial_spot",      "display_name":"Tomato — Bacterial Spot",       "confidence":0.18},
        {"class_id":"Tomato___Septoria_leaf_spot",  "display_name":"Tomato — Septoria Leaf Spot",   "confidence":0.10},
    ],
    "provider": "FIXTURE",
}


async def run_inference(img_bytes: bytes) -> dict:
    """Main inference entry point — TF → Gradio → Fixture."""
    _load_model()

    if _model_state == "TF_LOCAL":
        try:
            return _run_tf(img_bytes)
        except Exception as e:
            log.warning("TF inference error: %s — falling back", e)

    if GRADIO_URL:
        g = await _run_gradio(img_bytes, GRADIO_URL)
        if g:
            return g

    return FIXTURE_RESULT


def get_model_status() -> dict:
    _load_model()
    return {
        "state":         _model_state,
        "provider":      _model_state,
        "classes":       _tf_manifest.get("class_names", []) if _tf_manifest else ["FIXTURE"],
        "accuracy":      0.795 if _model_state == "TF_LOCAL" else None,
        "demo_mode":     DEMO_MODE,
    }


def get_autofill(class_id: str) -> dict:
    """Return auto-fill fields for a given class_id."""
    return _DISEASE_AUTOFILL.get(class_id, {})

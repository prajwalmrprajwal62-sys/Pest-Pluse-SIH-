"""
PestPulse — Quick Inference endpoint
POST /api/v1/quick-infer — takes image, returns auto-detected fields
Used by farmer page to auto-fill form on image upload
"""
from fastapi import APIRouter, UploadFile, File
from backend.services.inference import run_inference, get_autofill
from backend.services.quality_gate import check_quality

router = APIRouter(prefix="/api/v1")


@router.post("/quick-infer")
async def quick_infer(image: UploadFile = File(...)):
    """
    Auto-detect disease from image.
    Returns prediction + auto_fill fields for crop, symptom_group, severity.
    """
    image_bytes = await image.read()
    mime        = image.content_type or "image/jpeg"

    # Quality gate
    quality = check_quality(image_bytes, mime)
    if not quality["passed"]:
        return {
            "quality":    quality,
            "auto_fill":  {},
            "prediction": {},
            "status":     "quality_failed",
            "message":    quality["message"],
        }

    # Run real model inference
    pred = await run_inference(image_bytes)

    # Top-1 result
    top  = pred.get("top_k", [{}])[0] if pred.get("top_k") else {}
    cls  = top.get("class_id") or pred.get("class_id", "unknown")
    conf = top.get("confidence") or pred.get("confidence", 0.0)
    name = top.get("display_name") or pred.get("display_name", "Unknown")

    # Get auto-fill from inference service (disease → crop + symptom + severity)
    auto_fill = get_autofill(cls)

    # Adjust severity based on confidence if not set by disease map
    if "severity" not in auto_fill:
        if   conf > 0.85: auto_fill["severity"] = "many"
        elif conf > 0.65: auto_fill["severity"] = "few"

    return {
        "quality":     quality,
        "prediction":  {
            "class_id":     cls,
            "display_name": name,
            "confidence":   round(conf, 3),
            "top_k":        pred.get("top_k", []),
        },
        "auto_fill":   auto_fill,
        "provider":    pred.get("provider", "FIXTURE"),
        "status":      "ok",
        "disclaimer":  "AI auto-fill is a suggestion — you can correct any field.",
    }

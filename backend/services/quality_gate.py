"""
PestPulse — Image Quality Gate
Checks blur, brightness, dimensions, and MIME type before inference.
"""
import io
from PIL import Image, ImageStat
import numpy as np
from backend.config import (
    IMAGE_MIN_WIDTH, IMAGE_MIN_HEIGHT, IMAGE_MAX_MB,
    BLUR_THRESHOLD, BRIGHTNESS_MIN, BRIGHTNESS_MAX,
)

ALLOWED_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


def _laplacian_variance(pil_img: Image.Image) -> float:
    """Higher = sharper. Below BLUR_THRESHOLD = too blurry.
    Pure numpy — no scipy required."""
    gray = np.array(pil_img.convert("L"), dtype=np.float32)
    # Apply simple Laplacian via slicing (avoids scipy dependency)
    lap = (
        -gray[:-2, 1:-1] - gray[2:, 1:-1]
        - gray[1:-1, :-2] - gray[1:-1, 2:]
        + 4 * gray[1:-1, 1:-1]
    )
    return float(np.var(lap))


def _mean_brightness(pil_img: Image.Image) -> float:
    stat = ImageStat.Stat(pil_img.convert("L"))
    return stat.mean[0]


def check_quality(image_bytes: bytes, mime_type: str) -> dict:
    """
    Returns:
      {
        "passed": bool,
        "quality_state": "GOOD" | "BLURRY" | "TOO_DARK" | "TOO_BRIGHT" | "TOO_SMALL" | "INVALID_FORMAT",
        "message": str,
        "width": int | None,
        "height": int | None,
        "blur_score": float | None,
        "brightness": float | None,
      }
    """
    if mime_type.lower() not in ALLOWED_MIMES:
        return _fail("INVALID_FORMAT", "Unsupported file type. Use JPEG, PNG, or WebP.")

    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > IMAGE_MAX_MB:
        return _fail("INVALID_FORMAT", f"File too large ({size_mb:.1f} MB). Max {IMAGE_MAX_MB} MB.")

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        img = Image.open(io.BytesIO(image_bytes))  # re-open after verify
    except Exception as e:
        return _fail("INVALID_FORMAT", f"Could not decode image: {e}")

    w, h = img.size

    if w < IMAGE_MIN_WIDTH or h < IMAGE_MIN_HEIGHT:
        return _fail("TOO_SMALL", f"Image is {w}×{h}px. Minimum is {IMAGE_MIN_WIDTH}×{IMAGE_MIN_HEIGHT}px.", w, h)

    blur  = _laplacian_variance(img)
    brite = _mean_brightness(img)

    if blur < BLUR_THRESHOLD:
        return {**_fail("BLURRY", "Image is too blurry. Hold steady and retake.", w, h), "blur_score": blur, "brightness": brite}

    if brite < BRIGHTNESS_MIN:
        return {**_fail("TOO_DARK", "Image is too dark. Retake in better lighting.", w, h), "blur_score": blur, "brightness": brite}

    if brite > BRIGHTNESS_MAX:
        return {**_fail("TOO_BRIGHT", "Image is overexposed. Retake avoiding direct sunlight.", w, h), "blur_score": blur, "brightness": brite}

    return {
        "passed": True,
        "quality_state": "GOOD",
        "message": "Image looks usable.",
        "width": w, "height": h,
        "blur_score": round(blur, 2),
        "brightness": round(brite, 2),
    }


def _fail(state: str, msg: str, w=None, h=None) -> dict:
    return {
        "passed": False,
        "quality_state": state,
        "message": msg,
        "width": w, "height": h,
        "blur_score": None, "brightness": None,
    }

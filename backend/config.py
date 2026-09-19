"""
PestPulse — Central Configuration
All thresholds, crop lists, language strings, and rules live here.
"""

import os

# ── App identity ─────────────────────────────────────────────────────────────
APP_NAME       = "PestPulse"
APP_VERSION    = "1.0.0"
RULE_VERSION   = "pestpulse-rules-v1"

# ── Deployment ────────────────────────────────────────────────────────────────
DATABASE_URL   = os.getenv("DATABASE_URL", "sqlite:///./backend/data/pestpulse.db")
UPLOAD_DIR     = os.getenv("UPLOAD_DIR", "./backend/data/uploads")
MODEL_DIR      = os.getenv("MODEL_DIR",  "./backend/model/active")
GRADIO_URL     = os.getenv("GRADIO_URL", "")          # Set if Colab session is live
DEMO_MODE      = os.getenv("DEMO_MODE", "true").lower() == "true"

# ── Open-Meteo ────────────────────────────────────────────────────────────────
OPEN_METEO_ENABLED         = os.getenv("OPEN_METEO_ENABLED", "true").lower() == "true"
OPEN_METEO_TIMEOUT_SECONDS = int(os.getenv("OPEN_METEO_TIMEOUT_SECONDS", "5"))
WEATHER_CACHE_MINUTES      = 30
DEFAULT_LAT                = 12.97
DEFAULT_LON                = 77.59
DEFAULT_LOCATION_LABEL     = "Bengaluru"

# ── Bhashini Voice API ────────────────────────────────────────────────────────
BHASHINI_API_KEY           = os.getenv("BHASHINI_API_KEY", "")
BHASHINI_USER_ID           = os.getenv("BHASHINI_USER_ID", "")
BHASHINI_PIPELINE_ID       = os.getenv("BHASHINI_PIPELINE_ID", "64392f96daac500b55c543cd")
BHASHINI_ENABLED           = bool(BHASHINI_API_KEY)


# ── Image quality gate ────────────────────────────────────────────────────────
IMAGE_MIN_WIDTH    = 150   # Model resizes to 224 — any real phone photo is fine
IMAGE_MIN_HEIGHT   = 150
IMAGE_MAX_MB       = 20
BLUR_THRESHOLD     = 50.0   # Laplacian variance below this = blurry
BRIGHTNESS_MIN     = 20
BRIGHTNESS_MAX     = 240

# ── Triage thresholds ─────────────────────────────────────────────────────────
MONITOR_THRESHOLD = 0.45
REVIEW_THRESHOLD  = 0.70
CONFIDENCE_REVIEW_BELOW = 0.80   # AI confidence below this → REVIEW state

# ── Evidence weights ──────────────────────────────────────────────────────────
WEIGHTS = {
    "symptom":  0.25,
    "stage":    0.20,
    "weather":  0.20,
    "trap":     0.15,
    "severity": 0.10,
    "nearby":   0.10,
}

# ── Symptom risk signals ──────────────────────────────────────────────────────
SYMPTOM_SIGNAL = {
    "leaf_spots":      0.75,
    "yellowing":       0.55,
    "leaf_curling":    0.60,
    "holes_or_chewing":0.70,
    "wilting":         0.65,
    "powder_coating":  0.72,
    "none_visible":    0.05,
}

# ── Stage vulnerability ───────────────────────────────────────────────────────
STAGE_VULNERABILITY = {
    "seedling":   0.70,
    "vegetative": 0.50,
    "flowering":  0.80,
    "fruiting":   0.75,
    "maturity":   0.40,
}

# ── Supported crops (PlantVillage 14) ─────────────────────────────────────────
SUPPORTED_CROPS = [
    "tomato", "potato", "apple", "corn_maize", "grape",
    "bell_pepper", "cherry", "orange", "peach", "strawberry",
    "blueberry", "raspberry", "soybean", "squash",
]

CROP_DISPLAY = {
    "en": {
        "tomato":"Tomato","potato":"Potato","apple":"Apple",
        "corn_maize":"Corn / Maize","grape":"Grape","bell_pepper":"Bell Pepper",
        "cherry":"Cherry","orange":"Orange","peach":"Peach",
        "strawberry":"Strawberry","blueberry":"Blueberry","raspberry":"Raspberry",
        "soybean":"Soybean","squash":"Squash / Pumpkin",
    },
    "kn": {
        "tomato":"ಟೊಮೇಟೊ","potato":"ಆಲೂಗಡ್ಡೆ","apple":"ಸೇಬು",
        "corn_maize":"ಮೆಕ್ಕೆ ಜೋಳ","grape":"ದ್ರಾಕ್ಷಿ","bell_pepper":"ಕ್ಯಾಪ್ಸಿಕಂ",
        "cherry":"ಚೆರ್ರಿ","orange":"ಕಿತ್ತಳೆ","peach":"ಪೀಚ್",
        "strawberry":"ಸ್ಟ್ರಾಬೆರಿ","blueberry":"ಬ್ಲೂಬೆರಿ","raspberry":"ರಾಸ್‌ಬೆರಿ",
        "soybean":"ಸೋಯಾಬೀನ್","squash":"ಕುಂಬಳಕಾಯಿ",
    },
    "hi": {
        "tomato":"टमाटर","potato":"आलू","apple":"सेब",
        "corn_maize":"मक्का","grape":"अंगूर","bell_pepper":"शिमला मिर्च",
        "cherry":"चेरी","orange":"संतरा","peach":"आड़ू",
        "strawberry":"स्ट्रॉबेरी","blueberry":"ब्लूबेरी","raspberry":"रसभरी",
        "soybean":"सोयाबीन","squash":"कद्दू",
    },
}

# ── Output state translations ─────────────────────────────────────────────────
OUTPUT_STATES = {
    "monitor": {
        "en": "Monitor & Resample",
        "kn": "ಗಮನಿಸಿ ಮತ್ತು ಮರುಪರಿಶೀಲಿಸಿ",
        "hi": "निगरानी करें और पुनः जाँचें",
    },
    "low_risk_action": {
        "en": "Low-Risk Action",
        "kn": "ಕಡಿಮೆ ಅಪಾಯದ ಕ್ರಮ",
        "hi": "कम जोखिम वाली कार्रवाई",
    },
    "review_required": {
        "en": "Expert Review Required",
        "kn": "ತಜ್ಞರ ಪರಿಶೀಲನೆ ಅಗತ್ಯ",
        "hi": "विशेषज्ञ समीक्षा आवश्यक",
    },
    "invalid_input": {
        "en": "Invalid Input",
        "kn": "ಅಮಾನ್ಯ ಒಳಸೇರಿಕೆ",
        "hi": "अमान्य इनपुट",
    },
    "source_unavailable": {
        "en": "Data Unavailable",
        "kn": "ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ",
        "hi": "डेटा उपलब्ध नहीं",
    },
}

# ── Action descriptions (human_action) ───────────────────────────────────────
ACTIONS = {
    "monitor_and_resample": {
        "en": "Monitor the field for 3 days. Collect a clearer photo if symptoms worsen.",
        "kn": "3 ದಿನಗಳ ಕಾಲ ಹೊಲ ಗಮನಿಸಿ. ರೋಗಲಕ್ಷಣ ಹೆಚ್ಚಾದರೆ ಸ್ಪಷ್ಟ ಫೋಟೋ ತೆಗೆದು ಕಳುಹಿಸಿ.",
        "hi": "3 दिनों तक खेत की निगरानी करें। लक्षण बिगड़ने पर स्पष्ट फ़ोटो लें।",
    },
    "inspect_and_remove": {
        "en": "Inspect affected plants. Remove and destroy affected material. Improve ventilation.",
        "kn": "ಬಾಧಿತ ಸಸ್ಯಗಳನ್ನು ಪರಿಶೀಲಿಸಿ. ಬಾಧಿತ ಭಾಗಗಳನ್ನು ತೆಗೆದು ನಾಶಪಡಿಸಿ. ಗಾಳಿಯ ಚಲನೆ ಸುಧಾರಿಸಿ.",
        "hi": "प्रभावित पौधों की जाँच करें। प्रभावित हिस्सों को हटाएं और नष्ट करें।",
    },
    "improve_drainage": {
        "en": "Check root zone for waterlogging. Improve field drainage. Avoid chemical use without expert confirmation.",
        "kn": "ಬೇರಿನ ಭಾಗದಲ್ಲಿ ನೀರು ನಿಲ್ಲುವಿಕೆ ಪರಿಶೀಲಿಸಿ. ಚರಂಡಿ ವ್ಯವಸ್ಥೆ ಸುಧಾರಿಸಿ.",
        "hi": "जड़ क्षेत्र में जलभराव जाँचें। जल निकासी सुधारें।",
    },
    "refer_to_expert": {
        "en": "Case referred for expert review. Contact your local KVK or agriculture officer.",
        "kn": "ಪ್ರಕರಣವನ್ನು ತಜ್ಞ ಪರಿಶೀಲನೆಗಾಗಿ ಕಳುಹಿಸಲಾಗಿದೆ. ಸ್ಥಳೀಯ KVK ಅಥವಾ ಕೃಷಿ ಅಧಿಕಾರಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "hi": "मामला विशेषज्ञ समीक्षा के लिए भेजा गया। अपने स्थानीय KVK से संपर्क करें।",
    },
    "retake_image": {
        "en": "Image quality is too low. Please retake in good lighting with the leaf filling the frame.",
        "kn": "ಚಿತ್ರದ ಗುಣಮಟ್ಟ ತುಂಬಾ ಕಡಿಮೆ. ಒಳ್ಳೆಯ ಬೆಳಕಿನಲ್ಲಿ ಎಲೆ ಚೌಕಟ್ಟನ್ನು ತುಂಬುವ ರೀತಿ ಮತ್ತೆ ತೆಗೆಯಿರಿ.",
        "hi": "छवि गुणवत्ता बहुत कम है। अच्छी रोशनी में पत्ती को फ्रेम में भरकर दोबारा लें।",
    },
}

# ── KVK Expert contacts (Karnataka) ─────────────────────────────────────────
KVK_CONTACTS = [
    {"name": "KVK Bengaluru Urban",   "phone": "080-23411506", "district": "Bengaluru"},
    {"name": "KVK Tumkur",            "phone": "0816-2278489", "district": "Tumkur"},
    {"name": "KVK Ramanagara",        "phone": "080-27274020", "district": "Ramanagara"},
    {"name": "KVK Kolar",             "phone": "08152-243344", "district": "Kolar"},
    {"name": "KVK Chikkaballapur",    "phone": "08156-272153", "district": "Chikkaballapur"},
]

# ── Market prices (mock — APMC Bengaluru) ─────────────────────────────────────
MARKET_PRICES = [
    {"crop": "Tomato",       "price": "₹1,800/Quintal", "trend": "up"},
    {"crop": "Potato",       "price": "₹1,200/Quintal", "trend": "stable"},
    {"crop": "Corn / Maize", "price": "₹1,650/Quintal", "trend": "down"},
    {"crop": "Bell Pepper",  "price": "₹3,200/Quintal", "trend": "up"},
]

import os
from pathlib import Path

# Base directory of the backend package
BASE_DIR = Path(__file__).resolve().parent

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
SECRET_KEY = os.getenv("SECRET_KEY", "emergency-intelligence-yolo-secret-key-2026")

# CORS configuration: Allow requests from Vercel frontend and local development servers
CORS_ORIGINS_ENV = os.getenv("CORS_ALLOWED_ORIGINS", "*")
if CORS_ORIGINS_ENV == "*":
    CORS_ORIGINS = "*"
else:
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",") if origin.strip()]

# Storage paths (Relative to backend folder)
DATA_DIR = BASE_DIR / "data"
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"
SNAPSHOT_FOLDER = OUTPUT_FOLDER / "snapshots"
MODELS_DIR = BASE_DIR / "models"

# Ensure all runtime directories exist
for folder in [DATA_DIR, UPLOAD_FOLDER, OUTPUT_FOLDER, SNAPSHOT_FOLDER, MODELS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Database path (SQLite file stored in data directory)
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "emergency_intelligence.db")))

# YOLO Model configuration
DEFAULT_MODEL_NAME = "yolov8n.pt"
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(MODELS_DIR / DEFAULT_MODEL_NAME)))

# Detection & AI settings
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.35))
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", 0.45))

# COCO Class IDs relevant to road traffic emergency detection:
# 0: person, 1: bicycle, 2: car, 3: motorcycle, 5: bus, 7: truck
TARGET_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

# Collision Risk Analysis parameters
COLLISION_IOU_HIGH = 0.15          # Overlapping bounding box ratio indicating high collision risk
COLLISION_IOU_MEDIUM = 0.04        # Moderate bounding box overlap
COLLISION_PROXIMITY_HIGH_PX = 35   # Centroid distance (pixels) indicating immediate collision proximity
COLLISION_PROXIMITY_MED_PX = 75    # Centroid distance indicating close following/hazard
PEDESTRIAN_HAZARD_PROXIMITY_PX = 50 # Distance between vehicle and pedestrian triggering high risk

# Upload limits
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 Megabytes
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

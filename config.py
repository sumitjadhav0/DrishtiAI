"""config.py - Laptop slow asel tar fakt ethla PROFILE badla (kinva:  BLIND_PROFILE=light streamlit run app.py)

  light    : weak laptop (4 GB RAM / i3 / old CPU)    -> 3 models, lahan image, kami CPU
  balanced : normal laptop (8 GB RAM / i5)            -> 5 models   (DEFAULT)
  full     : strong laptop (16 GB RAM / i7 / Ryzen 7) -> sagale 7 models
Kontha profile suit hoto te  python benchmark.py  sangel."""
import os

PROFILE = os.environ.get("BLIND_PROFILE", "balanced").strip().lower()

PROFILES = {
    "light": dict(
        models=["YOLOv8n", "YOLO11n", "YOLOv5n"],
        imgsz=256, max_fps=5,  scene_every=8, ui_sleep=0.25, scene=True, stream_fps=12),
    "balanced": dict(
        models=["YOLOv5n", "YOLOv8n", "YOLOv9t", "YOLO11n", "YOLOv10n"],
        imgsz=320, max_fps=8,  scene_every=5, ui_sleep=0.15, scene=True, stream_fps=20),
    "full": dict(
        models=["YOLOv3-tiny", "YOLOv5n", "YOLOv8n", "YOLOv9t", "YOLOv10n", "YOLO11n", "YOLO12n"],
        imgsz=320, max_fps=10, scene_every=4, ui_sleep=0.10, scene=True, stream_fps=25),
}

_p = PROFILES[PROFILE]
MODELS = _p["models"]
IMG_SIZE = _p["imgsz"]
MAX_FPS = _p["max_fps"]            # CPU var jaast load nako mhanun detection speed cha upper limit
SCENE_EVERY = _p["scene_every"]    # jaga olakhnyacha interval (sec)
SCENE_ENABLED = _p["scene"]
UI_SLEEP = _p["ui_sleep"]
CPU_THREADS = max(1, min(4, (os.cpu_count() or 4) // 2))   # CPU chya ardhe cores

NAV_EVERY = 1.5          # route sangtana jaga tapasnyacha interval (sec)
WAYPOINT_GAP = 0.7       # jaga shikvtana 3 photos madhla antar (sec)

# ---- Live video (stream.py) ----
STREAM_FPS = _p["stream_fps"]                 # browser madhe video fps (inference pasun swatantra)
STREAM_PORT = int(os.environ.get("BLIND_PORT", 8765))
STREAM_LAN = os.environ.get("BLIND_STREAM_LAN", "0") == "1"   # 1 = phone/dusrya device var pan bagha (same Wi-Fi)
JPEG_QUALITY = 70
SHOW_BOXES = True                             # video var detection boxes

# ---- Camera: 0 / 1 (USB), kinva URL (glasses / phone IP camera / RTSP) ----
_cam = os.environ.get("BLIND_CAMERA", "0")
CAMERA_SOURCE = int(_cam) if _cam.isdigit() else _cam

# ---- Hardware: "cpu" (default) | "0" (NVIDIA GPU / Jetson) ----   Jetson: BLIND_DEVICE=0
DEVICE = os.environ.get("BLIND_DEVICE", "cpu")

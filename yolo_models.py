"""yolo_models.py - YOLO models + Round Robin (ek model load nahi zala tari baki chalatat)"""
import os
import time

import numpy as np
import torch
from ultralytics import YOLO

import config

torch.set_num_threads(config.CPU_THREADS)

IMG_SIZE = config.IMG_SIZE
CONF = 0.45      # kami confidence che (chukichi) results kadhun taka


def make_runner(weights):
    model = YOLO(weights)

    def run(frame):
        r = model.predict(frame, imgsz=IMG_SIZE, conf=CONF, device=config.DEVICE, verbose=False)[0]
        h, w = frame.shape[:2]
        out = []
        for b in r.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            out.append({"label": r.names[int(b.cls[0])], "conf": float(b.conf[0]),
                        "box": (x1 / w, y1 / h, x2 / w, y2 / h)})
        return out

    return run


# ---------- 7 Models sathi 7 vegle functions ----------
def load_yolov3_tiny(): return make_runner("yolov3-tinyu.pt")
def load_yolov5n():     return make_runner("yolov5nu.pt")
def load_yolov8n():     return make_runner("yolov8n.pt")
def load_yolov9t():     return make_runner("yolov9t.pt")
def load_yolov10n():    return make_runner("yolov10n.pt")
def load_yolo11n():     return make_runner("yolo11n.pt")
def load_yolo12n():     return make_runner("yolo12n.pt")


ALL_LOADERS = [
    ("YOLOv3-tiny", load_yolov3_tiny), ("YOLOv5n", load_yolov5n), ("YOLOv8n", load_yolov8n),
    ("YOLOv9t", load_yolov9t), ("YOLOv10n", load_yolov10n), ("YOLO11n", load_yolo11n),
    ("YOLO12n", load_yolo12n),
]
# config.py madhe nivadlele models
MODEL_LOADERS = [(n, f) for n, f in ALL_LOADERS if n in config.MODELS]

HAZARD_WEIGHTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hazards.pt")


class RoundRobin:
    def __init__(self):
        self.runners, self.failed = [], []
        dummy = np.zeros((IMG_SIZE, IMG_SIZE, 3), np.uint8)
        for name, loader in MODEL_LOADERS:
            try:
                runner = loader()
                runner(dummy)                       # warm-up: pahila frame slow nako
                self.runners.append((name, runner))
            except Exception as e:                  # download/version problem -> skip
                self.failed.append((name, str(e)[:100]))
                print(f"[WARN] {name} load zala nahi, skip kela: {e}")
        if not self.runners:
            raise RuntimeError("Ekhi YOLO model load zala nahi. Internet tapasa kinva: pip install -U ultralytics")
        self.hazard = None
        if os.path.exists(HAZARD_WEIGHTS):
            try:
                self.hazard = make_runner(HAZARD_WEIGHTS)
                self.hazard(dummy)
            except Exception as e:
                self.failed.append(("Hazard", str(e)[:100]))
                print(f"[WARN] Hazard model did not load; continuing without it: {e}")
        self.index = 0
        self.tick = 0

    def run_next(self, frame):
        self.tick += 1
        if self.hazard and self.tick % 2 == 0:
            name, runner = "Hazard", self.hazard
        else:
            name, runner = self.runners[self.index]
            self.index = (self.index + 1) % len(self.runners)
        t0 = time.time()
        detections = runner(frame)
        if name == "Hazard":
            # The merged annotations all use class 0, so old class-specific labels
            # are not trustworthy. Keep the alert name generic until data is remapped.
            for detection in detections:
                detection["label"] = "hazard"
        return {"model": name, "time": time.time(), "infer_ms": (time.time() - t0) * 1000,
                "detections": detections}

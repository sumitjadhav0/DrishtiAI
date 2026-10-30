"""Train the merged hazard detector: python train_hazards.py"""
import os
import shutil
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "datasets" / "hazards" / "data.yaml"
BASE_WEIGHTS = ROOT / "yolo11n.pt"
OUTPUT = ROOT / "hazards.pt"

if not DATA.is_file():
    raise FileNotFoundError(f"Hazard dataset config not found: {DATA}")
if not BASE_WEIGHTS.is_file():
    raise FileNotFoundError(f"Base model weights not found: {BASE_WEIGHTS}")

model = YOLO(str(BASE_WEIGHTS))
model.train(
    data=str(DATA),
    epochs=60,
    imgsz=320,
    device=os.environ.get("BLIND_DEVICE", "cpu"),
    batch=8,
    project=str(ROOT / "runs" / "detect"),
    name="hazard-train",
    exist_ok=True,
)

best = Path(model.trainer.best)
if not best.is_file():
    raise RuntimeError("Training finished without a best checkpoint; hazards.pt was not changed.")

temporary = OUTPUT.with_name(OUTPUT.name + ".tmp")
shutil.copy2(best, temporary)
os.replace(temporary, OUTPUT)
print(f"Done -> {OUTPUT}")

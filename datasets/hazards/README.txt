Hazard model (stairs / pothole) sathi data:

  images/train/*.jpg   labels/train/*.txt    <- 80% photos
  images/val/*.jpg     labels/val/*.txt      <- 20% photos (train madhe nako)

Pratek image sathi same nawacha .txt label file (YOLO format):  class cx cy w h  (0-1 madhe)
Labeling tool: Roboflow / LabelImg / CVAT (export "YOLOv8" format).
Pratek class che kamit kami 300+ photos ghya. Train zalyavar:  python train_hazards.py
Ani  runs/detect/train/weights/best.pt  chi copy  blind_assist/hazards.pt  mhanun thva.

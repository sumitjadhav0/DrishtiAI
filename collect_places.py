"""Tumchya college chya jagecha photos ghenyasathi:
    python collect_places.py classroom
SPACE = photo save, Q = bahercha. Pratek jagecha 8-10 photos (vegvegle kon / light) ghya."""
import os
import re
import sys
import time
import cv2

name = sys.argv[1] if len(sys.argv) > 1 else "classroom"
if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
    raise SystemExit("Place folder name must contain only letters, numbers, '_' or '-'.")
folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "places", name)
os.makedirs(folder, exist_ok=True)
cap = cv2.VideoCapture(0)
n = len(os.listdir(folder))
while True:
    ok, frame = cap.read()
    if not ok:
        break
    cv2.putText(frame, f"{name}: {n} saved | SPACE=save  Q=quit", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.imshow("collect", frame)
    k = cv2.waitKey(1) & 0xFF
    if k == 32:
        cv2.imwrite(os.path.join(folder, f"{int(time.time()*1000)}.jpg"), frame)
        n += 1
    elif k in (ord("q"), 27):
        break
cap.release()
cv2.destroyAllWindows()

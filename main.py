"""main.py - Streamlit shivay chalvne (glasses / Raspberry Pi / Jetson sathi).
    python main.py                          # camera 0, balanced profile
    python main.py --profile light --lang mr
    python main.py --camera http://192.168.1.50:8080/video      # glasses / phone camera stream
    python main.py --lan                    # phone var pan HUD bagha:  http://<laptop-ip>:8765
Ctrl+C = band."""
import argparse
import os
import time

ap = argparse.ArgumentParser()
ap.add_argument("--profile", choices=["light", "balanced", "full"])
ap.add_argument("--camera", help="0, 1 ... kinva URL/RTSP")
ap.add_argument("--lang", choices=["en", "hi", "mr"])
ap.add_argument("--lan", action="store_true", help="HUD dusrya device var pan (same Wi-Fi)")
ap.add_argument("--no-start", action="store_true", help="camera auto-start karu naka")
args = ap.parse_args()
if args.profile: os.environ["BLIND_PROFILE"] = args.profile
if args.camera: os.environ["BLIND_CAMERA"] = args.camera
if args.lan: os.environ["BLIND_STREAM_LAN"] = "1"

from pipeline import Pipeline          # noqa: E402  (env set zalyavar import)
from stream import StreamServer        # noqa: E402

p = Pipeline(args.lang)
srv = StreamServer(p).start()
print("\nMitra ready.  HUD: %s   (Ctrl+C = stop)\n" % srv.url())
if not args.no_start:
    p.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    p.stop()
    srv.stop()

"""Tumcha laptop kiti fast ahe te mojto ani konta PROFILE vapra te sangto:
    python benchmark.py"""
import time
import numpy as np
import psutil

import config
import yolo_models as ym

N = 15
frame = (np.random.rand(480, 640, 3) * 255).astype(np.uint8)
print(f"CPU cores: {psutil.cpu_count()}   RAM: {psutil.virtual_memory().total / 1e9:.1f} GB   "
      f"threads used: {config.CPU_THREADS}\n")

times = {}
for name, loader in ym.ALL_LOADERS:
    try:
        run = loader(); run(frame)
        t0 = time.time()
        for _ in range(N):
            run(frame)
        times[name] = (time.time() - t0) / N * 1000
        print(f"{name:12s} {times[name]:6.0f} ms / frame")
    except Exception as e:
        print(f"{name:12s} load failed: {str(e)[:70]}")

scene_ms = None
try:
    from scene import SceneRecognizer
    s = SceneRecognizer(); s._predict(frame)
    t0 = time.time(); s._predict(frame); scene_ms = (time.time() - t0) * 1000
    print(f"{'CLIP scene':12s} {scene_ms:6.0f} ms (pratek {config.SCENE_EVERY} sec la ek vela)")
except Exception as e:
    print("CLIP scene   skip:", str(e)[:70])

if times:
    avg = sum(times.values()) / len(times)
    print(f"\nSaravar (average) model: {avg:.0f} ms / frame")
    # Voting sathi ek cycle 1 second madhe pūrna zali pahije, 30% headroom thevun (camera, voice, UI sathi)
    fit = int(700 // avg)
    print(f"1 second madhe sadharan {fit} models cha cycle basto.")
    if fit >= 7:   rec = "full"
    elif fit >= 5: rec = "balanced"
    else:          rec = "light"
    print(f"\n==> Recommended profile: {rec}")
    print(f"    Windows:  set BLIND_PROFILE={rec} && streamlit run app.py")
    print(f"    Linux/Mac: BLIND_PROFILE={rec} streamlit run app.py")
    if avg > 250:
        print("    Tumcha laptop khup slow ahe: 'light' vapara, scene recognition band kara (config.py madhe scene=False)")

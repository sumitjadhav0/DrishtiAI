"""app.py (Streamlit) fake streamlit madhe chalavun tapasto"""
import sys, os, time, types, threading
exec(open("tests/test_all.py", encoding="utf-8").read().split("ok = fail = 0")[0])      # same stubs
import numpy as np
ok = fail = 0
def check(name, cond, extra=""):
    global ok, fail
    if cond: ok += 1; print("PASS", name)
    else: fail += 1; print("FAIL", name, extra)

import camera, config
LOC = {"v": 1}
class FakeCap:
    def read(self): time.sleep(0.03); return True, np.full((480, 640, 3), LOC["v"], np.uint8)
    def release(self): pass
camera.open_camera = lambda i=None, **k: FakeCap()
V = np.eye(6, dtype="float32")
class FakeScene:
    def embed(self, f): v = V[int(f[0, 0, 0])] + 0.03 * np.random.randn(6).astype("float32"); return (v / np.linalg.norm(v)).astype("float32")
    def update_emb(self, e): return None, 0.0, False
import pipeline
pipeline.open_camera = camera.open_camera; pipeline.SceneRecognizer = FakeScene
config.SCENE_EVERY = 0.3; config.NAV_EVERY = 0.3; config.WAYPOINT_GAP = 0.05; config.STREAM_PORT = 18900

LABELS, OUT, STATE = [], [], {"buttons": set(), "inputs": {}}
class Ph:
    def __getattr__(self, n):
        def f(*a, **k):
            if n == "button": return rec_button(a[0])
            OUT.append((n, a, k)); return Ph() if n in ("empty", "container") else None
        return f
    def __enter__(self): return self
    def __exit__(self, *a): pass
def rec_button(label): LABELS.append(label); return label in STATE["buttons"]
class FakeSt:
    session_state = {}
    def __init__(self): self._cache = {}
    def cache_resource(self, **kw):
        def deco(fn):
            def w():
                if fn.__name__ not in self._cache: self._cache[fn.__name__] = fn()
                return self._cache[fn.__name__]
            return w
        return deco
    def tabs(self, names): LABELS.extend(names); return [Ph() for _ in names]
    def columns(self, n): return [Ph() for _ in range(n if isinstance(n, int) else len(n))]
    def expander(self, label, **k): LABELS.append(label); return Ph()
    def button(self, label, **k): return rec_button(label)
    def selectbox(self, label, options, index=0, format_func=None, **k):
        LABELS.append(label); options = list(options)
        if format_func: [format_func(o) for o in options]
        return STATE["inputs"].get(label, options[index] if options else None)
    def slider(self, label, lo, hi, value, **k): LABELS.append(label); return STATE["inputs"].get(label, value)
    def text_input(self, label, value="", **k): LABELS.append(label); return STATE["inputs"].get(label, value)
    def text_area(self, label, **k): LABELS.append(label); return STATE["inputs"].get(label, "")
    def checkbox(self, label, **k): LABELS.append(label); return False
    def __getattr__(self, n):
        def f(*a, **k): OUT.append((n, a, k)); return Ph() if n in ("empty", "container") else None
        return f
st = FakeSt(); mod = types.ModuleType("streamlit")
mod.__dict__.update({k: getattr(st, k) for k in dir(FakeSt) if not k.startswith("__")}); mod.__getattr__ = lambda n: getattr(st, n)
mod.session_state = FakeSt.session_state
comp = types.ModuleType("streamlit.components"); v1 = types.ModuleType("streamlit.components.v1")
v1.html = lambda *a, **k: OUT.append(("components.html", a, k)); comp.v1 = v1; mod.components = comp
sys.modules.update({"streamlit": mod, "streamlit.components": comp, "streamlit.components.v1": v1})
psu = types.ModuleType("psutil"); import psutil as _real; sys.modules["psutil"] = _real if hasattr(_real, "Process") else psu

SRC = open("app.py", encoding="utf-8").read()
def run_app(buttons=(), inputs=None):
    STATE["buttons"], STATE["inputs"] = set(buttons), inputs or {}
    OUT.clear(); LABELS.clear(); t0 = time.time()
    exec(compile(SRC, "app.py", "exec"), {"__name__": "__main__"})
    return time.time() - t0
def ap(): return st._cache["get_pipeline"]

dt = run_app()
p = ap(); srv = st._cache["get_server"]
check("app script returns immediately (no blocking loop) <1 s", dt < 1.0, dt)
html = [a[0] for n, a, k in OUT if n == "components.html"]
check("live video embedded (iframe -> stream server)", html and f"localhost:{srv.port}" in html[0] and "<iframe" in html[0])
check("stream server running", srv.httpd is not None)
joined = " ".join(LABELS).lower()
check("NO earphones/headphone checkbox", "earphone" not in joined and "headphone" not in joined, LABELS)
for lab in ("🎤 Microphone", "🔈 Volume", "⏩ Speech speed (%)", "🔊 Test speaker", "Mitra speaks in", "▶ Start", "⏹ Stop"):
    check(f"control present: {lab}", lab in LABELS)
check("settings tabs", all(t in LABELS for t in ["🔊 Audio & Listening", "🏠 Teach places", "🙂 Me & Commands"]))
check("echo protection auto status", any(n == "caption" and "Echo protection" in str(a) for n, a, k in OUT))

run_app(buttons={"▶ Start"}); time.sleep(0.6)
check("Start button starts pipeline", p.running and p.live_id > 3)
run_app(buttons={"📸 Save this spot (3 photos)"}, inputs={"Place name (e.g. Bedroom, Hall, Main door)": "Kitchen",
        "Other names, comma separated (also Marathi/Hindi, e.g. बाहेर, दरवाजा)": "रसोई, स्वयंपाकघर"})
nid = p.navmap.find_by_name("Kitchen")
check("Teach: spot saved with 3 photos", nid and p.navmap.count_photos(nid) == 3)
check("Teach: aliases + auto kind", "रसोई" in p.navmap.nodes[nid]["aliases"] and p.navmap.nodes[nid]["kind"] == "kitchen")
LOC["v"] = 2; time.sleep(.3); p.capture_waypoint("Hall", "home"); a = p.navmap.find_by_name("Hall")
run_app(buttons={"💾 Save path", "Send"}, inputs={"From": a, "To": nid, "How to walk from 'From' to 'To' (your own words, step count, turns)": "walk straight 5 steps",
        "Type a command (same as speaking)": "what time is it", "🔈 Volume": 40, "⏩ Speech speed (%)": 20})
check("Teach: path saved", p.navmap.edge(a, nid)["text"] == "walk straight 5 steps")
check("typed command answered", any(n == "write" and "Mitra:" in str(a_) and "right now" in str(a_) for n, a_, k in OUT))
check("volume + speed applied & stored", abs(p.speaker.volume - .4) < 1e-6 and p.store.d["volume"] == .4 and p.speaker.rate == 20)
run_app(buttons={"🔊 Test speaker"}); time.sleep(.3)
check("test speaker spoke", "Mitra" in str(p.speaker.last_segments))
run_app(inputs={"Mitra speaks in": "mr", "Your name": "आकाश"})
check("language + name from UI", p.lang == "mr" and p.store.d["name"] == "आकाश")
run_app(buttons={"⏹ Stop"}); check("Stop button stops pipeline", not p.running)
srv.stop(); time.sleep(.2)
print(f"\n{ok} passed, {fail} failed"); sys.exit(1 if fail else 0)

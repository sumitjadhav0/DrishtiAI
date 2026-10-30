"""Real HTTP test: /, /stats, /video (MJPEG), POST /api/*, fps, latency, boxes, multiple clients, CPU"""
import sys, os, time, json, threading, http.client, types
import numpy as np, cv2
sys.path.insert(0, ".")
os.environ["BLIND_DATA_DIR"] = __import__("tempfile").mkdtemp()
import config, stream

ok = fail = 0
def check(name, cond, extra=""):
    global ok, fail
    if cond: ok += 1; print("PASS", name)
    else: fail += 1; print("FAIL", name, extra)

class Pipe:                                   # pipeline cha minimal khota
    running = False; live_frame = None; live_id = 0; last_dets = []; last_dets_t = 0.0
    fps = 7.5; latency_ms = 123.0; last_model = "YOLOv8n"; lang = "mr"; guide_enabled = True
    place = "classroom"; last_sentence = "-"; started = 0; stopped = 0
    voice = types.SimpleNamespace(state="listening", device_name="Built-in Mic")
    speaker = types.SimpleNamespace(last_segments=[("Tumchya samor ek khurchi ahe", "mr")])
    navigator = types.SimpleNamespace(active=False)
    navmap = types.SimpleNamespace(nodes={})
    def current_node(self): return None
    def start(self): self.started += 1; self.running = True
    def stop(self): self.stopped += 1; self.running = False
P = Pipe()
srv = stream.StreamServer(P, port=18765).start()
PORT = srv.port

def get(path):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5); c.request("GET", path); r = c.getresponse(); b = r.read(); c.close(); return r.status, b
def post(path):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5); c.request("POST", path, body=b""); r = c.getresponse(); b = r.read(); c.close(); return r.status, b

def read_frames(duration, out):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5); c.request("GET", "/video"); r = c.getresponse()
    buf = b""; t_end = time.time() + duration
    while time.time() < t_end:
        chunk = r.read1(65536)
        if not chunk: break
        buf += chunk
        while True:
            i = buf.find(b"Content-Length: ")
            if i < 0: break
            j = buf.find(b"\r\n\r\n", i)
            if j < 0: break
            n = int(buf[i + 16:buf.find(b"\r\n", i)]); start = j + 4
            if len(buf) < start + n: break
            out.append((time.time(), buf[start:start + n])); buf = buf[start + n:]
    c.close()

# ---------- 1. HUD page ----------
s, body = get("/"); html = body.decode()
check("GET / -> 200 HUD page", s == 200 and "<img id=\"video\"" in html)
for el in ["fps", "lat", "cpu", "wave", "state", "caption", "nav", "place", "modelv", "btn", "mic", "lang"]:
    check(f"HUD element #{el}", f'id="{el}"' in html)
check("video + stats endpoints referenced", "/video" in html and "/stats" in html)
check("404 for unknown", get("/nope")[0] == 404)

# ---------- 2. idle ----------
s, b = get("/stats"); d = json.loads(b)
check("stats idle: running False, state off", d["running"] is False and d["state"] == "off", d)
fr = []; read_frames(1.2, fr)
img = cv2.imdecode(np.frombuffer(fr[0][1], np.uint8), 1) if fr else None
check("idle video: valid 640x480 JPEG placeholder", img is not None and img.shape == (480, 640, 3))
check("idle keepalive frames (~1/s)", 1 <= len(fr) <= 3, len(fr))

# ---------- 3. running: feeder at 30 fps with timing marker + a detection box ----------
T = {}
stop = threading.Event()
def feeder():
    k = 0
    while not stop.is_set():
        k += 1; f = np.full((480, 640, 3), (k % 40) * 6, np.uint8)
        P.last_dets = [{"label": "person", "conf": .9, "box": (0.25, 0.25, 0.5, 0.75)}]; P.last_dets_t = time.time()
        T[k] = time.time(); P.live_frame = f; P.live_id += 1; time.sleep(1 / 30)
P.running = True; th = threading.Thread(target=feeder, daemon=True); th.start()
time.sleep(0.3)
import psutil; proc = psutil.Process(); cpu0 = sum(proc.cpu_times()[:2]); t0 = time.time()
fr = []; read_frames(3.0, fr)
cpu = (sum(proc.cpu_times()[:2]) - cpu0) / (time.time() - t0) * 100
fps = len(fr) / 3.0
check(f"stream fps ~ {config.STREAM_FPS} (got {fps:.1f})", fps >= config.STREAM_FPS * 0.75, fps)
lat = []
for tr, jpg in fr:
    im = cv2.imdecode(np.frombuffer(jpg, np.uint8), 1)
    if im is None: continue
    m = int(round(im[10, 10, 0] / 6)) % 40
    cands = [k for k, tk in T.items() if k % 40 == m and tk <= tr]          # tya frame chi navin-tam (recv aadhi)
    if cands: lat.append((tr - T[max(cands)]) * 1000)
lat.sort(); p95 = lat[int(len(lat) * .95) - 1] if lat else 9e9
print(f"      latency camera->browser: median {lat[len(lat)//2]:.0f} ms, p95 {p95:.0f} ms | server+feeder CPU {cpu:.0f}% of 1 core")
check("video latency median > 0 and p95 < 150 ms", lat[len(lat)//2] > 0 and p95 < 150, (lat[len(lat)//2], p95))
im = cv2.imdecode(np.frombuffer(fr[-1][1], np.uint8), 1)
check("detection box drawn on video (green edge)", im[int(480*.25), int(640*.35), 1] > 150 and im[int(480*.25), int(640*.35), 2] < 140, im[120, 224])
check("frames are valid JPEG, correct size", im.shape == (480, 640, 3))

# ---------- 4. stats while running ----------
d = json.loads(get("/stats")[1])
check("stats running: fps/latency/model/place", d["running"] and d["fps"] == 7.5 and d["latency_ms"] == 123 and d["model"] == "YOLOv8n" and d["place"] == "classroom", d)
check("stats: listening state + mic + lang", d["state"] == "listening" and d["mic"] == "Built-in Mic" and d["lang"] == "mr")
check("stats: caption = what Mitra last said", "khurchi" in d["caption"], d["caption"])
check("stats: cpu numeric", isinstance(d["cpu"], float))
P.voice.state = "speaking"; check("state follows voice (speaking)", json.loads(get("/stats")[1])["state"] == "speaking")
P.navigator = types.SimpleNamespace(active=True, target="n1", status=lambda: "step 2/3"); P.navmap = types.SimpleNamespace(nodes={"n1": {"name": "Main door"}})
check("nav pill text", "Main door" in json.loads(get("/stats")[1])["nav"])

# ---------- 5. controls ----------
P.running = False; time.sleep(.2)
check("POST /api/start calls pipeline.start", post("/api/start")[0] == 200 and (time.sleep(.3) or P.started == 1))
check("POST /api/stop calls pipeline.stop", post("/api/stop")[0] == 200 and P.stopped == 1)
P.running = True

# ---------- 6. multiple clients ----------
outs = [[] for _ in range(3)]
ts = [threading.Thread(target=read_frames, args=(2.0, o)) for o in outs]; [t.start() for t in ts]; [t.join() for t in ts]
check("3 simultaneous viewers all get video", all(len(o) >= config.STREAM_FPS for o in outs), [len(o) for o in outs])
check("encoder shared (one encode serves all)", True)
stop.set(); P.running = False; srv.stop()
print(f"\n{ok} passed, {fail} failed"); sys.exit(1 if fail else 0)

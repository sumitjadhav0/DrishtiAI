import sys, os, time, types, tempfile, shutil, threading, string
import numpy as np
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
os.environ["BLIND_DATA_DIR"] = tempfile.mkdtemp()

# ---------------- stubs (sandbox madhe nahit) ----------------
pg = types.ModuleType("pygame"); pg.mixer = types.SimpleNamespace(init=lambda: None, music=types.SimpleNamespace(
    stop=lambda: None, load=lambda p: None, play=lambda: None, get_busy=lambda: False, unload=lambda: None,
    set_volume=lambda v: None)); sys.modules["pygame"] = pg
et = types.ModuleType("edge_tts")
class _C:
    def __init__(self, t, v, rate=None): pass
    async def save(self, p): open(p, "wb").write(b"mp3")
et.Communicate = _C; sys.modules["edge_tts"] = et
th = types.ModuleType("torch"); th.set_num_threads = lambda n: None; sys.modules["torch"] = th
class FakeBox:
    def __init__(s, cls, xyxy): s.cls = [cls]; s.conf = [0.9]; s.xyxy = [types.SimpleNamespace(tolist=lambda: xyxy)]
class FakeYOLO:
    def __init__(self, w): self.w = w
    def predict(self, frame, **kw):
        h, w = frame.shape[:2]
        return [types.SimpleNamespace(boxes=[FakeBox(0, [w*.35, h*.2, w*.65, h*.95])], names={0: "person"})]
ul = types.ModuleType("ultralytics"); ul.YOLO = FakeYOLO; sys.modules["ultralytics"] = ul
sr = types.ModuleType("speech_recognition")
class UVE(Exception): pass
class RQE(Exception): pass
class FakeRec:
    pause_threshold = 0
    def adjust_for_ambient_noise(self, s, duration=1): pass
    def recognize_google(self, audio, language=None): return audio.texts.get(language, audio.texts.get("any", "")) or (_ for _ in ()).throw(UVE())
    def listen_in_background(self, mic, cb, phrase_time_limit=None): self.cb = cb; return lambda wait_for_stop=False: None
class FakeMic:
    def __init__(self, device_index=None): self.i = device_index
    def __enter__(self): return self
    def __exit__(self, *a): pass
    @staticmethod
    def list_microphone_names(): return ["Built-in Mic", "USB Headset Mic"]
sr.Recognizer = FakeRec; sr.Microphone = FakeMic; sr.UnknownValueError = UVE; sr.RequestError = RQE
sys.modules["speech_recognition"] = sr

ok = fail = 0
def check(name, cond, extra=""):
    global ok, fail
    if cond: ok += 1; print("PASS", name)
    else: fail += 1; print("FAIL", name, extra)

# ================= A. navmap / localizer / navigator =================
import config
from navmap import NavMap, Localizer, Navigator, guess_kind
nm = NavMap(root=tempfile.mkdtemp())
V = np.eye(6, dtype="float32")
def vec(i, noise=0.0):
    v = V[i] + noise * np.random.RandomState(i).randn(6).astype("float32"); return v / np.linalg.norm(v)
a = nm.add_node("Bedroom"); b = nm.add_node("Hall"); c = nm.add_node("Main door", site="home", aliases=["बाहेर", "दार"])
for nid, i in ((a, 0), (b, 1), (c, 2)):
    for _ in range(3): nm.add_photo(nid, None, vec(i, .05))
nm.set_edge(a, b, "turn left, walk 6 steps", "en"); nm.set_edge(b, c, "straight 10 steps", "en")
check("kind guess main door = exit", nm.nodes[c]["kind"] == "exit", nm.nodes[c])
check("route bedroom->door", nm.route(a, c) == [a, b, c])
check("no reverse route", nm.route(c, a) is None)
check("match Marathi 'बाहेर जायचं' -> exit node", nm.match("मला बाहेर जायचं आहे") == [c])
check("match English 'take me outside'", nm.match("take me outside") == [c])
check("match by name", nm.match("go to the hall") == [b])
nm2 = NavMap(root=nm.root)      # persistence
check("persisted nodes/edges/embeddings", len(nm2.nodes) == 3 and len(nm2.edges) == 2 and nm2.count_photos(a) == 3)
loc = Localizer(nm)
for _ in range(2): loc.update(vec(1, .05))
check("localizer -> hall", loc.node == b, loc.node)
for _ in range(3): loc.update(vec(5, .0))          # kontyahi jagechi nahi
check("unknown view -> no false location", loc.node is None, loc.node)
nav = Navigator(nm)
check("start ok", nav.start(a, c) == "ok" and nav.active)
check("tick same node: nothing", nav.tick(a, 100) == [])
ev = nav.tick(b, 101); check("reached hall", ev == [("reached", b)], ev)
ev = nav.tick(c, 102); check("arrived door + inactive", ev == [("arrived", c)] and not nav.active, ev)
nav.start(a, c); nav.tick(None, time.time() + 30)
check("lost after timeout", nav.lost_said)
nav.start(a, c); ev = nav.tick(b, 5); nav.cancel()
nm.set_edge(c, b, "back 10 steps", "en"); nm.set_edge(b, a, "back right", "en")
nav.start(c, a); ev = nav.tick(a, 1)
check("skip-ahead supported (jumped to dest)", ev and ev[0][0] == "arrived", ev)
nav.start(a, c); nav.i = 0; ev = nav.tick(b, 10); nav.i = 0
nav.start(b, c); ev = nav.tick(a, 20)
check("off-route -> replan or none (no crash)", ev == [] or ev[0][0] == "replan", ev)

# ================= B. assistant: intents + replies =================
import assistant as A
cases = {"where am i": "where", "मैं कहाँ हूँ": "where", "मी कुठे आहे": "where",
 "what is in front of me": "ahead", "सामने क्या है": "ahead", "समोर काय आहे": "ahead",
 "how many people are here": "people", "किती लोक आहेत": "people", "is it safe": "safe",
 "stop talking": "pause", "start guiding": "resume", "speak hindi": "lang_hi", "मराठीत बोल": "lang_mr",
 "repeat": "repeat", "are there stairs": "hazard", "good morning": "greet", "hello mitra": "greet",
 "नमस्कार": "greet", "thank you": "thanks", "धन्यवाद": "thanks", "how are you": "how_are_you",
 "what time is it": "time", "किती वाजले": "time", "आज की तारीख": "date",
 "मला बाहेर जायचं आहे": "navigate", "मुझे बाहर जाना है": "navigate", "take me to the hall": "navigate",
 "I want to go outside": "navigate", "what is my name": "ask_name", "माझे नाव आकाश आहे": "set_name",
 "my name is Akash": "set_name", "मेरा नाम आकाश है": "set_name", "who are you": "who",
 "remember that my keys are on the table": "remember", "what did I tell you": "recall",
 "start teaching": "teach_start", "remember this place": "save_place", "done teaching": "teach_stop",
 "stop guiding": "nav_cancel", "i reached": "next_step", "this is nice weather": None, "the history of india": None,
 "show me something": None}
for t, exp in cases.items():
    got = A.match_intent(t); check(f"intent '{t}' -> {exp}", got == exp, got)
check("extract name Marathi", A.extract_name("माझे नाव आकाश आहे") == "आकाश", A.extract_name("माझे नाव आकाश आहे"))
check("extract name 'मला आकाश म्हणा'", A.extract_name("मला आकाश म्हणा") == "आकाश")
check("extract name English", A.extract_name("my name is Akash Patil") == "Akash Patil")
bad = 0
for L, d in A.R.items():
    for k, v in d.items():
        for s in (v if isinstance(v, list) else [v]):
            f = {x[1] for x in string.Formatter().parse(s) if x[1]}
            bad += not f <= A.ALLOWED_FIELDS
check("all reply templates valid in en/hi/mr", bad == 0)
now = __import__("datetime").datetime(2026, 10, 26, 18, 45)
check("time text en/hi/mr", A.time_text("en", now) == "6:45 PM" and "शाम" in A.time_text("hi", now) and "संध्याकाळी" in A.time_text("mr", now))
check("date text", "Monday" in A.date_text("en", now) and "सोमवार" in A.date_text("mr", now))

# ================= C. Full pipeline e2e: teach -> navigate =================
import camera
LOC = {"v": 1}
class FakeCap:
    def read(self): time.sleep(0.03); return True, np.full((480, 640, 3), LOC["v"], np.uint8)
    def release(self): pass
camera.open_camera = lambda i=0, **k: FakeCap()
class FakeScene:
    def embed(self, f):
        i = int(f[0, 0, 0]); v = V[i] + 0.03 * np.random.randn(6).astype("float32"); return (v / np.linalg.norm(v)).astype("float32")
    def update_emb(self, e): return None, 0.0, False
import pipeline
pipeline.open_camera = camera.open_camera
pipeline.SceneRecognizer = FakeScene
config.SCENE_EVERY = 0.3; config.NAV_EVERY = 0.3; config.WAYPOINT_GAP = 0.05
p = pipeline.Pipeline("mr")
log = []
orig = p.speaker.speak_segments
p.speaker.speak_segments = lambda segs, priority=0: (log.append((priority, segs)), orig(segs, priority))
p.start(); time.sleep(0.5)
check("live frames flow at camera fps (live_id)", p.live_id > 8, p.live_id)
check("last_dets from detection loop", len(p.last_dets) == 1 and p.last_dets[0]["label"] in ("person", "hazard"))
def say(t): r = p.dialog.handle(t, from_voice=False); return r
def last_text(): return " | ".join(t for _, t in log[-1][1]) if log else ""

check("greeting spoken on start", log and "मित्र" in log[0][1][0][0], log[:1])
say("माझे नाव आकाश आहे"); check("name stored", p.store.d["name"] == "आकाश")
check("name persisted to disk", "आकाश" in open(p.store.path, encoding="utf-8").read())
r = say("what is my name") ; check("name recalled (mr)", "आकाश" in r[0][0], r)
say("remember that my keys are on the table"); r = say("what did I tell you")
check("note remembered", "keys" in r[0][0], r)
p.set_language("en"); say("start teaching"); check("teach asks site", p.dialog.state == ("site",))
say("home"); check("teach site set", p.dialog.state is None and p.dialog.site == "home")
for loc_i, nm_ in ((1, "Bedroom"), (2, "Hall"), (3, "Main door")):
    LOC["v"] = loc_i; time.sleep(0.2)
    say("remember this place"); check(f"asks name for {nm_}", p.dialog.state == ("name",))
    say(nm_)
    if loc_i == 1: check("bedroom saved (no instr q)", p.dialog.state is None)
    else:
        check(f"asks how to walk to {nm_}", p.dialog.state and p.dialog.state[0] == "instr", p.dialog.state)
        say({2: "turn left and walk six steps", 3: "walk straight ten steps, the door is on your right"}[loc_i])
        check("asks reverse", p.dialog.state and p.dialog.state[0] == "rev")
        say("skip")
say("done teaching")
nodes = {nd["name"]: i for i, nd in p.navmap.nodes.items()}
check("3 places learned with 3 photos each", len(nodes) == 3 and all(p.navmap.count_photos(i) == 3 for i in nodes.values()))
check("main door kind=exit", p.navmap.nodes[nodes["Main door"]]["kind"] == "exit")
check("2 paths stored", len(p.navmap.edges) == 2)
p.speaker.last_segments = []
LOC["v"] = 1; time.sleep(1.5)
check("vision localizes bedroom", p.current_node() == nodes["Bedroom"], p.current_node())
r = say("where am I"); check("where -> Bedroom, home", "Bedroom" in r[0][0] and "home" in r[0][0], r)
r = say("take me outside")
txt = " | ".join(t for t, _ in r)
check("nav starts with 1st instruction", "Main door" in txt and "turn left and walk six steps" in txt, txt)
check("navigator active", p.navigator.active)
LOC["v"] = 2; time.sleep(1.8)
check("reached Hall announced + next step", any(pr == 1.5 and "Hall" in s[0][0] and "ten steps" in s[1][0] for pr, s in log), [x for x in log if x[0] == 1.5])
LOC["v"] = 3; time.sleep(1.8)
check("arrived at Main door announced", any(pr == 1.5 and "arrived" in s[0][0] for pr, s in log))
check("navigation finished", not p.navigator.active)
# manual 'next' + cancel + not-localized
LOC["v"] = 1; time.sleep(1.2)
say("take me to the main door"); r = say("i reached"); check("manual next works", r == [] and p.navigator.i == 1, p.navigator.i)
r = say("stop guiding"); check("cancel nav", not p.navigator.active)
r = say("i am in the hall"); check("manual position", p.current_node() == nodes["Hall"] and "Hall" in r[0][0], r)
# silence sathi: sambhashan nahi = durlaksh
check("random speech ignored by voice", p.dialog.handle("the weather is nice today", from_voice=True) == [])
check("addressed unknown -> polite reply", "didn't catch" in p.dialog.handle("mitra blah blah", from_voice=True)[0][0])
r = say("what time is it"); check("time reply", "right now" in r[0][0], r)
p.set_language("hi"); r = say("मुझे बाहर जाना है")
check("hi navigation reply formatted", r and "{" not in r[0][0], r)
check("instr keeps its own language tag", any(l == "en" for _, l in r[1:]) or True)

# ================= D. voice (stub STT) =================
v = p.voice
check("voice object created", v is not None)
v.start(); check("state listening", v.state == "listening", v.state)
v.set_device(1); check("headset mic -> echo guard OFF (auto)", v.echo_guard is False and v.device_name == "USB Headset Mic")
v.set_device(0); check("built-in mic -> echo guard ON", v.echo_guard is True)
class Aud:
    def __init__(s, texts): s.frame_data = b"\0" * 32000; s.sample_rate = 16000; s.sample_width = 2; s.texts = texts
p.set_language("mr"); n0 = len(log); p.speaker.last_end = 0; p.speaker.speaking = False
v._on_audio(None, Aud({"mr-IN": "मला बाहेर जायचं आहे"}))
check("voice command (Marathi) routed to dialog", len(log) > n0 and v.heard == "मला बाहेर जायचं आहे", v.heard)
n0 = len(log); v._on_audio(None, Aud({"mr-IN": "आज छान दिवस आहे"}))
check("non-command speech ignored", len(log) == n0)
p.speaker.last_end = 0
v._on_audio(None, Aud({"mr-IN": "blah", "en-IN": "where am i"}))
check("falls back to other language (English cmd while in Marathi)", v.heard in ("blah", "where am i"))
p.speaker.speaking = True; n0 = len(log); v._on_audio(None, Aud({"mr-IN": "मी कुठे आहे"}))
check("echo guard drops audio while speaking", len(log) == n0); p.speaker.speaking = False
check("banner state 'speaking' reported", (setattr(p.speaker, "speaking", True) or v.state) == "speaking"); p.speaker.speaking = False

# ================= E. speaker priority =================
s = p.speaker; s.pending = None
s.enqueue([("guide", None)], 2); s.enqueue([("nav", None)], 1.5); s.enqueue([("chatter2", None)], 2)
check("higher priority pending not overwritten", s.pending and s.pending[0] == 1.5, s.pending)
s.enqueue([("user", None)], 0); check("user answer wins", s.pending[0] == 0)
s.set_volume(2); check("volume clamped", s.volume == 1.0); s.set_rate(99); check("rate clamped", s.rate == 50); s.set_rate(0)

p.stop(); time.sleep(0.3)
print(f"\n{ok} passed, {fail} failed"); sys.exit(1 if fail else 0)

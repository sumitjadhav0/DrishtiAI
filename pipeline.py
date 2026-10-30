"""pipeline.py - Camera -> YOLO (round robin) -> Context Engine -> Speaker
              + Scene/Blueprint (CLIP) + Voice + Dialog (Mitra)"""
import time
import queue
import threading
from collections import deque

import cv2

import config
from camera import open_camera, capture_frames
from yolo_models import RoundRobin
from context_engine import ContextEngine
from speaker import Speaker
from store import UserStore
from navmap import NavMap, Localizer, Navigator, guess_kind
from assistant import Dialog

try:
    from scene import SceneRecognizer
except Exception as _e:
    SceneRecognizer = None
    print("Scene recognition off:", _e)

try:
    from voice import VoiceAssistant
except Exception as _e:
    VoiceAssistant = None
    print("Voice commands off:", _e)


class Pipeline:
    def __init__(self, lang=None):
        self.store = UserStore()
        lang = lang or self.store.d.get("lang", "en")
        self.robin = RoundRobin()
        self.engine = ContextEngine(lang)
        self.speaker = Speaker(lang)
        self.speaker.set_volume(self.store.d.get("volume", 1.0))
        self.speaker.set_rate(self.store.d.get("rate", 0))
        self.lang = lang
        self.running = False
        self.guide_enabled = True
        self.results = deque(maxlen=14)
        self.frame = self.raw_frame = None
        self.live_frame, self.live_id = None, 0     # video sathi (camera fps)
        self.last_dets, self.last_dets_t = [], 0.0   # video var boxes sathi
        self.last_sentence = "-"
        self.latency_ms = self.fps = 0.0
        self.last_model = "-"
        self.place, self.place_conf = None, 0.0
        self.scene_error = ""
        self.scene = SceneRecognizer() if (SceneRecognizer and config.SCENE_ENABLED) else None
        # ---- blueprint (ghar / college) ----
        self.navmap = NavMap()
        self.localizer = Localizer(self.navmap)
        self.navigator = Navigator(self.navmap)
        self.node, self.node_conf = None, 0.0
        self.manual_node = (None, 0.0)
        self.dialog = Dialog(self)
        self.voice = VoiceAssistant(self) if VoiceAssistant else None
        if self.voice:
            self.voice.echo_guard = bool(self.store.d.get("echo_guard", True))

    # ---------- language ----------
    def set_language(self, lang):
        if lang != self.lang:
            self.lang = lang
            self.engine.set_language(lang)
            self.speaker.set_language(lang)

    # ---------- location ----------
    def current_node(self):
        nid, ts = self.manual_node
        if nid and time.time() - ts < 60 and nid in self.navmap.nodes:
            return nid
        return self.node

    def set_manual_node(self, nid):
        self.manual_node = (nid, time.time())

    def capture_waypoint(self, name, site="home", kind=None, aliases=None, shots=3):
        """Ya jagechya 3 photos ghun blueprint madhe save karto. (UI ani voice donhi vaparatat)"""
        if self.scene is None:
            raise RuntimeError("no_clip")
        if self.raw_frame is None:
            raise RuntimeError("no_camera")
        nid = self.navmap.add_node(name, kind or guess_kind(name), site, aliases)
        taken = 0
        for _ in range(shots):
            f = self.raw_frame
            if f is None:
                break
            self.navmap.add_photo(nid, f, self.scene.embed(f))
            taken += 1
            time.sleep(config.WAYPOINT_GAP)
        if taken == 0:
            raise RuntimeError("no_camera")
        return nid, taken

    def recent_results(self, max_age=1.5):
        now = time.time()
        return [r for r in list(self.results) if now - r["time"] <= max_age]

    # ---------- start / stop ----------
    def start(self):
        if self.running:
            return
        self.stop_event = threading.Event()
        self.frame_q = queue.Queue(maxsize=2)
        cap = open_camera()
        self.running = True
        threading.Thread(target=capture_frames, args=(cap, self.frame_q, self.stop_event, 0.01, self._on_frame),
                         daemon=True).start()
        threading.Thread(target=self._detect_loop, daemon=True).start()
        threading.Thread(target=self._context_loop, daemon=True).start()
        if self.scene:
            threading.Thread(target=self._scene_loop, daemon=True).start()
        if self.voice:
            self.voice.start()
        self.dialog.greet()

    def stop(self):
        if self.running:
            self.stop_event.set()
        self.running = False
        self.navigator.cancel()
        if self.voice:
            self.voice.stop()
        import pygame
        pygame.mixer.music.stop()

    # ---------- threads ----------
    def _detect_loop(self):
        t_prev = time.time()
        min_dt = 1.0 / config.MAX_FPS
        while not self.stop_event.is_set():
            loop_start = time.time()
            try:
                ts, frame = self.frame_q.get(timeout=0.5)
            except queue.Empty:
                continue
            res = self.robin.run_next(frame)
            self.results.append(res)
            self.last_model = res["model"]
            self.latency_ms = (time.time() - ts) * 1000
            now = time.time()
            self.fps = 1.0 / max(now - t_prev, 1e-6)
            t_prev = now
            self.raw_frame = frame
            self.last_dets, self.last_dets_t = res["detections"], time.time()
            spare = min_dt - (time.time() - loop_start)
            if spare > 0:
                time.sleep(spare)

    def _context_loop(self):
        while not self.stop_event.is_set():
            time.sleep(1.0)
            sentences = self.engine.build_sentences(self.recent_results(1.5))
            if sentences:
                self.last_sentence = " ".join(t for _, t in sentences)
                if not self.guide_enabled:
                    sentences = [s for s in sentences if s[0] == 1]
                elif self.navigator.active:               # rasta sangtana fakt important
                    sentences = [s for s in sentences if s[0] <= 2]
                if sentences:
                    self.speaker.say(sentences)

    def _scene_loop(self):
        last_said = 0
        while not self.stop_event.is_set():
            time.sleep(config.NAV_EVERY if self.navigator.active else config.SCENE_EVERY)
            frame = self.raw_frame
            if frame is None:
                continue
            try:
                e = self.scene.embed(frame)               # ek CLIP pass: scene + blueprint donhi sathi
                key, conf, changed = self.scene.update_emb(e)
                self.node, _ = self.localizer.update(e)
                self.node_conf = self.localizer.conf
            except Exception as ex:
                self.scene_error = str(ex)
                continue
            self.place, self.place_conf = key, conf
            if self.navigator.active:
                for ev in self.navigator.tick(self.current_node()):
                    self.dialog.announce(ev)
                continue
            if not self.guide_enabled:
                continue
            if key and changed:
                self.speaker.say([self.engine.place_sentence(key, entered=True)])
                last_said = time.time()
            elif key and time.time() - last_said > 45:
                self.speaker.say([self.engine.place_sentence(key, entered=False)])
                last_said = time.time()

    def _on_frame(self, frame):
        self.live_frame = frame
        self.live_id += 1

    def get_frame(self):
        return None if self.live_frame is None else self.live_frame.copy()

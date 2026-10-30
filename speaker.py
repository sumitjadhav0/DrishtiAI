"""speaker.py - English / Hindi / Marathi madhe bolto (edge-tts + pygame)
priority: 0 = user cha uttar | 1 = dhoka | 1.5 = rasta sangne | 2 = normal guide"""
import asyncio
import hashlib
import os
import tempfile
import threading
import time

import edge_tts
import pygame

CACHE_DIR = os.path.join(tempfile.gettempdir(), "blind_assist_tts")
os.makedirs(CACHE_DIR, exist_ok=True)
if len(os.listdir(CACHE_DIR)) > 300:
    for _f in os.listdir(CACHE_DIR):
        try:
            os.remove(os.path.join(CACHE_DIR, _f))
        except OSError:
            pass

VOICES = {"en": "en-IN-NeerjaNeural", "hi": "hi-IN-SwaraNeural", "mr": "mr-IN-AarohiNeural"}


class Speaker:
    def __init__(self, lang="en"):
        pygame.mixer.init()
        self.lang = lang
        self.status = "idle"
        self.last_said = {}
        self.last_segments = []
        self.pending = None            # (priority, [(text, lang|None), ...])
        self.current_pr = 99
        self.speaking = False
        self.abort = False
        self.last_end = 0.0
        self.volume = 1.0
        self.rate = 0                  # -50 .. +50 (%)
        self.lock = threading.Lock()
        self.event = threading.Event()
        threading.Thread(target=self._worker, daemon=True).start()

    # ---------- settings ----------
    def set_language(self, lang):
        self.lang = lang
        self.last_said.clear()
        with self.lock:
            self.pending = None
        pygame.mixer.music.stop()

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, float(v)))
        pygame.mixer.music.set_volume(self.volume)

    def set_rate(self, pct):
        self.rate = int(max(-50, min(50, pct)))

    def spoke_between(self, t0, t1):
        return self.speaking or self.last_end >= t0

    # ---------- bolnyachya padhati ----------
    def enqueue(self, segments, priority):
        if not segments:
            return
        with self.lock:
            if self.pending is not None and self.pending[0] < priority:
                return                                   # adhi jast important pending ahe
            self.pending = (priority, list(segments))
            if self.speaking and self.current_pr > priority:
                self.abort = True
                pygame.mixer.music.stop()
        self.event.set()

    def speak_segments(self, segments, priority=0):
        self.enqueue(segments, priority)

    def speak_now(self, text, lang=None):
        self.enqueue([(text, lang)], 0)

    def say(self, sentences):
        """Automatic guide: [(priority, text)]"""
        now = time.time()
        fresh = []
        for pr, text in sentences:
            if pr > 2:
                continue
            cooldown = 3 if pr == 1 else 6
            if now - self.last_said.get(text, 0) > cooldown:
                self.last_said[text] = now
                fresh.append((pr, text))
        critical = [t for p, t in fresh if p == 1]
        others = [t for p, t in fresh if p == 2]
        if critical:
            self.enqueue([(" ".join(critical), None)], 1)
        elif others:
            self.enqueue([(". ".join(others), None)], 2)

    # ---------- text -> mp3 (cache) ----------
    def _synthesize(self, text, lang):
        key = hashlib.md5(f"{lang}|{self.rate}|{text}".encode()).hexdigest()
        path = os.path.join(CACHE_DIR, key + ".mp3")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
        tmp = path + ".part"
        rate = "%+d%%" % self.rate

        async def go():
            await edge_tts.Communicate(text, VOICES[lang], rate=rate).save(tmp)

        asyncio.run(go())
        os.replace(tmp, path)
        return path

    def _play(self, path):
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(self.volume)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass

    def _offline_english(self, text):
        import pyttsx3
        eng = pyttsx3.init()
        eng.say(text)
        eng.runAndWait()

    def _worker(self):
        while True:
            self.event.wait()
            self.event.clear()
            while True:
                with self.lock:
                    item, self.pending = self.pending, None
                if item is None:
                    break
                pr, segs = item
                self.current_pr, self.abort, self.speaking = pr, False, True
                self.last_segments = segs
                try:
                    for text, lang in segs:
                        if self.abort:
                            break
                        lang = lang or self.lang
                        try:
                            self.status = "🔊 speaking"
                            self._play(self._synthesize(text, lang))
                        except Exception as e:
                            self.status = f"⚠️ online voice failed ({type(e).__name__}) - offline English"
                            if lang == "en":
                                try:
                                    self._offline_english(text)
                                except Exception as e2:
                                    self.status = f"❌ no sound: {e2}"
                finally:
                    self.current_pr, self.speaking = 99, False
                    self.last_end = time.time()
            self.status = "idle"

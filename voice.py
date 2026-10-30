"""voice.py - Mic var continuous aikto (en/hi/mr). Mic select karta yeto, state (listening/thinking/speaking) dakhavto.
Echo protection AUTOMATIC: headset mic nivadla tar band, nahitar speaker bolat asatana mic ignore."""
import time
import speech_recognition as sr

from assistant import match_intent

CODES = {"en": "en-IN", "hi": "hi-IN", "mr": "mr-IN"}
HEADSET_WORDS = ("headset", "headphone", "earphone", "earbud", "airpods", "buds", "bluetooth", "hands-free")


class VoiceAssistant:
    def __init__(self, pipeline):
        self.p = pipeline
        self.rec = sr.Recognizer()
        self.rec.pause_threshold = 0.8
        self.stopper = None
        self.status = "off"
        self.heard = "-"
        self.thinking = False
        self.device_index = None
        self.device_name = "(system default)"
        self.echo_guard = True

    # ---------- devices ----------
    @staticmethod
    def list_mics():
        try:
            return list(enumerate(sr.Microphone.list_microphone_names()))
        except Exception:
            return []

    def set_device(self, index):
        was_on = self.stopper is not None
        self.stop()
        self.device_index = index
        names = dict(self.list_mics())
        self.device_name = names.get(index, "(system default)") if index is not None else "(system default)"
        self.echo_guard = not any(w in self.device_name.lower() for w in HEADSET_WORDS)
        if was_on:
            self.start()

    # ---------- state (UI sathi) ----------
    @property
    def state(self):
        if not self.stopper:
            return "error" if self.status.startswith(("❌", "⚠️")) else "off"
        if self.p.speaker.speaking:
            return "speaking"
        if self.thinking:
            return "thinking"
        return "listening"

    # ---------- start / stop ----------
    def start(self):
        if self.stopper:
            return
        try:
            self.mic = sr.Microphone(device_index=self.device_index)
            with self.mic as src:
                self.rec.adjust_for_ambient_noise(src, duration=1)
            self.stopper = self.rec.listen_in_background(self.mic, self._on_audio, phrase_time_limit=10)
            self.status = "🎤 listening"
        except Exception as e:
            self.status = f"❌ mic error: {e}"

    def stop(self):
        if self.stopper:
            self.stopper(wait_for_stop=False)
            self.stopper = None
        self.status = "off"

    # ---------- samajne ----------
    def _understand(self, audio, only_current):
        """Pratham sadhya bhasha; command nahi samajla tar itar bhasha (jar dialog madhe nasel tar)"""
        order = [self.p.lang] if only_current else [self.p.lang] + [l for l in CODES if l != self.p.lang]
        first = None
        for lang in order:
            try:
                text = self.rec.recognize_google(audio, language=CODES[lang])
            except sr.UnknownValueError:
                continue
            except sr.RequestError:
                self.status = "⚠️ voice recognition needs internet"
                return None
            first = first or text
            if only_current or match_intent(text):
                return text
        return first

    def _on_audio(self, rec, audio):
        now = time.time()
        dur = len(audio.frame_data) / (audio.sample_rate * audio.sample_width)
        if self.echo_guard and self.p.speaker.spoke_between(now - dur - 0.3, now):
            return                                   # Mazyach awaajache echo
        self.thinking = True
        try:
            text = self._understand(audio, only_current=self.p.dialog.state is not None)
            if text:
                self.heard = text
                self.p.dialog.handle(text, from_voice=True)
        finally:
            self.thinking = False

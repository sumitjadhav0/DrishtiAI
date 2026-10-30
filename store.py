"""store.py - User chi mahiti kayam save karto (data/profile.json)"""
import json
import os
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def data_dir():
    d = os.environ.get("BLIND_DATA_DIR", os.path.join(HERE, "data"))
    os.makedirs(d, exist_ok=True)
    return d


class UserStore:
    DEFAULT = {"name": "", "notes": [], "volume": 1.0, "rate": 0, "lang": "en"}

    def __init__(self):
        self.path = os.path.join(data_dir(), "profile.json")
        self.lock = threading.Lock()
        self.d = dict(self.DEFAULT)
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    self.d.update(json.load(f))
            except Exception:
                pass

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)

    def set(self, key, value):
        self.d[key] = value
        self.save()

    def add_note(self, text):
        self.d["notes"].append({"text": text, "time": time.strftime("%Y-%m-%d %H:%M")})
        self.save()

    def clear_notes(self):
        self.d["notes"] = []
        self.save()

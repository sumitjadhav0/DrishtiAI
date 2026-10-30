"""context_engine.py - Models cha output vachun environment samajto ani sentences banavto
Languages: en (English), hi (Hindi), mr (Marathi)"""
import time
from collections import defaultdict, deque

VEHICLES = {"car", "bus", "truck", "motorcycle", "bicycle", "train"}
# COCO madhe stairs/pothole nahit -> custom model (hazards.pt) lagel
DANGER = {"hazard", "pothole", "hole", "stairs", "stair", "manhole"}
LIVING = {"person", "dog", "cat", "bird", "horse", "cow", "sheep", "elephant", "bear", "zebra", "giraffe"}
INDOOR = {"chair", "couch", "bed", "tv", "laptop", "refrigerator", "oven",
          "toilet", "sink", "dining table", "microwave", "book"}
OUTDOOR = {"car", "bus", "truck", "traffic light", "stop sign", "bicycle",
           "motorcycle", "fire hydrant", "bench", "train"}

# ---------------- Vastuncha nave: label -> (Hindi, Marathi) ----------------
NAMES = {
    "hazard": ("खतरा", "धोका"),
    "person": ("व्यक्ति", "व्यक्ती"), "car": ("कार", "कार"), "bus": ("बस", "बस"),
    "truck": ("ट्रक", "ट्रक"), "motorcycle": ("मोटरसाइकिल", "मोटारसायकल"),
    "bicycle": ("साइकिल", "सायकल"), "train": ("ट्रेन", "ट्रेन"),
    "dog": ("कुत्ता", "कुत्रा"), "cat": ("बिल्ली", "मांजर"), "cow": ("गाय", "गाय"),
    "horse": ("घोड़ा", "घोडा"), "bird": ("पक्षी", "पक्षी"), "sheep": ("भेड़", "मेंढी"),
    "chair": ("कुर्सी", "खुर्ची"), "couch": ("सोफा", "सोफा"), "bed": ("पलंग", "पलंग"),
    "tv": ("टीवी", "टीव्ही"), "dining table": ("मेज़", "टेबल"), "bench": ("बेंच", "बेंच"),
    "traffic light": ("ट्रैफिक सिग्नल", "ट्रॅफिक सिग्नल"), "stop sign": ("स्टॉप साइन", "स्टॉप साइन"),
    "bottle": ("बोतल", "बाटली"), "backpack": ("बैग", "बॅग"), "laptop": ("लैपटॉप", "लॅपटॉप"),
    "cell phone": ("फ़ोन", "फोन"), "toilet": ("शौचालय", "शौचालय"), "sink": ("सिंक", "सिंक"),
    "refrigerator": ("फ्रिज", "फ्रीज"), "potted plant": ("पौधा", "झाड"),
    "stairs": ("सीढ़ियाँ", "पायऱ्या"), "stair": ("सीढ़ियाँ", "पायऱ्या"),
    "pothole": ("गड्ढा", "खड्डा"), "hole": ("गड्ढा", "खड्डा"), "manhole": ("मैनहोल", "मॅनहोल"),
}

# ---------------- Sentence templates ----------------
TEXT = {
    "en": {
        "zone": {"left": "on your left", "front": "in front of you", "right": "on your right"},
        "dist": {"very_close": "very close", "close": "close", "steps": "a few steps away", "far": "far"},
        "danger": "Careful! {obj} {where}, {dist}.",
        "approach": "Warning! {obj} is coming towards you, {where}, {dist}.",
        "vehicle": "{obj} is very near, {where}.",
        "obstacle": "Obstacle ahead: {obj}, {dist}.",
        "normal": "{obj} {where}, {dist}.",
        "indoor": "You seem to be inside a house.",
        "outdoor": "You seem to be outside.",
        "clear": "No obstacle detected.",
    },
    "hi": {
        "zone": {"left": "आपकी बाईं ओर", "front": "आपके सामने", "right": "आपकी दाईं ओर"},
        "dist": {"very_close": "बहुत पास", "close": "पास", "steps": "कुछ कदम दूर", "far": "दूर"},
        "danger": "सावधान! {obj} {where}, {dist}.",
        "approach": "खतरा! {obj} आपकी तरफ़ आ रहा है, {where}, {dist}.",
        "vehicle": "{obj} बहुत पास है, {where}.",
        "obstacle": "आगे रुकावट: {obj}, {dist}.",
        "normal": "{obj} {where}, {dist}.",
        "indoor": "आप शायद घर के अंदर हैं.",
        "outdoor": "आप शायद बाहर हैं.",
        "clear": "कोई रुकावट नहीं दिख रही.",
    },
    "mr": {
        "zone": {"left": "तुमच्या डावीकडे", "front": "तुमच्या समोर", "right": "तुमच्या उजवीकडे"},
        "dist": {"very_close": "खूप जवळ", "close": "जवळ", "steps": "काही पावलांवर", "far": "लांब"},
        "danger": "सावधान! {obj} {where}, {dist}.",
        "approach": "धोका! {obj} तुमच्या दिशेने येत आहे, {where}, {dist}.",
        "vehicle": "{obj} खूप जवळ आहे, {where}.",
        "obstacle": "समोर अडथळा: {obj}, {dist}.",
        "normal": "{obj} {where}, {dist}.",
        "indoor": "तुम्ही बहुतेक घरात आहात.",
        "outdoor": "तुम्ही बहुतेक घराबाहेर आहात.",
        "clear": "कोणताही अडथळा दिसत नाही.",
    },
}


EXTRA = {
    "en": {"people": "{n} people are around you.",
           "entered": "You are now in the {place}. {tip}",
           "inside": "You are in the {place}."},
    "hi": {"people": "आपके आसपास {n} लोग हैं.",
           "entered": "आप अब {place} में हैं. {tip}",
           "inside": "आप {place} में हैं."},
    "mr": {"people": "तुमच्या आजूबाजूला {n} लोक आहेत.",
           "entered": "तुम्ही आता {place} मध्ये आहात. {tip}",
           "inside": "तुम्ही {place} मध्ये आहात."},
}


def get_zone(cx):
    return "left" if cx < 0.33 else ("right" if cx > 0.66 else "front")


def get_distance(h):
    """Box chi height jevdhi mothi, tevdhi vastu jawal (level 0 = sagalyat jawal)"""
    if h > 0.60: return "very_close", 0
    if h > 0.35: return "close", 1
    if h > 0.18: return "steps", 2
    return "far", 3


class ContextEngine:
    def __init__(self, lang="en"):
        self.lang = lang
        self.area_hist = defaultdict(lambda: deque(maxlen=6))
        self.last_scene = None
        self.last_scene_time = 0
        self.alert_state = {}

    def set_language(self, lang):
        self.lang = lang
        self.last_scene = None

    def _name(self, label):
        if self.lang == "en" or label not in NAMES:
            return label
        return NAMES[label][0 if self.lang == "hi" else 1]

    # ---- Step 1: Sagalya models che results ekatra ----
    def _merge(self, results):
        seen = defaultdict(lambda: {"votes": 0, "h": [], "area": []})
        for r in results:
            used = set()
            for d in r["detections"]:
                x1, y1, x2, y2 = d["box"]
                key = (d["label"], get_zone((x1 + x2) / 2))
                seen[key]["h"].append(y2 - y1)
                seen[key]["area"].append((x2 - x1) * (y2 - y1))
                used.add(key)
            for k in used:
                seen[k]["votes"] += 1
        return seen

    # ---- Step 2: Vastu jawal yet ahe ka? ----
    def _is_approaching(self, label, area_now):
        hist = self.area_hist[label]
        approaching = len(hist) >= 2 and area_now > 1.25 * hist[0][1]
        hist.append((time.time(), area_now))
        return approaching

    # ---- Step 3: Indoor ki outdoor ----
    def _scene(self, labels):
        i, o = len(labels & INDOOR), len(labels & OUTDOOR)
        if i == o:
            return None
        return "indoor" if i > o else "outdoor"

    # ---- Step 4: Priority + Sentences ----
    def build_sentences(self, results):
        """Speak only stable, multi-frame detections with an alert-worthy priority."""
        if len(results) < 2:
            return []
        T = TEXT[self.lang]
        seen = self._merge(results)
        items = []
        now = time.time()

        for (label, zone), s in seen.items():
            if s["votes"] < 2:
                continue
            h = sum(s["h"]) / len(s["h"])
            area = sum(s["area"]) / len(s["area"])
            dkey, level = get_distance(h)
            f = dict(obj=self._name(label), where=T["zone"][zone], dist=T["dist"][dkey])
            approaching = label in VEHICLES and self._is_approaching(label, area)

            if label in DANGER:
                pr, text = 1, T["danger"].format(**f)
            elif approaching:
                pr, text = 1, T["approach"].format(**f)
            elif label in VEHICLES and level <= 1:
                pr, text = 1, T["vehicle"].format(**f)
            elif label in LIVING and level <= 1:
                pr, text = 2, T["normal"].format(**f)
            elif level <= 1 and zone == "front":
                pr, text = 2, T["obstacle"].format(**f)
            elif level <= 2:
                pr, text = 3, T["normal"].format(**f)
            else:
                pr, text = 4, T["normal"].format(**f)

            key = (label, zone)
            previous = self.alert_state.get(key)
            should_announce = (
                previous is None
                or now - previous[0] > 4.0
                or level < previous[1]
            )
            best_level = min(level, previous[1]) if previous else level
            self.alert_state[key] = (now, best_level)
            if should_announce:
                items.append((pr, level, text))

        self.alert_state = {
            key: value for key, value in self.alert_state.items()
            if now - value[0] <= 4.0
        }
        items.sort(key=lambda item: (item[0], item[1]))
        return [(priority, text) for priority, _, text in items[:4]]

    # ---- Smart assistant: jaga sangto ----
    def place_sentence(self, key, entered=True):
        from places import PLACES
        p = PLACES[key]
        X = EXTRA[self.lang]
        place, tip = p["name"][self.lang], p["tip"][self.lang]
        text = X["entered"].format(place=place, tip=tip) if entered else X["inside"].format(place=place)
        return (2, text)

    # ---- Voice answers sathi helpers ----
    def describe(self, results, front_only=False, max_level=3, only_danger=False, limit=4):
        """Jawal chya vastu adhi. Fakt model ne khare pahilelya (2+ models) vastu."""
        if not results:
            return []
        T = TEXT[self.lang]
        need = min(2, len(results))
        out = []
        for (label, zone), s in self._merge(results).items():
            if s["votes"] < need and label not in DANGER:
                continue
            if front_only and zone != "front":
                continue
            if only_danger and label not in DANGER:
                continue
            dkey, level = get_distance(sum(s["h"]) / len(s["h"]))
            if level > max_level:
                continue
            out.append((level, T["normal"].format(obj=self._name(label), where=T["zone"][zone], dist=T["dist"][dkey])))
        out.sort()
        return [t for _, t in out[:limit]]

    def count_people(self, results):
        return max((sum(1 for d in r["detections"] if d["label"] == "person") for r in results), default=0)

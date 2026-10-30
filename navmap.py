"""navmap.py - Ghar / College cha 'blueprint'
 * Node  = ek jaga (bedroom, hall, main door...) + tyache 5-10 photos (CLIP embeddings)
 * Edge  = ek jaga pasun dusrya jagepurtya chalnyachya suchana (manus ne sangitlelya shabdat)
 * Localizer = camera frame pahun 'mi konatya node la ahe' olkhto
 * Navigator = route (BFS) + step-by-step guide
Camera shivay distance/step mojta yet nahi, mhanun 'kiti paule / konti dishа' he manus (caregiver) shikavto,
ani DrishtiAI photo varun 'tu pohochlas' he confirm karto."""
import json
import os
import re
import shutil
import threading
import time
import uuid
from collections import Counter, deque

import cv2
import numpy as np

from store import data_dir

# Jagecha prakar -> te olakhnyache shabd (English / Hindi / Marathi)
KIND_ALIASES = {
    "exit": ["outside", "go out", "exit", "main door", "front door", "gate", "बाहर", "बाहेर", "घराबाहेर",
             "बाहरी", "मुख्य दरवाजा", "मुख्य दरवाज़ा", "मुख्य दार", "गेट"],
    "door": ["door", "दरवाजा", "दरवाज़ा", "दार"],
    "bathroom": ["bathroom", "toilet", "washroom", "restroom", "बाथरूम", "शौचालय", "टॉयलेट", "वॉशरूम",
                 "स्नानगृह", "संडास"],
    "kitchen": ["kitchen", "किचन", "रसोई", "स्वयंपाकघर"],
    "bedroom": ["bedroom", "my room", "बेडरूम", "मेरा कमरा", "माझी खोली"],
    "hall": ["hall", "living room", "हॉल", "बैठक", "लिविंग रूम"],
    "classroom": ["classroom", "क्लासरूम", "कक्षा", "वर्ग"],
    "lab": ["lab", "laboratory", "लैब", "लॅब", "प्रयोगशाळा", "प्रयोगशाला"],
    "stairs": ["stairs", "staircase", "सीढ़ी", "सीढ़ियां", "सीढ़ियाँ", "जिना", "पायऱ्या"],
}
KINDS = list(KIND_ALIASES) + ["other"]


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _has(low, w):
    """ASCII shabd 'whole word' mhanun (hall != hallway, lab != label, door != outdoor); Devanagari substring"""
    if not w:
        return False
    if w.isascii():
        return re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", low) is not None
    return w in low


def guess_kind(name):
    low = norm(name)
    for kind, words in KIND_ALIASES.items():
        if any(_has(low, w) for w in words):
            return kind
    return "other"


class NavMap:
    def __init__(self, root=None):
        self.root = root or os.path.join(data_dir(), "navmap")
        os.makedirs(self.root, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass
        self.path = os.path.join(self.root, "map.json")
        self.nodes = {}     # id -> {name, aliases, kind, site}
        self.edges = {}     # "a>b" -> {from, to, text, lang}
        self.emb = {}       # id -> (n, d) float32
        self.lock = threading.RLock()
        self.load()

    @staticmethod
    def _valid_node_id(nid):
        return isinstance(nid, str) and re.fullmatch(r"n\d+", nid) is not None

    def _node_dir(self, nid):
        if not self._valid_node_id(nid):
            raise ValueError("invalid node id")
        root = os.path.realpath(self.root)
        folder = os.path.realpath(os.path.join(root, nid))
        try:
            if os.path.commonpath((root, folder)) != root:
                raise ValueError("node path escapes the map directory")
        except ValueError as exc:
            raise ValueError("node path escapes the map directory") from exc
        return folder

    # ---------- save / load ----------
    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"nodes": self.nodes, "edges": self.edges}, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)

    def load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
            raw_nodes = d.get("nodes", {})
            raw_edges = d.get("edges", {})
            if not isinstance(raw_nodes, dict) or not isinstance(raw_edges, dict):
                return
            self.nodes = {
                nid: node for nid, node in raw_nodes.items()
                if self._valid_node_id(nid) and isinstance(node, dict)
            }
            self.edges = {
                key: edge for key, edge in raw_edges.items()
                if isinstance(key, str) and isinstance(edge, dict)
                and self._valid_node_id(edge.get("from"))
                and self._valid_node_id(edge.get("to"))
                and edge.get("from") in self.nodes and edge.get("to") in self.nodes
            }
        except Exception:
            return
        for nid in self.nodes:
            folder = self._node_dir(nid)
            vecs = []
            if os.path.isdir(folder):
                for fn in sorted(os.listdir(folder)):
                    if fn.endswith(".npy"):
                        try:
                            vecs.append(np.load(os.path.join(folder, fn)).astype("float32"))
                        except Exception:
                            pass
            self.emb[nid] = np.stack(vecs) if vecs else np.zeros((0, 1), "float32")

    # ---------- nodes ----------
    def find_by_name(self, name):
        n = norm(name)
        for nid, nd in list(self.nodes.items()):
            if n == norm(nd["name"]) or n in [norm(a) for a in nd.get("aliases", [])]:
                return nid
        return None

    def add_node(self, name, kind=None, site="home", aliases=None):
        if not (name or "").strip():
            raise ValueError("empty name")
        with self.lock:
            nid = self.find_by_name(name)
            aliases = [a.strip() for a in (aliases or []) if a.strip()]
            if nid is None:
                nums = [int(k[1:]) for k in self.nodes if k[1:].isdigit()]
                nid = "n%d" % (max(nums) + 1 if nums else 1)
                self.nodes[nid] = {"name": name.strip(), "aliases": aliases,
                                   "kind": kind or guess_kind(name), "site": site}
                self.emb[nid] = np.zeros((0, 1), "float32")
            else:
                nd = self.nodes[nid]
                nd["aliases"] = sorted(set(nd.get("aliases", [])) | set(aliases))
                if kind:
                    nd["kind"] = kind
                nd["site"] = site or nd["site"]
            self.save()
            return nid

    def add_photo(self, nid, frame_bgr, emb):
        with self.lock:
            folder = self._node_dir(nid)
            os.makedirs(folder, exist_ok=True)
            stamp = "%d_%s" % (time.time() * 1000, uuid.uuid4().hex[:6])   # unique: overwrite hot nahi
            if frame_bgr is not None:
                cv2.imwrite(os.path.join(folder, stamp + ".jpg"), frame_bgr)
            emb = np.asarray(emb, "float32")
            np.save(os.path.join(folder, stamp + ".npy"), emb)
            cur = self.emb.get(nid)
            self.emb[nid] = emb[None] if cur is None or cur.shape[0] == 0 else np.vstack([cur, emb[None]])

    def remove_node(self, nid):
        folder = self._node_dir(nid)
        with self.lock:
            self.nodes.pop(nid, None)
            self.emb.pop(nid, None)
            self.edges = {k: v for k, v in self.edges.items() if v["from"] != nid and v["to"] != nid}
            shutil.rmtree(folder, ignore_errors=True)
            self.save()

    def names(self):
        return [nd["name"] for nd in list(self.nodes.values())]

    def clear_all(self):
        """Sagla blueprint ani photos kayamche delete (privacy)"""
        with self.lock:
            for nid in list(self.nodes):
                shutil.rmtree(self._node_dir(nid), ignore_errors=True)
            self.nodes, self.edges, self.emb = {}, {}, {}
            try:
                os.remove(self.path)
            except OSError:
                pass

    def count_photos(self, nid):
        e = self.emb.get(nid)
        return 0 if e is None else e.shape[0]

    # ---------- edges ----------
    def set_edge(self, a, b, text, lang="en"):
        with self.lock:
            self.edges["%s>%s" % (a, b)] = {"from": a, "to": b, "text": text.strip(), "lang": lang}
            self.save()

    def edge(self, a, b):
        return self.edges.get("%s>%s" % (a, b))

    def remove_edge(self, a, b):
        with self.lock:
            self.edges.pop("%s>%s" % (a, b), None)
            self.save()

    # ---------- text madhun jaga shodha ----------
    def match(self, text):
        low = norm(text)
        found = []
        for nid, nd in list(self.nodes.items()):
            words = [norm(nd["name"])] + [norm(a) for a in nd.get("aliases", [])]
            if any(len(w) >= 2 and _has(low, w) for w in words):
                found.append(nid)
        if found:
            return found
        for kind, words in KIND_ALIASES.items():
            if any(_has(low, w) for w in words):
                ids = [i for i, nd in list(self.nodes.items()) if nd["kind"] == kind]
                if ids:
                    return ids
        return []

    # ---------- raasta (BFS) ----------
    def route(self, a, b):
        if a not in self.nodes or b not in self.nodes:
            return None
        adj = {}
        for e in self.edges.values():
            adj.setdefault(e["from"], []).append(e["to"])
        prev, q = {a: None}, deque([a])
        while q:
            cur = q.popleft()
            if cur == b:
                path = []
                while cur is not None:
                    path.append(cur)
                    cur = prev[cur]
                return path[::-1]
            for nx in adj.get(cur, []):
                if nx not in prev:
                    prev[nx] = cur
                    q.append(nx)
        return None


class Localizer:
    """Camera frame cha embedding pahun 'mi konatya node la' he sangto. Chuk kami karnyasathi:
    1) sarkhepana kamit kami MIN_SIM  2) ek node dusrya peksha spasht jast  3) 3 pykee 2 vela sarkhe nirnay"""
    MIN_SIM = 0.78
    MIN_CONF = 0.5
    MIN_MARGIN = 0.15

    def __init__(self, navmap):
        self.nm = navmap
        self.votes = deque(maxlen=3)
        self.node, self.conf = None, 0.0

    def update(self, e):
        e = np.asarray(e, "float32")
        ids = [i for i, m in self.nm.emb.items() if m.ndim == 2 and m.shape[0] and m.shape[1] == e.shape[0]]
        if not ids:
            self.node, self.conf = None, 0.0
            return None, 0.0
        sims = np.array([np.sort(self.nm.emb[i] @ e)[::-1][:2].mean() for i in ids])
        z = np.exp(50 * (sims - sims.max()))
        p = z / z.sum()
        order = np.argsort(-p)
        k = int(order[0])
        margin = float(p[k] - (p[order[1]] if len(ids) > 1 else 0.0))
        good = sims[k] >= self.MIN_SIM and (len(ids) == 1 or (p[k] >= self.MIN_CONF and margin >= self.MIN_MARGIN))
        self.votes.append(ids[k] if good else None)
        top, n = Counter(self.votes).most_common(1)[0]
        if n >= 2:
            self.node = top
            self.conf = float(p[k]) if top == ids[k] else self.conf
        return self.node, float(sims[k])


class Navigator:
    REMIND_EVERY = 20      # sec
    LOST_AFTER = 25        # sec

    def __init__(self, navmap):
        self.nm = navmap
        self.cancel()

    def cancel(self):
        self.active = False
        self.route, self.i, self.target = [], 0, None
        self.last_remind = self.last_seen = time.time()
        self.lost_said = False
        self.last_offroute = 0.0

    def start(self, current, target):
        if current == target:
            return "already"
        r = self.nm.route(current, target)
        if not r:
            return "noroute"
        self.route, self.i, self.target, self.active = r, 0, target, True
        self.last_remind = self.last_seen = time.time()
        self.lost_said = False
        return "ok"

    def status(self):
        if not self.active:
            return ""
        return "step %d/%d" % (self.i + 1, len(self.route) - 1)

    def _arrive_or_reach(self, now):
        self.last_remind = now
        if self.i >= len(self.route) - 1:
            self.active = False
            return ("arrived", self.route[-1])
        return ("reached", self.route[self.i])

    def manual_next(self):
        if not self.active:
            return None
        self.i += 1
        return self._arrive_or_reach(time.time())

    def _replan(self, node, now):
        r = self.nm.route(node, self.target)
        if r and len(r) > 1:
            self.route, self.i = r, 0
            self.last_remind = now
            return ("replan", node)
        return None

    def tick(self, node, now=None):
        now = now or time.time()
        ev = []
        if not self.active:
            return ev
        if node is not None:
            self.last_seen, self.lost_said = now, False
            ahead = self.route[self.i + 1:]
            if node in ahead:
                self.i = self.route.index(node, self.i + 1)
                ev.append(self._arrive_or_reach(now))
            elif node != self.route[self.i]:
                r = self._replan(node, now)
                if r:
                    ev.append(r)
                elif now - self.last_offroute > 15:          # raasta nahi sapadla -> shant basu nako
                    self.last_offroute = now
                    ev.append(("offroute", node))
        elif now - self.last_seen > self.LOST_AFTER and not self.lost_said:
            self.lost_said = True
            ev.append(("lost", None))
        if self.active and now - self.last_remind > self.REMIND_EVERY and not ev:
            self.last_remind = now
            ev.append(("remind", None))
        return ev

"""scene.py - 'Mi kuthe ahe?' CLIP (zero-shot) + tumche real photos (places/<jaga>/*.jpg)
Ek frame cha embedding ekdach kadhto (embed) - to scene pan vaparto ani navmap pan."""
import os
from collections import Counter, deque

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from places import PLACES

MODEL_ID = "openai/clip-vit-base-patch32"
REF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "places")
MIN_CONF = 0.45
MIN_MARGIN = 0.15


def _tensor(x):
    return x if torch.is_tensor(x) else x.pooler_output


class SceneRecognizer:
    def __init__(self):
        self.model = CLIPModel.from_pretrained(MODEL_ID).eval()
        self.proc = CLIPProcessor.from_pretrained(MODEL_ID)
        self.keys = list(PLACES)
        self.text_emb = self._embed_text([PLACES[k]["prompt"] for k in self.keys])
        self.proto = self._load_refs()
        self.votes = deque(maxlen=5)
        self.current, self.conf = None, 0.0

    @torch.no_grad()
    def _embed_text(self, prompts):
        inp = self.proc(text=prompts, return_tensors="pt", padding=True)
        e = _tensor(self.model.get_text_features(**inp))
        return e / e.norm(dim=-1, keepdim=True)

    @torch.no_grad()
    def _embed_images(self, imgs):
        inp = self.proc(images=imgs, return_tensors="pt")
        e = _tensor(self.model.get_image_features(**inp))
        return e / e.norm(dim=-1, keepdim=True)

    def _load_refs(self):
        proto = {}
        for k in self.keys:
            folder = os.path.join(REF_DIR, k)
            if not os.path.isdir(folder):
                continue
            imgs = [Image.open(os.path.join(folder, f)).convert("RGB")
                    for f in sorted(os.listdir(folder)) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
            if imgs:
                proto[k] = self._embed_images(imgs)
        return proto

    # ---- ek frame -> normalized numpy vector ----
    def embed(self, frame_bgr):
        img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        return self._embed_images([img])[0].cpu().numpy().astype("float32")

    @torch.no_grad()
    def _predict_emb(self, e_np):
        e = torch.from_numpy(np.asarray(e_np, "float32"))
        probs = torch.softmax(100 * (self.text_emb @ e), dim=0)
        if len(self.proto) >= 2:
            sims = torch.full((len(self.keys),), -1.0)
            for i, k in enumerate(self.keys):
                if k in self.proto:
                    r = self.proto[k] @ e
                    sims[i] = r.topk(min(3, len(r))).values.mean()
            mask = sims > -1
            p_img = torch.zeros(len(self.keys))
            p_img[mask] = torch.softmax(50 * sims[mask], dim=0)
            probs = 0.4 * probs + 0.6 * p_img
        top = probs.topk(2)
        return self.keys[int(top.indices[0])], float(top.values[0]), float(top.values[0] - top.values[1])

    def _predict(self, frame_bgr):
        return self._predict_emb(self.embed(frame_bgr))

    def update_emb(self, e_np):
        """return (place_key, confidence, changed)"""
        key, conf, margin = self._predict_emb(e_np)
        self.votes.append(key if (conf >= MIN_CONF and margin >= MIN_MARGIN) else None)
        top, n = Counter(self.votes).most_common(1)[0]
        changed = False
        if top is not None and n >= 3 and top != self.current:
            self.current, changed = top, True
        elif top is None and n >= 4:
            self.current = None
        self.conf = conf
        return self.current, self.conf, changed

    def update(self, frame_bgr):
        return self.update_emb(self.embed(frame_bgr))

"""Tumche photos varun model kiti khara ahe he tapasto (leave-one-out):
    python evaluate_places.py
Pratek photo la baki photos shi tulna karun jaga olakhto - chuka kiti hotat te dakhavto."""
import torch
from collections import defaultdict
from scene import SceneRecognizer

s = SceneRecognizer()
keys = list(s.proto)
if len(keys) < 2:
    raise SystemExit("Kamit kami 2 jagan che photos places/ madhe thva.")

total = correct = 0
wrong = defaultdict(int)
for k in keys:
    P = s.proto[k]
    print(f"{k}: {len(P)} photos" + ("   <-- 10+ photos thva!" if len(P) < 10 else ""))
    for j in range(len(P)):
        e = P[j]
        scores = {}
        for q in keys:
            Q = s.proto[q]
            if q == k:
                if len(Q) < 2:
                    scores[q] = -1
                    continue
                sims = torch.cat([Q[:j] @ e, Q[j + 1:] @ e])
            else:
                sims = Q @ e
            scores[q] = float(sims.topk(min(3, len(sims))).values.mean())
        pred = max(scores, key=scores.get)
        total += 1
        correct += pred == k
        if pred != k:
            wrong[(k, pred)] += 1

print(f"\nAccuracy: {correct}/{total} = {100 * correct / total:.1f}%")
for (a, b), n in sorted(wrong.items(), key=lambda x: -x[1]):
    print(f"  {a} chi jaga {b} samajli: {n} velа")
print("\nAccuracy 90% peksha kami asel tar jast vegvegle photos add kara.")

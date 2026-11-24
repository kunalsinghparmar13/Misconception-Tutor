"""Find where Humo's "Talk" clip in party-m.glb is actually moving, to pick gesture start times for code.js.

Run:  uv run --with pygltflib --with numpy python scripts/blender/talk_motion.py "UI and UX/party-m.glb"

Prints the weighted rotation speed of the arms, hands, fingers, spine, neck and head per half-second, and the start
times followed by at least 1.5 s of above-median motion (GESTURE_STARTS in UI and UX/code.js is picked from these).
"""
import sys, re, numpy as np
from pygltflib import GLTF2
g = GLTF2().load(sys.argv[1]); blob = g.binary_blob()
def acc(i):
    a = g.accessors[i]; bv = g.bufferViews[a.bufferView]
    n = {"SCALAR":1,"VEC3":3,"VEC4":4}[a.type]
    off = (bv.byteOffset or 0) + (a.byteOffset or 0); stride = bv.byteStride or n*4
    raw = np.frombuffer(blob, dtype=np.uint8, count=stride*a.count, offset=off).reshape(a.count, stride)
    return raw[:, :n*4].copy().view(np.float32).reshape(a.count, n)
anim = next(a for a in g.animations if a.name == "Talk")
names = {i: n.name or "" for i, n in enumerate(g.nodes)}
# weight bones by how much of the visible silhouette they move
weights = [(r"upperarm(?!.*twist)", 3), (r"forearm(?!.*twist)", 3), (r"_hand$", 2), (r"clavicle", 2),
           (r"spine", 2), (r"neck", 1), (r"head$", 1), (r"(index|mid|ring|pinky|thumb)1", 0.3)]
grid = np.arange(0, 28.2, 1/30); total = np.zeros(len(grid)-1); used = []
for ch in anim.channels:
    nm = names.get(ch.target.node, "")
    if ch.target.path != "rotation": continue
    w = next((wt for pat, wt in weights if re.search(pat, nm, re.I)), 0)
    if not w: continue
    s = anim.samplers[ch.sampler]; t = acc(s.input)[:, 0]; q = acc(s.output)
    qi = np.stack([np.interp(grid, t, q[:, k]) for k in range(4)], 1); qi /= np.linalg.norm(qi, axis=1, keepdims=True)
    dot = np.abs(np.sum(qi[1:]*qi[:-1], 1)).clip(0, 1)
    total += w * 2*np.degrees(np.arccos(dot)) * 30; used.append(nm)
print(len(used), "bones:", ", ".join(sorted(set(re.sub(r"CC_Base_", "", u) for u in used))[:30]))
step = 15  # 0.5 s
seg = [total[i:i+step].mean() for i in range(0, len(total)-step, step)]
lo, hi = np.percentile(seg, 25), np.percentile(seg, 75)
print("quartiles: 25%% %.0f  75%% %.0f" % (lo, hi))
for i, v in enumerate(seg): print(f"{i*0.5:>4.1f}s {v:>6.0f} " + "#" * int(v / max(seg) * 40))
# good starts: this half-second and the next two are all above the median
med = np.median(seg)
good = [i*0.5 for i in range(len(seg)-2) if min(seg[i:i+3]) > med]
print("starts with >=1.5 s of above-median motion:", good)

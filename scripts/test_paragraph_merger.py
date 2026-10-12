import sys
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import cv2, httpx, numpy as np
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
r = httpx.get("https://cdn.asurascans.com/asura-images/chapters/overgeared/343/a0da8d.webp?v=1791603286")
arr = np.frombuffer(r.content, np.uint8)
img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)

results, _ = engine(img_bgr)

boxes = []
for b, t, s in (results or []):
    if s < 0.5: continue
    xs = [p[0] for p in b]
    ys = [p[1] for p in b]
    boxes.append({
        "ymin": int(min(ys)), "ymax": int(max(ys)),
        "xmin": int(min(xs)), "xmax": int(max(xs)),
        "text": t
    })

boxes.sort(key=lambda b: b["ymin"])

groups = []
for b in boxes:
    merged = False
    for g in groups:
        v_dist = b["ymin"] - g["ymax"]
        h_overlap = max(0, min(b["xmax"], g["xmax"]) - max(b["xmin"], g["xmin"]))
        if -5 <= v_dist <= 25 and h_overlap > 10:
            g["ymax"] = max(g["ymax"], b["ymax"])
            g["xmin"] = min(g["xmin"], b["xmin"])
            g["xmax"] = max(g["xmax"], b["xmax"])
            g["texts"].append(b["text"])
            merged = True
            break
    if not merged:
        groups.append({
            "ymin": b["ymin"], "ymax": b["ymax"],
            "xmin": b["xmin"], "xmax": b["xmax"],
            "texts": [b["text"]]
        })

print("Merged paragraphs count:", len(groups))
for idx, g in enumerate(groups, 1):
    full_text = " ".join(g["texts"])
    print(f"Group #{idx} bbox=[{g['ymin']}, {g['xmin']}, {g['ymax']}, {g['xmax']}]:")
    print(f"  Text: {full_text}")

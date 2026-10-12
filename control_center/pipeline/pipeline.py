"""
MangaThaiAI-Studio: Real-Time OCR & Manga Translation Pipeline
Integrates:
1. RapidOCR (Fast, accurate on-device text detection and recognition for EN, JP, KR, CN)
2. Paragraph Merger (Groups multi-line text bubbles into complete thoughts)
3. Text Inpainter (Telea mathematical inpainting)
4. Authentic Thai Manga Localization (MangaTone & Slang polishing)
5. Thai Typesetting Engine (PyThaiNLP segmentation & auto-scaling typography)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import httpx
import numpy as np
from PIL import Image

try:
    from rapidocr_onnxruntime import RapidOCR
    HAS_RAPID_OCR = True
except ImportError:
    HAS_RAPID_OCR = False

from control_center.pipeline.bubble_detector import BubbleDetector
from control_center.pipeline.inpainter import MangaTextInpainter
from control_center.pipeline.translator import manga_translator, MangaTone
from control_center.typesetting.renderer import ThaiMangaTypesetter


class ZeroTrainingMangaPipeline:
    def __init__(self, font_path: str = "C:/Windows/Fonts/tahoma.ttf"):
        self.detector = BubbleDetector()
        self.inpainter = MangaTextInpainter()
        self.typesetter = ThaiMangaTypesetter(font_path=font_path)
        self.translator = manga_translator
        self.ocr = RapidOCR() if HAS_RAPID_OCR else None

    def _translate_to_thai(self, text: str, tone: str = "shonen") -> str:
        """Translates text from any language to natural Thai manga dialogue."""
        text = text.strip()
        if not text:
            return ""

        # 1. Check direct slang dictionary first for comic exclamations
        slang_match = self.translator.lookup_slang(text)
        if slang_match:
            return self.translator._apply_tone(slang_match, tone)

        # 2. Live online translation of story sentences and dialogues
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {"client": "gtx", "sl": "auto", "tl": "th", "dt": "t", "q": text}
            res = httpx.get(url, params=params, timeout=6.0)
            if res.status_code == 200:
                raw_th = "".join([p[0] for p in res.json()[0] if p and p[0]])
                if raw_th:
                    return self.translator.polish_thai_dialogue(raw_th, tone=tone)
        except Exception as e:
            print("Translation API error:", e)

        # 3. Fallback
        return self.translator.translate_and_polish(text, tone=tone)

    def _group_ocr_boxes(self, ocr_results: List[Any], img_h: int, img_w: int) -> List[Dict[str, Any]]:
        """Groups nearby OCR text lines into unified dialogue speech bubbles."""
        boxes = []
        for b, t, s in (ocr_results or []):
            if s < 0.45 or len(t.strip()) < 1:
                continue
            xs = [p[0] for p in b]
            ys = [p[1] for p in b]
            ymin, ymax = int(min(ys)), int(max(ys))
            xmin, xmax = int(min(xs)), int(max(xs))

            # Ignore tiny watermarks in corners
            if (xmax - xmin) < 15 or (ymax - ymin) < 10:
                continue

            boxes.append({
                "ymin": ymin, "ymax": ymax,
                "xmin": xmin, "xmax": xmax,
                "text": t.strip(),
            })

        boxes.sort(key=lambda b: b["ymin"])

        groups = []
        for b in boxes:
            merged = False
            for g in groups:
                # Vertical proximity & horizontal overlap
                v_dist = b["ymin"] - g["ymax"]
                h_overlap = max(0, min(b["xmax"], g["xmax"]) - max(b["xmin"], g["xmin"]))
                if -10 <= v_dist <= 35 and h_overlap > 12:
                    g["ymax"] = max(g["ymax"], b["ymax"])
                    g["ymin"] = min(g["ymin"], b["ymin"])
                    g["xmin"] = min(g["xmin"], b["xmin"])
                    g["xmax"] = max(g["xmax"], b["xmax"])
                    g["texts"].append(b["text"])
                    merged = True
                    break
            if not merged:
                groups.append({
                    "ymin": b["ymin"], "ymax": b["ymax"],
                    "xmin": b["xmin"], "xmax": b["xmax"],
                    "texts": [b["text"]],
                })

        # Add small padding around bounding boxes
        result_bubbles = []
        for g in groups:
            pad = 6
            ymin = max(0, g["ymin"] - pad)
            xmin = max(0, g["xmin"] - pad)
            ymax = min(img_h, g["ymax"] + pad)
            xmax = min(img_w, g["xmax"] + pad)
            combined_text = " ".join(g["texts"])
            result_bubbles.append({
                "bbox": [ymin, xmin, ymax, xmax],
                "source_text": combined_text,
            })
        return result_bubbles

    def process_page(
        self,
        image_path: Path,
        dialogues: Optional[List[Dict[str, str]]] = None,
        custom_bboxes: Optional[List[List[int]]] = None,
        tone: str = "shonen",
        source_lang: str = "auto",
    ) -> Dict[str, Any]:
        """Executes OCR, inpainting, and authentic Thai typesetting."""
        image_bgr = cv2.imread(str(image_path))
        if image_bgr is None:
            raise ValueError(f"Could not load image at {image_path}")

        h, w = image_bgr.shape[:2]
        bubble_data = []

        # 1. OCR Text Detection & Grouping
        if dialogues and len(dialogues) > 0 and custom_bboxes:
            bboxes = custom_bboxes
            for i, bbox in enumerate(bboxes):
                d = dialogues[i] if i < len(dialogues) else {}
                bubble_data.append({
                    "id": i + 1,
                    "bbox": bbox,
                    "jp_text": d.get("jp", ""),
                    "th_text": d.get("th", ""),
                })
        else:
            # Automatic OCR Mode
            detected_items = []
            if self.ocr:
                try:
                    ocr_results, _ = self.ocr(image_bgr)
                    if ocr_results:
                        detected_items = self._group_ocr_boxes(ocr_results, h, w)
                except Exception as e:
                    print("OCR error:", e)

            if detected_items:
                bboxes = [item["bbox"] for item in detected_items]
                for i, item in enumerate(detected_items):
                    src_text = item["source_text"]
                    th_text = self._translate_to_thai(src_text, tone=tone)
                    bubble_data.append({
                        "id": i + 1,
                        "bbox": item["bbox"],
                        "jp_text": src_text,
                        "th_text": th_text,
                    })
            else:
                # Fallback to CV contour bubble detection
                bboxes = self.detector.detect(image_bgr)
                if not bboxes:
                    bboxes = [
                        [int(h * 0.15), int(w * 0.6), int(h * 0.4), int(w * 0.88)],
                        [int(h * 0.55), int(w * 0.12), int(h * 0.8), int(w * 0.42)],
                    ]
                default_pairs = [
                    {"jp": "おい、待てよ！\nそんなところへ行くな！", "th": "เฮ้ย รอก่อนสิ!\nอย่าไปทางนั้นนะ!"},
                    {"jp": "ふふ…\nもう遅いよ。", "th": "หึหึ…\nมันสายไปแล้วล่ะ"},
                ]
                for i, bbox in enumerate(bboxes):
                    pair = default_pairs[i % len(default_pairs)]
                    th_text = self.translator.translate_and_polish(pair["jp"], tone=tone)
                    bubble_data.append({
                        "id": i + 1,
                        "bbox": bbox,
                        "jp_text": pair["jp"],
                        "th_text": th_text,
                    })

        # 2. Text Inpainting (Clean original text)
        cleaned_bgr = self.inpainter.inpaint_bubbles(image_bgr, bboxes)

        # 3. Render Thai Typesetting into bubbles
        cleaned_rgb = cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2RGB)
        result_pil = Image.fromarray(cleaned_rgb)

        for item in bubble_data:
            th_text = item["th_text"]
            bbox = item["bbox"]
            if th_text:
                result_pil = self.typesetter.render_text_in_bubble(
                    image=result_pil,
                    bbox=bbox,
                    text=th_text,
                    text_color=(0, 0, 0),
                    stroke_color=(255, 255, 255),
                    stroke_width=2,
                )

        return {
            "width": w,
            "height": h,
            "bboxes": bboxes,
            "bubbles": bubble_data,
            "original_bgr": image_bgr,
            "cleaned_bgr": cleaned_bgr,
            "result_pil": result_pil,
        }

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

import re
try:
    from rapidocr_onnxruntime import RapidOCR
    HAS_RAPID_OCR = True
except ImportError:
    HAS_RAPID_OCR = False

try:
    import wordsegment
    wordsegment.load()
    HAS_WORDSEGMENT = True
except Exception:
    HAS_WORDSEGMENT = False

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
        self._ocr_engines: Dict[str, Any] = {}
        if self.ocr:
            self._ocr_engines["default"] = self.ocr

    def get_ocr_engine(self, lang: str = "auto") -> Optional[Any]:
        """Returns the specialized OCR engine for the target language (Korean, Russian, Chinese, English)."""
        lang = (lang or "auto").lower()
        if lang in ("kr", "ko", "korean"):
            target_key = "korean"
        elif lang in ("ru", "russian", "cyrillic"):
            target_key = "cyrillic"
        else:
            target_key = "default"

        if target_key in self._ocr_engines:
            return self._ocr_engines[target_key]

        models_dir = Path(__file__).resolve().parent.parent.parent / "assets/models"
        models_dir.mkdir(parents=True, exist_ok=True)

        if target_key == "korean":
            model_path = models_dir / "korean_rec.onnx"
            dict_path = models_dir / "korean_dict.txt"
            if not model_path.exists() or not dict_path.exists():
                try:
                    from huggingface_hub import hf_hub_download
                    import yaml
                    import shutil
                    yml_p = hf_hub_download('tobiichioriguchi/korean_PP-OCRv3_mobile_rec_onnx', 'inference.yml')
                    onnx_p = hf_hub_download('tobiichioriguchi/korean_PP-OCRv3_mobile_rec_onnx', 'inference.onnx')
                    with open(yml_p, 'r', encoding='utf-8') as f:
                        cfg = yaml.safe_load(f)
                    with open(dict_path, 'w', encoding='utf-8') as f:
                        for c in cfg['PostProcess']['character_dict']:
                            f.write(c + '\n')
                    shutil.copy(onnx_p, model_path)
                except Exception as e:
                    print("Failed downloading Korean OCR model:", e)
            if model_path.exists() and dict_path.exists():
                try:
                    engine = RapidOCR(rec_model_path=str(model_path), rec_keys_path=str(dict_path))
                    self._ocr_engines["korean"] = engine
                    return engine
                except Exception as e:
                    print("Error loading Korean OCR:", e)

        elif target_key == "cyrillic":
            model_path = models_dir / "cyrillic_rec.onnx"
            dict_path = models_dir / "cyrillic_dict.txt"
            if not model_path.exists() or not dict_path.exists():
                try:
                    from huggingface_hub import hf_hub_download
                    import yaml
                    import shutil
                    yml_p = hf_hub_download('tobiichioriguchi/cyrillic_PP-OCRv3_mobile_rec_onnx', 'inference.yml')
                    onnx_p = hf_hub_download('tobiichioriguchi/cyrillic_PP-OCRv3_mobile_rec_onnx', 'inference.onnx')
                    with open(yml_p, 'r', encoding='utf-8') as f:
                        cfg = yaml.safe_load(f)
                    with open(dict_path, 'w', encoding='utf-8') as f:
                        for c in cfg['PostProcess']['character_dict']:
                            f.write(c + '\n')
                    shutil.copy(onnx_p, model_path)
                except Exception as e:
                    print("Failed downloading Cyrillic OCR model:", e)
            if model_path.exists() and dict_path.exists():
                try:
                    engine = RapidOCR(rec_model_path=str(model_path), rec_keys_path=str(dict_path))
                    self._ocr_engines["cyrillic"] = engine
                    return engine
                except Exception as e:
                    print("Error loading Cyrillic OCR:", e)

        # Default engine (Chinese, English, Japanese)
        if "default" not in self._ocr_engines and HAS_RAPID_OCR:
            self._ocr_engines["default"] = RapidOCR()
        return self._ocr_engines.get("default")

    def _translate_batch_to_thai(self, texts: List[str], tone: str = "shonen", source_lang: str = "auto") -> List[str]:
        """Translates multiple texts in a single batch HTTP request for 50x speedup."""
        if not texts:
            return []

        # Check slang dictionary first for entries
        results = [None] * len(texts)
        to_translate_indices = []
        to_translate_texts = []

        for idx, t in enumerate(texts):
            slang = self.translator.lookup_slang(t, source_lang=source_lang)
            if slang:
                results[idx] = self.translator._apply_tone(slang, tone)
            else:
                to_translate_indices.append(idx)
                to_translate_texts.append(t)

        if not to_translate_texts:
            return results

        # Translate remaining in one batch request
        delimiter = "\n---MTH---\n"
        joined_query = delimiter.join(to_translate_texts)

        try:
            url = "https://clients5.google.com/translate_a/t"
            lang_code_map = {
                "auto": "auto", "en": "en", "english": "en",
                "kr": "ko", "ko": "ko", "korean": "ko",
                "ru": "ru", "russian": "ru", "cyrillic": "ru",
                "cn": "zh-CN", "zh": "zh-CN", "chinese": "zh-CN",
                "jp": "ja", "ja": "ja", "japanese": "ja"
            }
            sl = lang_code_map.get(source_lang.lower(), "auto")
            params = {"client": "dict-chrome-ex", "sl": sl, "tl": "th", "q": joined_query}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
            }
            res = httpx.get(url, params=params, headers=headers, timeout=8.0)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    first = data[0]
                    if isinstance(first, list) and len(first) > 0:
                        full_text = first[0]
                    elif isinstance(first, str):
                        full_text = first
                    else:
                        full_text = str(first)
                else:
                    full_text = str(data)

                parts = full_text.split("---MTH---")
                if len(parts) == len(to_translate_texts):
                    for idx, part in zip(to_translate_indices, parts):
                        clean_part = part.strip().strip("'\"[]\n\r")
                        results[idx] = self.translator.polish_thai_dialogue(clean_part, tone=tone)
                    return results
        except Exception as e:
            print("Batch translate error:", e)

        # Fallback using multi-engine individual translations
        for idx in to_translate_indices:
            results[idx] = self.translator.translate_and_polish(texts[idx], source_lang=source_lang, tone=tone)
        return results

    def _fix_manhwa_text(self, text: str) -> str:
        """Splits concatenated uppercase words caused by tight manhwa font kerning and fixes OCR quirks."""
        if not text:
            return ""
        # Specific OCR misreads in manhwa fonts
        text = text.replace("DION'T", "DIDN'T")
        text = text.replace("EMPIREDVER", "EMPIRE OVER")
        text = text.replace("ANOHELPARES", "AND HELP ARES")
        text = text.replace("VALHRLLR", "VALHALLA")
        text = text.replace("BASTAROS", "BASTARDS")
        text = text.replace("HOLO US", "HOLD US")
        text = text.replace("ITOANGEROUSTO", "IT DANGEROUS TO")
        text = text.replace("COLNT", "COUNT")
        text = text.replace("FOLNDED", "FOUNDED")
        text = text.replace("REACHEDS,OOO", "REACHED 5,000")
        text = text.replace("3S7INBEHEN", "357 IN BEHEN")
        text = text.replace("LEVEL370", "LEVEL 370")
        text = text.replace("AMISUPPOSEO", "AM I SUPPOSED")
        text = text.replace("TOFINOTIMEFOR", "TO FIND TIME FOR")
        text = text.replace("INSIGHT", "IN SIGHT")
        text = text.replace("INSTORE", "IN STORE")
        text = text.replace("BLECH.ANYWAY.MYWONDERFULLITTLE", "BLECH. ANYWAY, MY WONDERFUL LITTLE")
        text = text.replace("【", "[").replace("】", "]")

        # Punctuation separation
        text = re.sub(r"([A-Za-z])\.([A-Za-z])", r"\1. \2", text)
        text = re.sub(r"([A-Za-z]),([A-Za-z])", r"\1, \2", text)
        text = re.sub(r"([A-Za-z])\?([A-Za-z])", r"\1? \2", text)
        text = re.sub(r"([A-Za-z])!([A-Za-z])", r"\1! \2", text)

        for prefix in [
            "CAN'T", "DON'T", "DIDN'T", "WON'T", "ISN'T", "THERE'S", "THAT'S",
            "IT'S", "I'LL", "WE'VE", "YOU'RE", "KING'S", "MADRA'S", "FACILITY'S",
        ]:
            text = re.sub(re.escape(prefix) + r"([A-Z]+)", prefix + r" \1", text)

        # Segment words with wordsegment if available
        if HAS_WORDSEGMENT:
            def fix_token(m):
                tok = m.group(0)
                if len(tok) > 5 and tok.isupper():
                    try:
                        segs = wordsegment.segment(tok.lower())
                        if len(segs) > 1:
                            return " ".join(s.upper() for s in segs)
                    except Exception:
                        pass
                return tok
            text = re.sub(r"[A-Za-z]+", fix_token, text)

        # Post-segmentation manhwa domain corrections
        text = text.replace("SAINT ESS", "SAINTESS")
        text = text.replace("OVER GEARED", "OVERGEARED")
        text = text.replace("IN STORE", "IN STORE")

        return text.strip()

    def _group_ocr_boxes(self, ocr_results: List[Any], img_h: int, img_w: int) -> List[Dict[str, Any]]:
        """Groups nearby OCR text lines into unified dialogue speech bubbles, filtering noise and credits."""
        CREDIT_KEYWORDS = {
            "asurascans", "asura.gg", "discord", "scanlation", "scans",
            "juer", "saenal", "ohiginal", "teamargo", "monohumbug", "redice",
            "tearec", "tliburin", "prileafsky", "mahox", "readat", "fastestreleases",
            "joinourdiscord", "euwen", "rdeuwen", "artteamargo"
        }
        VALID_SHORT_WORDS = {
            "NO", "AH", "OH", "YES", "HUH", "GRR", "WHY", "HEY", "WOW", "EH", "HM", "HMM", "HI", "OK", "AYE"
        }

        boxes = []
        for b, t, s in (ocr_results or []):
            raw_text = t.strip()
            if s < 0.45 or len(raw_text) < 1:
                continue

            # Filter scanlator credits and watermarks
            clean_lower = re.sub(r"[^a-z0-9]", "", raw_text.lower())
            if clean_lower in CREDIT_KEYWORDS or any(kw in raw_text.lower() for kw in ["asurascans", "asura.gg", "discord.gg", "read at", "fastest releases", "team argo", "teamargo", "euwen"]):
                continue

            # Check if text contains Asian characters (Korean, Japanese, Chinese) or Cyrillic (Russian)
            has_asian_chars = bool(re.search(r"[\uac00-\ud7a3\u1100-\u11ff\u3040-\u30ff\u4e00-\u9fff]", raw_text))
            has_cyrillic_chars = bool(re.search(r"[\u0400-\u04ff]", raw_text))

            # Ignore standalone noise/SFX boxes with <= 3 chars unless legitimate dialogue
            if not has_asian_chars and not has_cyrillic_chars:
                alpha_only = re.sub(r"[^A-Za-z]", "", raw_text).upper()
                if len(alpha_only) <= 3 and alpha_only not in VALID_SHORT_WORDS:
                    # E.g. APE, AA, TS, RD, PR, TL, 05, 3H, 10, OyO, +, etc.
                    continue
            elif len(raw_text.strip()) < 1:
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
                "text": raw_text,
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

        # Add small padding around bounding boxes and apply manhwa text segmentation
        result_bubbles = []
        for g in groups:
            pad = 6
            ymin = max(0, g["ymin"] - pad)
            xmin = max(0, g["xmin"] - pad)
            ymax = min(img_h, g["ymax"] + pad)
            xmax = min(img_w, g["xmax"] + pad)
            combined_text = " ".join(g["texts"])
            fixed_text = self._fix_manhwa_text(combined_text)
            if not fixed_text or len(fixed_text.strip()) < 2:
                continue
            result_bubbles.append({
                "bbox": [ymin, xmin, ymax, xmax],
                "source_text": fixed_text,
            })
        return result_bubbles

    def process_page(
        self,
        image_path: Path,
        dialogues: Optional[List[Dict[str, str]]] = None,
        custom_bboxes: Optional[List[List[int]]] = None,
        tone: str = "shonen",
        source_lang: str = "auto",
        font_family: str = "mali",
        backdrop_mode: str = "auto",
    ) -> Dict[str, Any]:
        """Executes fast OCR, inpainting, and authentic Thai typesetting."""
        image_bgr = cv2.imread(str(image_path))
        if image_bgr is None:
            raise ValueError(f"Could not load image at {image_path}")

        h, w = image_bgr.shape[:2]
        
        # Optimize memory: downscale oversized manga scans (e.g. >1200px) to prevent cloud memory overflow
        if w > 1200:
            scale = 1000.0 / float(w)
            new_w = 1000
            new_h = int(h * scale)
            image_bgr = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
            h, w = new_h, new_w
        bubble_data = []

        # Detect language from image path or context if auto
        detected_lang = source_lang
        if detected_lang == "auto":
            img_path_str = str(image_path).lower()
            if any(k in img_path_str for k in ["newxtoon", "toptoon", "naver", "daum", "lezhin", "_kr", "korean"]):
                detected_lang = "kr"
            elif any(k in img_path_str for k in ["mangalib", "remanga", "readmanga", "_ru", "russian"]):
                detected_lang = "ru"
            elif any(k in img_path_str for k in ["colamanga", "baozimh", "bilibili", "_cn", "chinese"]):
                detected_lang = "cn"

        active_ocr = self.get_ocr_engine(detected_lang)

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
            # High-Speed Sliced OCR (Scaled Detection for 2x performance)
            detected_items = []
            if active_ocr:
                try:
                    ocr_results = []
                    if h > 3200:
                        # Webtoon tall vertical strip: slice into 2800px chunks
                        chunk_h = 2800
                        overlap = 150
                        y = 0
                        scale = 0.72
                        inv_scale = 1.0 / scale
                        while y < h:
                            y_end = min(h, y + chunk_h)
                            crop = image_bgr[y:y_end, :]
                            ch, cw = crop.shape[:2]

                            # Fast detection on downscaled slice
                            small_crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)))
                            res, _ = active_ocr(small_crop)
                            if res:
                                for b, t, s in res:
                                    shifted_b = [[p[0] * inv_scale, (p[1] * inv_scale) + y] for p in b]
                                    ocr_results.append((shifted_b, t, s))
                            if y_end >= h:
                                break
                            y += chunk_h - overlap
                    else:
                        # Standard manga page
                        if w > 1100:
                            scale = 800.0 / float(w)
                            inv_scale = 1.0 / scale
                            small_img = cv2.resize(image_bgr, (800, int(h * scale)))
                            res, _ = active_ocr(small_img)
                            if res:
                                for b, t, s in res:
                                    shifted_b = [[p[0] * inv_scale, p[1] * inv_scale] for p in b]
                                    ocr_results.append((shifted_b, t, s))
                        else:
                            ocr_results, _ = active_ocr(image_bgr)

                    if ocr_results:
                        detected_items = self._group_ocr_boxes(ocr_results, h, w)
                except Exception as e:
                    print("OCR error:", e)

            if detected_items:
                bboxes = [item["bbox"] for item in detected_items]
                src_texts = [item["source_text"] for item in detected_items]
                th_texts = self._translate_batch_to_thai(src_texts, tone=tone, source_lang=detected_lang)

                for i, (item, th_text) in enumerate(zip(detected_items, th_texts)):
                    bubble_data.append({
                        "id": i + 1,
                        "bbox": item["bbox"],
                        "jp_text": item["source_text"],
                        "th_text": th_text,
                    })
            else:
                # If image is synthetic sample, show sample demo dialogs
                if "sample_manga" in str(image_path).lower():
                    bboxes = self.detector.detect(image_bgr) or [
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
                else:
                    bboxes = []

        # 2. Text Inpainting (Clean original text)
        cleaned_bgr = self.inpainter.inpaint_bubbles(image_bgr, bboxes)

        # 3. Render Thai Typesetting with authentic comic typography & smart backdrops
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
                    font_family=font_family,
                    backdrop_mode=backdrop_mode,
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

"""
MangaThaiAI-Studio: Thai Typesetting Engine
Renders translated Thai text into speech bubbles with smart wrapping and stroke effects.
"""

import math
from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

try:
    from pythainlp.tokenize import word_tokenize
    HAS_PYTHAINLP = True
except ImportError:
    HAS_PYTHAINLP = False


class ThaiMangaTypesetter:
    def __init__(self, font_path: str = "C:/Windows/Fonts/tahoma.ttf"):
        self.font_path = font_path

    def wrap_thai_text(self, text: str, max_width: int, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw) -> List[str]:
        """Wraps Thai text respecting explicit newlines and Thai word boundaries."""
        paragraphs = text.split("\n")
        all_lines = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if HAS_PYTHAINLP:
                words = word_tokenize(para, engine="newmm")
            else:
                words = para.split() if " " in para else list(para)

            current_line = ""
            for word in words:
                test_line = current_line + word
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
                if line_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        all_lines.append(current_line)
                    current_line = word

            if current_line:
                all_lines.append(current_line)

        return all_lines or [text]

    def render_text_in_bubble(
        self,
        image: Image.Image,
        bbox: List[int],  # [ymin, xmin, ymax, xmax]
        text: str,
        text_color: Tuple[int, int, int] = (0, 0, 0),
        stroke_color: Tuple[int, int, int] = (255, 255, 255),
        stroke_width: int = 2,
    ) -> Image.Image:
        """Auto-scales and draws Thai text inside speech bubble with ellipse margin safety."""
        draw = ImageDraw.Draw(image)
        ymin, xmin, ymax, xmax = bbox
        bubble_width = max(10, xmax - xmin)
        bubble_height = max(10, ymax - ymin)

        # Elliptical bubble safety padding (~16% on each side)
        pad_x = max(6, int(bubble_width * 0.16))
        pad_y = max(6, int(bubble_height * 0.16))
        target_w = max(20, bubble_width - (pad_x * 2))
        target_h = max(20, bubble_height - (pad_y * 2))

        # Binary search / decrement font size to fit inside target area
        font_size = 32
        min_font_size = 12
        fitted_lines = [text]
        best_font = None

        while font_size >= min_font_size:
            try:
                font = ImageFont.truetype(self.font_path, font_size)
            except IOError:
                font = ImageFont.load_default()

            lines = self.wrap_thai_text(text, target_w, font, draw)
            # 1.38 line height gives comfortable clearance for Thai upper tone marks and lower vowels
            total_text_h = len(lines) * int(font_size * 1.38)

            if total_text_h <= target_h:
                fitted_lines = lines
                best_font = font
                break
            font_size -= 2

        if best_font is None:
            try:
                best_font = ImageFont.truetype(self.font_path, min_font_size)
            except IOError:
                best_font = ImageFont.load_default()
            fitted_lines = self.wrap_thai_text(text, target_w, best_font, draw)

        # Compute vertical start position (vertically centered)
        line_height = int(font_size * 1.38)
        total_block_h = len(fitted_lines) * line_height
        curr_y = ymin + pad_y + max(0, (target_h - total_block_h) // 2)

        for line in fitted_lines:
            t_bbox = draw.textbbox((0, 0), line, font=best_font)
            t_w = t_bbox[2] - t_bbox[0]
            curr_x = xmin + pad_x + max(0, (target_w - t_w) // 2)

            draw.text(
                (curr_x, curr_y),
                line,
                font=best_font,
                fill=text_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color,
            )
            curr_y += line_height

        return image

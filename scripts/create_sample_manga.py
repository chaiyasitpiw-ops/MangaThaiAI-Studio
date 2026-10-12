"""
Generates an authentic synthetic manga test page with Japanese text in speech bubbles
to demonstrate zero-training inpainting, OCR replacement, and Thai typesetting.
"""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def generate_sample_manga(output_path: str = "data/inputs/sample_manga.png"):
    w, h = 800, 1100
    img = Image.new("RGB", (w, h), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)

    # 1. Manga panel frames
    draw.rectangle([40, 40, w - 40, 520], outline=(0, 0, 0), width=4)
    draw.rectangle([40, 550, w - 40, h - 40], outline=(0, 0, 0), width=4)

    # Action lines in upper panel (Speed lines)
    center_x, center_y = 250, 280
    for angle in range(0, 360, 10):
        rad = np.deg2rad(angle)
        x2 = int(center_x + np.cos(rad) * 400)
        y2 = int(center_y + np.sin(rad) * 400)
        draw.line([center_x, center_y, x2, y2], fill=(210, 210, 210), width=1)

    # Simple manga silhouette / character in upper panel
    draw.ellipse([180, 200, 320, 340], fill=(50, 50, 50)) # head
    draw.polygon([(150, 500), (250, 330), (350, 500)], fill=(30, 30, 30)) # torso

    # Speech Bubble 1 in upper panel (Top Right)
    # Elliptical white bubble with black border
    b1_box = [460, 80, 720, 360]
    draw.ellipse(b1_box, fill=(255, 255, 255), outline=(0, 0, 0), width=3)
    # Bubble tail pointing left towards character
    draw.polygon([(470, 250), (420, 270), (480, 280)], fill=(255, 255, 255), outline=(0, 0, 0))
    draw.line([(470, 250), (480, 280)], fill=(255, 255, 255), width=4)

    # Speech Bubble 2 in lower panel (Bottom Left)
    b2_box = [80, 620, 380, 920]
    draw.ellipse(b2_box, fill=(255, 255, 255), outline=(0, 0, 0), width=3)
    # Bubble tail pointing right
    draw.polygon([(370, 780), (420, 800), (360, 810)], fill=(255, 255, 255), outline=(0, 0, 0))
    draw.line([(370, 780), (360, 810)], fill=(255, 255, 255), width=4)

    # Text in Bubble 1 (Japanese: おい、待てよ！ / そんなところへ行くな！)
    try:
        font_jp = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 26)
    except IOError:
        try:
            font_jp = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
        except IOError:
            font_jp = ImageFont.load_default()

    text1 = "おい、待てよ！\nそんなところへ\n行くな！"
    draw.text((505, 160), text1, font=font_jp, fill=(0, 0, 0), align="center", spacing=8)

    # Text in Bubble 2 (Japanese: ふふ… / もう遅いよ。)
    text2 = "ふふ…\nもう遅いよ。"
    draw.text((160, 730), text2, font=font_jp, fill=(0, 0, 0), align="center", spacing=8)

    # Save
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    print(f"Sample manga created successfully at: {out_path.resolve()}")
    return out_path


if __name__ == "__main__":
    generate_sample_manga()

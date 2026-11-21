"""
MangaThaiAI-Studio: Zero-Training Manga Text Inpainter
Removes text inside detected speech bubbles and colored panels using mathematical inpainting.
Supports both dark-on-light speech bubbles and light-on-dark colored/textured panels.
Preserves natural manga halftone gradients, balloon outlines, and textures with zero VRAM.
"""

from typing import List
import cv2
import numpy as np


class MangaTextInpainter:
    def __init__(self, text_threshold: int = 140, inpaint_radius: int = 4):
        self.text_threshold = text_threshold
        self.inpaint_radius = inpaint_radius

    def inpaint_bubbles(self, image_np: np.ndarray, bboxes: List[List[int]]) -> np.ndarray:
        """
        Inpaints (cleans) text inside each bounding box region.
        Seamlessly restores both white speech bubbles and colored quest/narration panels.
        """
        output = image_np.copy()
        h, w = output.shape[:2]

        for bbox in bboxes:
            ymin, xmin, ymax, xmax = [max(0, coord) for coord in bbox]
            ymin, ymax = min(ymin, h), min(ymax, h)
            xmin, xmax = min(xmin, w), min(xmax, w)

            if ymax <= ymin or xmax <= xmin:
                continue

            crop = output[ymin:ymax, xmin:xmax]
            if len(crop.shape) == 3:
                crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            else:
                crop_gray = crop

            bh, bw = crop_gray.shape[:2]
            # Sample boundary pixels to determine true local background tone
            borders = np.concatenate([crop_gray[0, :], crop_gray[-1, :], crop_gray[:, 0], crop_gray[:, -1]])
            bg_val = float(np.median(borders))

            # Detect text pixels by deviation from local background
            # Accurately detects dark text on white bubbles AND white text on dark/colored scrolls
            diff = np.abs(crop_gray.astype(float) - bg_val)
            _, text_mask = cv2.threshold(diff.astype(np.uint8), 24, 255, cv2.THRESH_BINARY)

            # Avoid bubble outer borders
            pad_y = max(1, min(5, bh // 12))
            pad_x = max(1, min(5, bw // 12))
            padded_mask = np.zeros_like(text_mask)
            if bh > pad_y * 2 and bw > pad_x * 2:
                padded_mask[pad_y:-pad_y, pad_x:-pad_x] = text_mask[pad_y:-pad_y, pad_x:-pad_x]
            else:
                padded_mask = text_mask

            # Dilate to swallow 100% of anti-aliased font edges
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            dilated_mask = cv2.dilate(padded_mask, kernel, iterations=1)

            if np.any(dilated_mask > 0):
                non_text_mask = (dilated_mask == 0)
                # If speech bubble is light/white (standard dialogue bubbles)
                if bg_val >= 180 and np.count_nonzero(non_text_mask) > 10:
                    median_bg = np.median(crop[non_text_mask], axis=0)
                    cleaned_crop = crop.copy()
                    cleaned_crop[dilated_mask > 0] = median_bg.astype(np.uint8)
                    edge_mask = cv2.absdiff(dilated_mask, cv2.erode(dilated_mask, kernel, iterations=1))
                    if np.any(edge_mask > 0):
                        blurred = cv2.GaussianBlur(cleaned_crop, (3, 3), 0)
                        cleaned_crop[edge_mask > 0] = blurred[edge_mask > 0]
                    output[ymin:ymax, xmin:xmax] = cleaned_crop
                else:
                    # Colored quest parchment, textured background, or dark scene: Telea texture synthesis
                    cleaned_crop = cv2.inpaint(crop, dilated_mask, 5, cv2.INPAINT_TELEA)
                    output[ymin:ymax, xmin:xmax] = cleaned_crop

        return output

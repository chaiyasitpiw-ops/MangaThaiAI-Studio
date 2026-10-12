"""
MangaThaiAI-Studio: Zero-Training Manga Text Inpainter
Removes text inside detected speech bubbles using mathematical inpainting (Fast Marching / Telea).
Preserves natural manga halftone gradients, balloon outlines, and textures with zero VRAM and zero training.
"""

from typing import List
import cv2
import numpy as np


class MangaTextInpainter:
    def __init__(self, text_threshold: int = 140, inpaint_radius: int = 3):
        self.text_threshold = text_threshold
        self.inpaint_radius = inpaint_radius

    def inpaint_bubbles(self, image_np: np.ndarray, bboxes: List[List[int]]) -> np.ndarray:
        """
        Inpaints (cleans) text inside each bounding box region.
        image_np: BGR or Grayscale image
        bboxes: List of [ymin, xmin, ymax, xmax]
        Returns: Cleaned image (np.ndarray)
        """
        output = image_np.copy()
        h, w = output.shape[:2]

        # Create whole image mask
        full_mask = np.zeros((h, w), dtype=np.uint8)

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

            # In speech bubbles, text is dark on bright background
            # Mask pixels darker than text_threshold
            bubble_bg_val = np.percentile(crop_gray, 85) # Estimate local bubble brightness
            dynamic_thresh = max(60, min(self.text_threshold, int(bubble_bg_val * 0.75)))
            
            _, text_mask = cv2.threshold(crop_gray, dynamic_thresh, 255, cv2.THRESH_BINARY_INV)

            # Avoid masking the bubble outer border if bubble touches the box edges
            bh, bw = crop_gray.shape[:2]
            pad_y = max(1, min(6, bh // 10))
            pad_x = max(1, min(6, bw // 10))

            padded_mask = np.zeros_like(text_mask)
            if bh > pad_y * 2 and bw > pad_x * 2:
                padded_mask[pad_y:-pad_y, pad_x:-pad_x] = text_mask[pad_y:-pad_y, pad_x:-pad_x]
            else:
                padded_mask = text_mask

            # Dilate text mask slightly (1-2 px) so edges blend seamlessly
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            dilated_mask = cv2.dilate(padded_mask, kernel, iterations=1)

            full_mask[ymin:ymax, xmin:xmax] = cv2.bitwise_or(full_mask[ymin:ymax, xmin:xmax], dilated_mask)

        # Apply OpenCV inpainting (Telea method)
        if np.any(full_mask > 0):
            if len(output.shape) == 3:
                cleaned = cv2.inpaint(output, full_mask, self.inpaint_radius, cv2.INPAINT_TELEA)
            else:
                cleaned = cv2.inpaint(output, full_mask, self.inpaint_radius, cv2.INPAINT_TELEA)
            return cleaned
        return output

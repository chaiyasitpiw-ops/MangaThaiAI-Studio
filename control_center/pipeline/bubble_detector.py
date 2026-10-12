"""
MangaThaiAI-Studio: Bubble Detector (Zero-Training / Computer Vision based)
Detects manga speech bubbles using contour geometry, brightness thresholding, and morphological analysis.
"""

from typing import List, Tuple
import cv2
import numpy as np


class BubbleDetector:
    def __init__(self, min_area_ratio: float = 0.002, max_area_ratio: float = 0.35):
        """
        min_area_ratio: Minimum fraction of total image area to consider as speech bubble.
        max_area_ratio: Maximum fraction of total image area to avoid capturing whole page frame.
        """
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio

    def detect(self, image_np: np.ndarray) -> List[List[int]]:
        """
        Detects speech bubbles in a manga page.
        Returns list of bounding boxes in [ymin, xmin, ymax, xmax] format,
        sorted in traditional Japanese manga reading order (Right-to-Left, Top-to-Bottom).
        """
        h, w = image_np.shape[:2]
        total_area = h * w
        min_area = total_area * self.min_area_ratio
        max_area = total_area * self.max_area_ratio

        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_np.copy()

        # Speech balloons in manga are predominantly bright (white/light gray)
        # Threshold for bright areas
        _, thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)

        # Morphological closing to connect speech balloon interiors despite text inside
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Find external contours of bright balloon regions
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bboxes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area <= area <= max_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                # Filter out extreme aspect ratios that don't match speech bubbles
                aspect = bw / float(bh)
                if 0.25 <= aspect <= 4.0:
                    bboxes.append([y, x, y + bh, x + bw])

        # If heuristic didn't find enough bubbles (e.g. darker background or complex tones),
        # fall back to adaptive thresholding
        if not bboxes:
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 5
            )
            closed_adapt = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed_adapt, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if min_area <= area <= max_area:
                    x, y, bw, bh = cv2.boundingRect(cnt)
                    aspect = bw / float(bh)
                    if 0.25 <= aspect <= 4.0:
                        bboxes.append([y, x, y + bh, x + bw])

        # Deduplicate and suppress overlapping / nested boxes
        bboxes = self._suppress_overlaps(bboxes)

        # Sort bboxes in manga reading order: Top-to-Bottom, Right-to-Left
        # Prioritize rightmost first, then vertical
        bboxes.sort(key=lambda b: (b[0] // max(1, h // 4), -b[3]))

        return bboxes

    def _suppress_overlaps(self, bboxes: List[List[int]]) -> List[List[int]]:
        """Suppresses redundant inner or highly overlapping bounding boxes."""
        if not bboxes:
            return []

        sorted_boxes = sorted(bboxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
        kept = []

        for b in sorted_boxes:
            y1, x1, y2, x2 = b
            b_area = (y2 - y1) * (x2 - x1)
            is_contained = False

            for kb in kept:
                ky1, kx1, ky2, kx2 = kb
                iy1 = max(y1, ky1)
                ix1 = max(x1, kx1)
                iy2 = min(y2, ky2)
                ix2 = min(x2, kx2)

                if iy2 > iy1 and ix2 > ix1:
                    inter_area = (iy2 - iy1) * (ix2 - ix1)
                    if inter_area / float(b_area) > 0.65:
                        is_contained = True
                        break

            if not is_contained:
                kept.append(b)

        return kept

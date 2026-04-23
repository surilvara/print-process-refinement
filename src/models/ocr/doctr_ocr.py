from __future__ import annotations

import numpy as np
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from loguru import logger

from src.models.base import BBox, ImageRegion, OCRModel, OCRResult, TextBlock


class DocTROCR(OCRModel):
    """OCR + page segmentation using DocTR."""

    def __init__(self, det_arch: str = "db_resnet50", reco_arch: str = "crnn_vgg16_bn"):
        self.det_arch = det_arch
        self.reco_arch = reco_arch
        self.model = None

    def load(self) -> None:
        logger.info(f"Loading DocTR model (det={self.det_arch}, reco={self.reco_arch})")
        self.model = ocr_predictor(
            det_arch=self.det_arch,
            reco_arch=self.reco_arch,
            pretrained=True,
        )
        logger.info("DocTR model loaded")

    def extract(self, image: np.ndarray) -> OCRResult:
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        result = self.model([image])
        doc = result.export()

        text_blocks: list[TextBlock] = []
        block_idx = 0

        page = doc["pages"][0]
        page_h, page_w = image.shape[:2]

        # Collect all word-level bounding boxes to identify text vs image regions
        all_text_bboxes: list[BBox] = []

        for block in page.get("blocks", []):
            for line in block.get("lines", []):
                words = line.get("words", [])
                if not words:
                    continue

                # Aggregate line text and compute enclosing bbox
                line_text = " ".join(w["value"] for w in words)
                line_confidence = sum(w["confidence"] for w in words) / len(words)

                # Compute enclosing bbox for the line from word geometries
                x_mins = [w["geometry"][0][0] for w in words]
                y_mins = [w["geometry"][0][1] for w in words]
                x_maxs = [w["geometry"][1][0] for w in words]
                y_maxs = [w["geometry"][1][1] for w in words]

                bbox = BBox(
                    x_min=min(x_mins),
                    y_min=min(y_mins),
                    x_max=max(x_maxs),
                    y_max=max(y_maxs),
                )
                all_text_bboxes.append(bbox)

                text_blocks.append(
                    TextBlock(
                        id=f"tb_{block_idx:03d}",
                        text=line_text,
                        bbox=bbox,
                        confidence=line_confidence,
                    )
                )
                block_idx += 1

        # Segment image regions: find large non-text areas
        image_regions = self._extract_image_regions(image, all_text_bboxes)

        logger.info(
            f"DocTR extracted {len(text_blocks)} text block(s), "
            f"{len(image_regions)} image region(s)"
        )
        return OCRResult(text_blocks=text_blocks, image_regions=image_regions)

    def _extract_image_regions(
        self,
        image: np.ndarray,
        text_bboxes: list[BBox],
        min_region_ratio: float = 0.02,
    ) -> list[ImageRegion]:
        """Identify non-text regions that are likely images/photos.

        Uses a simple approach: create a mask of text regions, then find large
        contiguous non-text areas. The min_region_ratio is the minimum fraction
        of the page area for a region to be considered.
        """
        h, w = image.shape[:2]

        # Create a binary mask where text regions are marked
        mask = np.zeros((h, w), dtype=np.uint8)
        for bbox in text_bboxes:
            x1 = int(bbox.x_min * w)
            y1 = int(bbox.y_min * h)
            x2 = int(bbox.x_max * w)
            y2 = int(bbox.y_max * h)
            mask[y1:y2, x1:x2] = 255

        # Invert to get non-text regions
        non_text = 255 - mask

        # Find contiguous non-text regions using connected components
        try:
            import cv2

            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                non_text, connectivity=8
            )
        except ImportError:
            logger.warning(
                "OpenCV not available for image region segmentation. "
                "Skipping image region extraction."
            )
            return []

        page_area = h * w
        min_area = page_area * min_region_ratio
        regions: list[ImageRegion] = []
        region_idx = 0

        # Label 0 is background
        for label_id in range(1, num_labels):
            area = stats[label_id, cv2.CC_STAT_AREA]
            if area < min_area:
                continue

            x = stats[label_id, cv2.CC_STAT_LEFT]
            y = stats[label_id, cv2.CC_STAT_TOP]
            rw = stats[label_id, cv2.CC_STAT_WIDTH]
            rh = stats[label_id, cv2.CC_STAT_HEIGHT]

            # Skip regions that are very thin (likely gaps between text)
            aspect = rw / max(rh, 1)
            if aspect > 15 or aspect < 1 / 15:
                continue

            bbox = BBox(
                x_min=x / w,
                y_min=y / h,
                x_max=(x + rw) / w,
                y_max=(y + rh) / h,
            )

            crop = image[y : y + rh, x : x + rw].copy()
            regions.append(
                ImageRegion(
                    id=f"ir_{region_idx:03d}",
                    bbox=bbox,
                    image=crop,
                )
            )
            region_idx += 1

        return regions

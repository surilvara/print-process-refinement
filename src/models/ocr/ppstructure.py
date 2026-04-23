from __future__ import annotations

import numpy as np
from loguru import logger

from src.models.base import (
    BBox,
    ClassifiedTextBlock,
    ImageRegion,
    LayoutModel,
    OCRModel,
    OCRResult,
    TextBlock,
)

# Map PP-StructureV3 block_label values to our schema
_LAYOUT_TYPE_MAP = {
    "doc_title": "headline",
    "title": "headline",
    "text": "body",
    "figure_caption": "caption",
    "table_caption": "caption",
    "header": "byline",
    "footer": "other",
    "table": "body",
    "equation": "other",
    "reference": "other",
    "figure": None,  # image region → OWLv2
    "image": None,
    "seal": "other",
    "chart": "other",
    "header_image": None,
    "footer_image": None,
    "aside_text": "body",
    "number": "other",
    "footnote": "other",
    "abstract": "body",
    "paragraph_title": "subheadline",
}


class PPStructureBackend(OCRModel, LayoutModel):
    """Combined OCR + layout analysis using PaddleOCR PP-StructureV3.

    Implements both OCRModel and LayoutModel — a single call to extract()
    performs detection, recognition, and layout classification in one pass.
    The result of classify() returns the pre-computed classified blocks.
    """

    def __init__(self, lang: str = "en", use_gpu: bool = False):
        self.lang = lang
        self.use_gpu = use_gpu
        self._engine = None
        # Cache classified results after each extract() call
        self._last_classified: list[ClassifiedTextBlock] = []

    def load(self) -> None:
        logger.info(f"Loading PP-StructureV3 (lang={self.lang}, gpu={self.use_gpu})")
        from paddleocr import PPStructureV3

        self._engine = PPStructureV3(
            lang=self.lang,
            device="gpu" if self.use_gpu else "cpu",
        )
        logger.info("PP-StructureV3 loaded")

    def extract(self, image: np.ndarray) -> OCRResult:
        if self._engine is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        h, w = image.shape[:2]

        # v3 returns a generator — consume into list, one result per page
        results = list(self._engine.predict(image))
        if not results:
            logger.warning("PP-StructureV3 returned no results")
            self._last_classified = []
            return OCRResult(text_blocks=[], image_regions=[])

        # parsing_res_list contains the structured blocks
        page_data = results[0].json.get("res", {})
        blocks = page_data.get("parsing_res_list", [])

        # Also get layout_det_res for figure/image regions not in parsing_res_list
        layout_boxes = page_data.get("layout_det_res", {}).get("boxes", [])

        text_blocks: list[TextBlock] = []
        classified_blocks: list[ClassifiedTextBlock] = []
        image_regions: list[ImageRegion] = []
        tb_idx = 0
        ir_idx = 0

        # Process text/structure blocks from parsing_res_list
        for block in blocks:
            label = block.get("block_label", "text").lower()
            content = block.get("block_content", "").strip()
            raw_bbox = block.get("block_bbox", [0, 0, w, h])

            if not content:
                continue

            x1, y1, x2, y2 = raw_bbox
            norm_bbox = BBox(
                x_min=max(0.0, x1 / w),
                y_min=max(0.0, y1 / h),
                x_max=min(1.0, x2 / w),
                y_max=min(1.0, y2 / h),
            )

            mapped_type = _LAYOUT_TYPE_MAP.get(label, "other")

            # Figure in text blocks — crop for image analysis
            if mapped_type is None:
                crop = image[int(y1) : int(y2), int(x1) : int(x2)].copy()
                if crop.size > 0:
                    image_regions.append(
                        ImageRegion(id=f"ir_{ir_idx:03d}", bbox=norm_bbox, image=crop)
                    )
                    ir_idx += 1
                continue

            tb_id = f"tb_{tb_idx:03d}"
            text_blocks.append(
                TextBlock(id=tb_id, text=content, bbox=norm_bbox, confidence=1.0)
            )
            classified_blocks.append(
                ClassifiedTextBlock(
                    id=tb_id,
                    text=content,
                    bbox=norm_bbox,
                    block_type=mapped_type,
                    confidence=1.0,
                )
            )
            tb_idx += 1

        # Extract figure/image regions from layout detection (not in parsing list)
        for box in layout_boxes:
            label = box.get("label", "").lower()
            if _LAYOUT_TYPE_MAP.get(label) is None and label in _LAYOUT_TYPE_MAP:
                coords = box.get("coordinate", [0, 0, w, h])
                x1, y1, x2, y2 = coords
                norm_bbox = BBox(
                    x_min=max(0.0, x1 / w),
                    y_min=max(0.0, y1 / h),
                    x_max=min(1.0, x2 / w),
                    y_max=min(1.0, y2 / h),
                )
                crop = image[int(y1) : int(y2), int(x1) : int(x2)].copy()
                if crop.size > 0:
                    image_regions.append(
                        ImageRegion(id=f"ir_{ir_idx:03d}", bbox=norm_bbox, image=crop)
                    )
                    ir_idx += 1

        # Cache for classify() to return
        self._last_classified = classified_blocks

        logger.info(
            f"PP-StructureV3 extracted {len(text_blocks)} text block(s), "
            f"{len(image_regions)} image region(s)"
        )
        return OCRResult(text_blocks=text_blocks, image_regions=image_regions)

    def classify(
        self, text_blocks: list[TextBlock], image: np.ndarray
    ) -> list[ClassifiedTextBlock]:
        """Return pre-computed layout classifications from the last extract() call."""
        return self._last_classified

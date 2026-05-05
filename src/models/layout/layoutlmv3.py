from __future__ import annotations

import numpy as np
import torch
from loguru import logger
from PIL import Image
from transformers import AutoProcessor, AutoModelForTokenClassification

from src.device import best_torch_device, log_device_once
from src.models.base import (
    BBox,
    ClassifiedTextBlock,
    LayoutModel,
    TextBlock,
)

# LayoutLMv3 token classification label mapping.
# The default microsoft/layoutlmv3-base is a base model without a classification head,
# so we use a heuristic fallback when no fine-tuned model is available.
LABEL_MAP = {
    0: "other",
    1: "headline",
    2: "subheadline",
    3: "body",
    4: "caption",
    5: "byline",
    6: "advertisement_copy",
}


class LayoutLMv3Layout(LayoutModel):
    """Document layout classification using LayoutLMv3.

    If a fine-tuned token-classification model is provided, it uses that directly.
    Otherwise, falls back to a heuristic classifier based on bounding box geometry
    (size, position) which works reasonably well for newspaper/magazine layouts.
    """

    def __init__(self, model_name: str = "microsoft/layoutlmv3-base"):
        self.model_name = model_name
        self.processor = None
        self.model = None
        self._use_heuristic = False
        self.device = best_torch_device()

    def load(self) -> None:
        logger.info(f"Loading LayoutLMv3 model: {self.model_name}")
        log_device_once("LayoutLMv3", self.device)
        try:
            self.processor = AutoProcessor.from_pretrained(
                self.model_name, apply_ocr=False
            )
            self.model = AutoModelForTokenClassification.from_pretrained(
                self.model_name
            ).to(self.device)
            self.model.eval()
            logger.info("LayoutLMv3 token classification model loaded")
        except Exception:
            logger.warning(
                f"Could not load {self.model_name} as token classifier. "
                "Falling back to heuristic layout classification."
            )
            self._use_heuristic = True
            # Still load the processor for potential future use
            try:
                self.processor = AutoProcessor.from_pretrained(
                    self.model_name, apply_ocr=False
                )
            except Exception:
                pass

    def classify(
        self, text_blocks: list[TextBlock], image: np.ndarray
    ) -> list[ClassifiedTextBlock]:
        if not text_blocks:
            return []

        if self._use_heuristic:
            return self._classify_heuristic(text_blocks, image)

        return self._classify_model(text_blocks, image)

    def _classify_model(
        self, text_blocks: list[TextBlock], image: np.ndarray
    ) -> list[ClassifiedTextBlock]:
        """Classify using the LayoutLMv3 model."""
        pil_image = Image.fromarray(image)
        h, w = image.shape[:2]

        words = [tb.text for tb in text_blocks]
        # LayoutLMv3 expects boxes in [x_min, y_min, x_max, y_max] scaled to 1000
        boxes = [
            [
                int(tb.bbox.x_min * 1000),
                int(tb.bbox.y_min * 1000),
                int(tb.bbox.x_max * 1000),
                int(tb.bbox.y_max * 1000),
            ]
            for tb in text_blocks
        ]

        encoding = self.processor(
            pil_image,
            words,
            boxes=boxes,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        encoding_on_device = {k: v.to(self.device) for k, v in encoding.items()}

        with torch.no_grad():
            outputs = self.model(**encoding_on_device)

        logits = outputs.logits
        predictions = logits.argmax(-1).squeeze().tolist()
        if isinstance(predictions, int):
            predictions = [predictions]

        # Map predictions back to text blocks
        # The tokenizer may produce more tokens than text blocks; we take the
        # first prediction per word.
        results: list[ClassifiedTextBlock] = []
        word_ids = encoding.word_ids(batch_index=0)

        # Gather first prediction per word
        word_preds: dict[int, int] = {}
        for token_idx, word_id in enumerate(word_ids):
            if word_id is not None and word_id not in word_preds:
                if token_idx < len(predictions):
                    word_preds[word_id] = predictions[token_idx]

        for i, tb in enumerate(text_blocks):
            pred_id = word_preds.get(i, 0)
            block_type = LABEL_MAP.get(pred_id, "other")
            results.append(
                ClassifiedTextBlock(
                    id=tb.id,
                    text=tb.text,
                    bbox=tb.bbox,
                    block_type=block_type,
                    confidence=tb.confidence,
                )
            )

        logger.info(f"LayoutLMv3 classified {len(results)} text block(s)")
        return results

    def _classify_heuristic(
        self, text_blocks: list[TextBlock], image: np.ndarray
    ) -> list[ClassifiedTextBlock]:
        """Heuristic layout classification based on bbox geometry.

        Rules:
        - Large text near the top → headline
        - Medium text near top → subheadline
        - Small text near an image region (bottom of page) → caption
        - Small italic-like short text → byline
        - Everything else → body
        """
        results: list[ClassifiedTextBlock] = []

        # Compute stats for relative sizing
        heights = [tb.bbox.y_max - tb.bbox.y_min for tb in text_blocks]
        widths = [tb.bbox.x_max - tb.bbox.x_min for tb in text_blocks]
        if not heights:
            return []
        median_h = sorted(heights)[len(heights) // 2]
        median_w = sorted(widths)[len(widths) // 2]

        for tb in text_blocks:
            h = tb.bbox.y_max - tb.bbox.y_min
            w = tb.bbox.x_max - tb.bbox.x_min
            y_center = (tb.bbox.y_min + tb.bbox.y_max) / 2
            word_count = len(tb.text.split())

            if h > median_h * 1.8 and y_center < 0.3:
                block_type = "headline"
            elif h > median_h * 1.3 and y_center < 0.4:
                block_type = "subheadline"
            elif word_count <= 6 and y_center > 0.7:
                block_type = "caption"
            elif word_count <= 4 and (
                "by " in tb.text.lower() or "photo" in tb.text.lower()
            ):
                block_type = "byline"
            else:
                block_type = "body"

            results.append(
                ClassifiedTextBlock(
                    id=tb.id,
                    text=tb.text,
                    bbox=tb.bbox,
                    block_type=block_type,
                    confidence=tb.confidence,
                )
            )

        type_counts = {}
        for r in results:
            type_counts[r.block_type] = type_counts.get(r.block_type, 0) + 1
        logger.info(f"Heuristic classified {len(results)} block(s): {type_counts}")

        return results

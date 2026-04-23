from __future__ import annotations

import numpy as np
import torch
from loguru import logger
from PIL import Image
from transformers import Owlv2ForObjectDetection, Owlv2Processor

from src.models.base import (
    BBox,
    Detection,
    ImageAnalysisModel,
    ImageRegion,
    ImageRegionWithDetections,
)


class OWLv2ImageAnalysis(ImageAnalysisModel):
    """Zero-shot object detection using OWLv2."""

    def __init__(
        self,
        model_name: str = "google/owlv2-base-patch16-ensemble",
        confidence_threshold: float = 0.3,
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.processor = None
        self.model = None

    def load(self) -> None:
        logger.info(f"Loading OWLv2 model: {self.model_name}")
        self.processor = Owlv2Processor.from_pretrained(self.model_name)
        self.model = Owlv2ForObjectDetection.from_pretrained(self.model_name)
        self.model.eval()
        logger.info("OWLv2 model loaded")

    def detect(
        self, image_regions: list[ImageRegion], prompts: list[str]
    ) -> list[ImageRegionWithDetections]:
        if self.model is None or self.processor is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        if not prompts:
            logger.warning("No detection prompts provided, skipping image analysis")
            return [
                ImageRegionWithDetections(id=r.id, bbox=r.bbox) for r in image_regions
            ]

        results: list[ImageRegionWithDetections] = []
        total_detections = 0

        for region in image_regions:
            detections = self._detect_in_region(region, prompts)
            total_detections += len(detections)
            results.append(
                ImageRegionWithDetections(
                    id=region.id,
                    bbox=region.bbox,
                    detections=detections,
                )
            )

        logger.info(
            f"OWLv2 found {total_detections} detection(s) across "
            f"{len(image_regions)} image region(s)"
        )
        return results

    def _detect_in_region(
        self, region: ImageRegion, prompts: list[str]
    ) -> list[Detection]:
        """Run OWLv2 on a single image region."""
        pil_image = Image.fromarray(region.image)

        # OWLv2 expects a list of text queries
        texts = [prompts]

        inputs = self.processor(text=texts, images=pil_image, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)

        target_sizes = torch.tensor([pil_image.size[::-1]])  # (height, width)

        # Handle API difference across transformers versions
        post_process = getattr(
            self.processor,
            "post_process_object_detection",
            getattr(self.processor, "post_process_grounded_object_detection", None),
        )
        if post_process is None:
            raise RuntimeError(
                "OWLv2 processor has no post_process method. "
                "Check your transformers version."
            )
        results = post_process(
            outputs, target_sizes=target_sizes, threshold=self.confidence_threshold
        )

        detections: list[Detection] = []
        if results:
            result = results[0]
            boxes = result["boxes"]
            scores = result["scores"]
            labels = result["labels"]

            img_h, img_w = region.image.shape[:2]

            for box, score, label_idx in zip(boxes, scores, labels):
                x1, y1, x2, y2 = box.tolist()
                # Normalise bbox to 0-1 range relative to the crop
                bbox = BBox(
                    x_min=max(0.0, x1 / img_w),
                    y_min=max(0.0, y1 / img_h),
                    x_max=min(1.0, x2 / img_w),
                    y_max=min(1.0, y2 / img_h),
                )
                detections.append(
                    Detection(
                        label=prompts[label_idx.item()],
                        confidence=round(score.item(), 4),
                        bbox=bbox,
                    )
                )

        return detections

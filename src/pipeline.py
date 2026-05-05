from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger

from src.config import PipelineConfig
from src.input_handler import load_file_pages, resolve_inputs
from src.models.base import (
    DocumentResult,
    ImageAnalysisModel,
    ImageRegionWithDetections,
    LayoutModel,
    NERModel,
    OCRModel,
    PageResult,
)
from src.models.image_analysis.owlv2 import OWLv2ImageAnalysis
from src.models.layout.layoutlmv3 import LayoutLMv3Layout
from src.models.ner.spacy_ner import SpacyNER
from src.models.ocr.doctr_ocr import DocTROCR
from src.models.ocr.paddleocr_vl import PaddleOCRVLBackend
from src.models.ocr.ppstructure import PPStructureBackend
from src.output_handler import write_result

# Backends that handle both OCR and layout in a single pass — the same
# instance is shared between the OCR and layout stages.
COMBINED_OCR_LAYOUT_BACKENDS = {"ppstructure", "paddleocr_vl"}

# Registry of available model backends
OCR_BACKENDS: dict[str, type[OCRModel]] = {
    "doctr": DocTROCR,
    "ppstructure": PPStructureBackend,
    "paddleocr_vl": PaddleOCRVLBackend,
}
LAYOUT_BACKENDS: dict[str, type[LayoutModel]] = {
    "layoutlmv3": LayoutLMv3Layout,
    "ppstructure": PPStructureBackend,
    "paddleocr_vl": PaddleOCRVLBackend,
}
NER_BACKENDS: dict[str, type[NERModel]] = {
    "spacy": SpacyNER,
}
IMAGE_ANALYSIS_BACKENDS: dict[str, type[ImageAnalysisModel]] = {
    "owlv2": OWLv2ImageAnalysis,
}


def _create_ocr(config: PipelineConfig) -> OCRModel:
    cfg = config.models.get("ocr")
    if cfg is None:
        raise ValueError("No OCR model configured")
    cls = OCR_BACKENDS.get(cfg.backend)
    if cls is None:
        raise ValueError(
            f"Unknown OCR backend: {cfg.backend}. Available: {list(OCR_BACKENDS)}"
        )
    if cfg.backend == "doctr":
        return cls(
            det_arch=cfg.detection or "db_resnet50",
            reco_arch=cfg.recognition or "crnn_vgg16_bn",
        )
    if cfg.backend == "ppstructure":
        return cls(lang=cfg.model_name or "en")
    if cfg.backend == "paddleocr_vl":
        return cls(
            vl_rec_backend=cfg.vl_rec_backend,
            vl_rec_server_url=cfg.vl_rec_server_url,
            vl_rec_api_model_name=cfg.vl_rec_api_model_name,
        )
    return cls()


def _create_layout(config: PipelineConfig) -> LayoutModel:
    cfg = config.models.get("layout")
    if cfg is None:
        raise ValueError("No layout model configured")
    cls = LAYOUT_BACKENDS.get(cfg.backend)
    if cls is None:
        raise ValueError(
            f"Unknown layout backend: {cfg.backend}. Available: {list(LAYOUT_BACKENDS)}"
        )
    if cfg.backend == "layoutlmv3":
        return cls(model_name=cfg.model_name or "microsoft/layoutlmv3-base")
    return cls()


def _create_ner(config: PipelineConfig) -> NERModel:
    cfg = config.models.get("ner")
    if cfg is None:
        raise ValueError("No NER model configured")
    cls = NER_BACKENDS.get(cfg.backend)
    if cls is None:
        raise ValueError(
            f"Unknown NER backend: {cfg.backend}. Available: {list(NER_BACKENDS)}"
        )
    if cfg.backend == "spacy":
        return cls(
            model_name=cfg.model_name or "en_core_web_trf",
            label_remapping=config.label_remapping,
        )
    return cls()


def _create_image_analysis(config: PipelineConfig) -> ImageAnalysisModel:
    cfg = config.models.get("image_analysis")
    if cfg is None:
        raise ValueError("No image analysis model configured")
    cls = IMAGE_ANALYSIS_BACKENDS.get(cfg.backend)
    if cls is None:
        raise ValueError(
            f"Unknown image analysis backend: {cfg.backend}. "
            f"Available: {list(IMAGE_ANALYSIS_BACKENDS)}"
        )
    if cfg.backend == "owlv2":
        return cls(
            model_name=cfg.model_name or "google/owlv2-base-patch16-ensemble",
            confidence_threshold=cfg.confidence_threshold,
        )
    return cls()


class Pipeline:
    """Orchestrator that runs all pipeline stages in sequence."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        ocr_cfg = config.models.get("ocr")

        # Some backends handle both OCR and layout in a single pass —
        # share the same instance for both stages.
        if ocr_cfg and ocr_cfg.backend in COMBINED_OCR_LAYOUT_BACKENDS:
            shared = _create_ocr(config)
            self.ocr: OCRModel = shared
            self.layout: LayoutModel = shared  # type: ignore[assignment]
        else:
            self.ocr = _create_ocr(config)
            self.layout = _create_layout(config)

        self.ner: NERModel = _create_ner(config)
        self.image_analysis: ImageAnalysisModel = _create_image_analysis(config)
        self._combined_backend = (
            ocr_cfg and ocr_cfg.backend in COMBINED_OCR_LAYOUT_BACKENDS
        )

    def load_models(self) -> None:
        """Load all models. Call once before processing."""
        logger.info("Loading all pipeline models...")
        self.ocr.load()
        # Skip layout.load() when both share the same instance
        if not self._combined_backend:
            self.layout.load()
        self.ner.load()
        self.image_analysis.load()
        logger.info("All models loaded")

    def process_page(self, image: np.ndarray, page_number: int) -> PageResult:
        """Process a single page image through all stages."""
        logger.info(f"Processing page {page_number}")

        # Stage 1: OCR + page segmentation
        ocr_result = self.ocr.extract(image)

        # Stage 2a: Layout classification
        classified_blocks = self.layout.classify(ocr_result.text_blocks, image)

        # Stage 2b: NER
        blocks_with_entities = self.ner.extract_entities(classified_blocks)

        # Stage 3: Image analysis
        prompts = self.config.get_all_prompts_flat()
        try:
            image_detections = self.image_analysis.detect(
                ocr_result.image_regions, prompts
            )
        except Exception:
            logger.exception("Image analysis failed, continuing with text results only")
            image_detections = [
                ImageRegionWithDetections(id=r.id, bbox=r.bbox)
                for r in ocr_result.image_regions
            ]

        return PageResult(
            page_number=page_number,
            text_blocks=blocks_with_entities,
            image_regions=image_detections,
        )

    def process_file(self, file_path: Path) -> DocumentResult:
        """Process a single file (image or PDF) through the pipeline."""
        logger.info(f"Processing file: {file_path.name}")
        pages = load_file_pages(file_path)

        page_results: list[PageResult] = []
        errors: list[str] = []
        for i, page_image in enumerate(pages, start=1):
            try:
                result = self.process_page(page_image, page_number=i)
                page_results.append(result)
            except Exception as exc:
                msg = f"Page {i}: {type(exc).__name__}: {exc}"
                logger.exception(f"Failed to process page {i} of {file_path.name}")
                errors.append(msg)
                continue

        return DocumentResult(
            input_file=file_path.name,
            pages=page_results,
            errors=errors,
        )

    def run(self, input_path: str | Path) -> list[Path]:
        """Run the full pipeline on an input path (file or folder).

        Returns a list of output file paths.
        """
        files = resolve_inputs(input_path)
        if not files:
            logger.warning("No files to process")
            return []

        logger.info(f"Pipeline starting — {len(files)} file(s) to process")
        self.load_models()

        output_paths: list[Path] = []
        for file_path in files:
            try:
                doc_result = self.process_file(file_path)
                output_path = write_result(doc_result, self.config, file_path.name)
                output_paths.append(output_path)
                self._move_to_processed(file_path)
            except Exception:
                logger.exception(f"Failed to process {file_path.name}, skipping")
                continue

        logger.info(
            f"Pipeline complete — {len(output_paths)}/{len(files)} file(s) processed"
        )
        return output_paths

    def _move_to_processed(self, file_path: Path) -> None:
        """Move a successfully processed file to the 'processed' subfolder."""
        processed_dir = file_path.parent.parent / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        dest = processed_dir / file_path.name
        file_path.rename(dest)
        logger.info(f"Moved {file_path.name} → processed/")

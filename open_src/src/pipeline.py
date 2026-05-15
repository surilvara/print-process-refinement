from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from loguru import logger

from src.config import PipelineConfig
from src.input_handler import InputItem, load_file_pages, resolve_inputs
from src.models.base import (
    BBox,
    ClassifiedTextBlock,
    DocumentResult,
    ImageAnalysisModel,
    ImageRegion,
    ImageRegionWithDetections,
    LayoutModel,
    NERModel,
    OCRModel,
    PageResult,
    TextBlock,
)
from src.models.image_analysis.owlv2 import OWLv2ImageAnalysis
from src.models.layout.layoutlmv3 import LayoutLMv3Layout
from src.models.ner.dmr_alias_matcher import DMRAliasMatcher
from src.models.ner.spacy_ner import SpacyNER
from src.models.ocr.doctr_ocr import DocTROCR
from src.models.ocr.paddleocr_vl import PaddleOCRVLBackend
from src.models.ocr.ppstructure import PPStructureBackend
from src.output_handler import write_result
from src.publication import (
    PublicationMetadataExtractor,
    create_publication_extractor,
)

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
    "dmr_alias_matcher": DMRAliasMatcher,
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
    if cfg.backend == "dmr_alias_matcher":
        if not cfg.dmr_db_path:
            raise ValueError(
                "models.ner.dmr_db_path is required when backend is dmr_alias_matcher"
            )
        base_ner: NERModel | None = None
        if cfg.base_ner_backend:
            base_cls = NER_BACKENDS.get(cfg.base_ner_backend)
            if base_cls is None:
                raise ValueError(f"Unknown base_ner_backend: {cfg.base_ner_backend}")
            if cfg.base_ner_backend == "spacy":
                base_ner = base_cls(
                    model_name=cfg.base_ner_model_name or "en_core_web_trf",
                    label_remapping=config.label_remapping,
                )
            elif cfg.base_ner_backend == "dmr_alias_matcher":
                raise ValueError("base_ner_backend cannot be dmr_alias_matcher")
            else:
                base_ner = base_cls()
        return cls(
            db_path=cfg.dmr_db_path,
            base_ner=base_ner,
            min_alias_length=cfg.min_alias_length,
            alias_stopwords=(
                frozenset(s.lower() for s in cfg.alias_stopwords)
                if cfg.alias_stopwords
                else None
            ),
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
        self.publication_extractor: PublicationMetadataExtractor = (
            create_publication_extractor(config.publication_extraction.backend)
        )
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

    # ── OCR-from-disk pathway ──
    #
    # Skips Stage 1 (OCR + layout segmentation) entirely. Reads OCR output
    # produced by an ocr_eval runner and feeds the rest of the pipeline (NER,
    # DMR matcher, OWLv2) from it. Useful for:
    #   - Iterating on downstream stages without re-paying OCR cost.
    #   - Swapping OCR engines without writing a new backend inside open_src.
    #   - Feeding Google Vision (or any frozen baseline) into the pipeline.
    #
    # The OCR runner's `block_type` is treated as authoritative; the layout
    # backend is not invoked. OWLv2 crops are loaded from the runner's
    # `source_image_path` so the original image must still exist on disk.

    def process_ocr_json(self, ocr_json_path: Path, page_number: int = 1) -> PageResult:
        """Process a single OcrOutput JSON file as one page."""
        ocr_output = _load_ocr_output(ocr_json_path)
        logger.info(
            f"Processing OCR JSON: {ocr_json_path.name} "
            f"({len(ocr_output.blocks)} blocks, "
            f"{len(ocr_output.image_regions)} image regions, "
            f"runner={ocr_output.runner})"
        )

        classified_blocks = _classified_blocks_from_ocr(ocr_output)

        # Stage 2b: NER
        blocks_with_entities = self.ner.extract_entities(classified_blocks)

        # Stage 3: Image analysis (best-effort)
        image_regions = _image_regions_from_ocr(ocr_output)
        prompts = self.config.get_all_prompts_flat()
        try:
            image_detections = self.image_analysis.detect(image_regions, prompts)
        except Exception:
            logger.exception("Image analysis failed, continuing with text results only")
            image_detections = [
                ImageRegionWithDetections(id=r.id, bbox=r.bbox) for r in image_regions
            ]

        return PageResult(
            page_number=page_number,
            text_blocks=blocks_with_entities,
            image_regions=image_detections,
        )

    def process_ocr_file(self, ocr_json_path: Path) -> DocumentResult:
        """Wrap a single OCR JSON file as a one-page DocumentResult."""
        errors: list[str] = []
        page_results: list[PageResult] = []
        try:
            page_results.append(self.process_ocr_json(ocr_json_path, page_number=1))
        except Exception as exc:
            msg = f"OCR JSON {ocr_json_path.name}: {type(exc).__name__}: {exc}"
            logger.exception(f"Failed to process OCR JSON {ocr_json_path.name}")
            errors.append(msg)

        ocr_output = _load_ocr_output(ocr_json_path)
        # Name the result after the original image, not the OCR JSON, so
        # downstream filenames stay consistent with the standard pipeline.
        input_name = (
            Path(ocr_output.source_image_path).name
            if ocr_output.source_image_path
            else ocr_json_path.with_suffix(".jpg").name
        )
        return DocumentResult(
            input_file=input_name,
            pages=page_results,
            errors=errors,
        )

    def load_downstream_models(self) -> None:
        """Load only the models needed by the OCR-from-disk pathway.

        Skips OCR + layout backends to keep startup cheap.
        """
        logger.info("Loading downstream models (NER + image analysis)...")
        self.ner.load()
        self.image_analysis.load()
        logger.info("Downstream models loaded")

    def run_from_ocr(self, ocr_path: str | Path) -> list[Path]:
        """Run the downstream pipeline against pre-computed OCR JSON.

        `ocr_path` is either a single JSON file or a folder of JSON files
        (one file per image, output of an ocr_eval runner). When `ocr_path`
        is a folder, its basename is treated as the publication identity
        (same convention as the `--input` path) and the publication
        extractor parses magazine/issue date from the name. Returns the
        list of output JSON paths written by the pipeline.
        """
        ocr_path = Path(ocr_path)
        json_files = _resolve_ocr_json_paths(ocr_path)
        if not json_files:
            logger.warning("No OCR JSON files to process")
            return []

        # Build per-file publication metadata. For a folder input, the
        # folder name carries the publication identity and each JSON becomes
        # a page labelled "1", "2", ... in sort order.
        page_meta: dict[Path, dict | None] = {}
        if ocr_path.is_dir():
            meta = self.publication_extractor.extract(ocr_path)
            publication_base = {
                "name": ocr_path.name,
                "magazine_name": meta.magazine_name,
                "issue_date": meta.issue_date,
                "source_path": str(ocr_path.resolve()),
                "total_pages": len(json_files),
            }
            for i, jf in enumerate(json_files, start=1):
                page_meta[jf] = {**publication_base, "page_label": str(i)}
            logger.info(
                f"Treating {ocr_path.name} as publication "
                f"(magazine={meta.magazine_name!r}, issue_date={meta.issue_date})"
            )
        else:
            page_meta[json_files[0]] = None

        logger.info(
            f"OCR-from-disk pipeline starting — {len(json_files)} file(s) to process"
        )
        self.load_downstream_models()

        run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        output_paths: list[Path] = []
        for json_path in json_files:
            try:
                doc_result = self.process_ocr_file(json_path)
                output_path = write_result(
                    doc_result,
                    self.config,
                    doc_result.input_file,
                    publication_meta=page_meta.get(json_path),
                    run_timestamp=run_timestamp,
                )
                output_paths.append(output_path)
            except Exception:
                logger.exception(
                    f"Failed to process OCR JSON {json_path.name}, skipping"
                )
                continue

        logger.info(
            f"OCR-from-disk pipeline complete — "
            f"{len(output_paths)}/{len(json_files)} file(s) processed"
        )
        return output_paths

    def run(self, input_path: str | Path) -> list[Path]:
        """Run the full pipeline on an input path (file or folder).

        Returns a list of output file paths.
        """
        input_path = Path(input_path)
        items = resolve_inputs(input_path, extractor=self.publication_extractor)
        if not items:
            logger.warning("No files to process")
            return []

        logger.info(f"Pipeline starting — {len(items)} item(s) to process")
        self.load_models()

        # Single timestamp shared across every output of this run, so all pages
        # of a publication land in the same <name>_<timestamp>/ subdirectory.
        run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

        output_paths: list[Path] = []
        for item in items:
            try:
                doc_result = self.process_file(item.path)
                publication_meta = self._publication_meta(item)
                output_path = write_result(
                    doc_result,
                    self.config,
                    item.path.name,
                    publication_meta=publication_meta,
                    run_timestamp=run_timestamp,
                )
                output_paths.append(output_path)
            except Exception:
                logger.exception(f"Failed to process {item.path.name}, skipping")
                continue

        logger.info(
            f"Pipeline complete — {len(output_paths)}/{len(items)} item(s) processed"
        )
        return output_paths

    @staticmethod
    def _publication_meta(item: InputItem) -> dict | None:
        if item.publication is None:
            return None
        return {
            "name": item.publication.name,
            "magazine_name": item.publication.magazine_name,
            "issue_date": item.publication.issue_date,
            "source_path": item.publication.source_path,
            "page_label": item.page_label,
            "total_pages": item.total_pages_in_publication,
        }


# ── Module-level helpers for the OCR-from-disk pathway ──
#
# These translate the ocr_eval schema (OcrOutput / OcrBlock / ImageRegion)
# into the pipeline's internal types (ClassifiedTextBlock / ImageRegion).
# Import is lazy so we don't pull in ocr_eval at module-load time when
# running the standard --input path.

# Block types the pipeline downstream understands. Anything outside this
# set is normalised to "body" (a safe default for NER and DMR matching).
_KNOWN_BLOCK_TYPES = frozenset(
    {
        "headline",
        "subheadline",
        "body",
        "caption",
        "byline",
        "advertisement_copy",
        "other",
    }
)


def _import_ocr_eval():
    """Import the ocr_eval schema lazily, adding it to sys.path if needed."""
    try:
        from ocr_eval.schema import OcrOutput as _OcrOutput  # noqa: F401
    except ImportError:
        # pipeline.py is at open_src/src/pipeline.py, so the workspace root
        # (which contains ocr_eval/) is parents[2].
        workspace_root = Path(__file__).resolve().parents[2]
        if str(workspace_root) not in sys.path:
            sys.path.insert(0, str(workspace_root))
    from ocr_eval.schema import OcrOutput  # type: ignore[import-not-found]

    return OcrOutput


def _load_ocr_output(path: Path):
    OcrOutput = _import_ocr_eval()
    return OcrOutput.load(path)


def _classified_blocks_from_ocr(ocr_output) -> list[ClassifiedTextBlock]:
    """Translate OcrOutput.blocks → ClassifiedTextBlock list.

    The runner's `block_type` is preserved when recognised; otherwise we
    default to "body" so NER/DMR matching still sees the text.
    """
    classified: list[ClassifiedTextBlock] = []
    for i, b in enumerate(ocr_output.blocks):
        block_type = b.block_type if b.block_type in _KNOWN_BLOCK_TYPES else "body"
        classified.append(
            ClassifiedTextBlock(
                id=f"tb_{i:03d}",
                text=b.text,
                bbox=BBox(
                    x_min=b.bbox.x_min,
                    y_min=b.bbox.y_min,
                    x_max=b.bbox.x_max,
                    y_max=b.bbox.y_max,
                ),
                block_type=block_type,
                confidence=b.confidence,
            )
        )
    return classified


def _image_regions_from_ocr(ocr_output) -> list[ImageRegion]:
    """Translate OcrOutput.image_regions → ImageRegion list with crops.

    Re-opens `source_image_path` and crops by normalised bbox. Skips regions
    whose source image can't be loaded; OWLv2 simply sees fewer regions.
    """
    if not ocr_output.image_regions:
        return []

    src = ocr_output.source_image_path
    if not src:
        logger.warning(
            "OCR output has image_regions but no source_image_path; "
            "skipping image analysis stage"
        )
        return []

    src_path = Path(src)
    if not src_path.is_file():
        logger.warning(
            f"source_image_path not found ({src_path}); "
            "skipping image analysis stage"
        )
        return []

    try:
        from PIL import Image as _PILImage

        with _PILImage.open(src_path) as im:
            rgb = np.array(im.convert("RGB"))
    except Exception:
        logger.exception(f"Failed to load source image {src_path}")
        return []

    h, w = rgb.shape[:2]
    regions: list[ImageRegion] = []
    for i, r in enumerate(ocr_output.image_regions):
        x1 = max(0, int(r.bbox.x_min * w))
        y1 = max(0, int(r.bbox.y_min * h))
        x2 = min(w, int(r.bbox.x_max * w))
        y2 = min(h, int(r.bbox.y_max * h))
        if x2 <= x1 or y2 <= y1:
            continue
        crop = rgb[y1:y2, x1:x2].copy()
        if crop.size == 0:
            continue
        regions.append(
            ImageRegion(
                id=f"ir_{i:03d}",
                bbox=BBox(
                    x_min=r.bbox.x_min,
                    y_min=r.bbox.y_min,
                    x_max=r.bbox.x_max,
                    y_max=r.bbox.y_max,
                ),
                image=crop,
            )
        )
    return regions


def _resolve_ocr_json_paths(path: Path) -> list[Path]:
    """Accept a single .json file or a folder of .json files."""
    if path.is_file():
        if path.suffix.lower() != ".json":
            raise ValueError(f"Expected a .json file: {path}")
        return [path]
    if path.is_dir():
        return sorted(p for p in path.glob("*.json") if p.is_file())
    raise FileNotFoundError(f"OCR path does not exist: {path}")

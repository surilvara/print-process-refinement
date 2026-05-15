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

# Map PaddleOCR-VL block_label values to our schema.
# PaddleOCR-VL emits the same label vocabulary as PP-StructureV3.
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


class PaddleOCRVLBackend(OCRModel, LayoutModel):
    """Combined OCR + layout analysis using PaddleOCR-VL.

    PaddleOCR-VL is a 0.9B vision-language model that performs OCR, layout
    detection, and structure parsing end-to-end. Output schema mirrors
    PP-StructureV3 (parsing_res_list with block_label / block_content /
    block_bbox), so the same downstream parsing applies.
    """

    def __init__(
        self,
        use_gpu: bool = False,
        engine: str = "paddle",
        vl_rec_backend: str | None = None,
        vl_rec_server_url: str | None = None,
        vl_rec_api_model_name: str | None = None,
    ):
        self.use_gpu = use_gpu
        self.engine = engine
        # Optional remote VL backend (e.g. an MLX-VLM server on Apple Silicon).
        # When set, the VLM recognition stage is offloaded to that server while
        # layout detection still runs locally via PaddlePaddle.
        self.vl_rec_backend = vl_rec_backend
        self.vl_rec_server_url = vl_rec_server_url
        self.vl_rec_api_model_name = vl_rec_api_model_name
        self._engine = None
        # Cache classified results after each extract() call so classify() can
        # return them without re-running the model.
        self._last_classified: list[ClassifiedTextBlock] = []

    def load(self) -> None:
        logger.info(
            f"Loading PaddleOCR-VL (gpu={self.use_gpu}, engine={self.engine}, "
            f"vl_rec_backend={self.vl_rec_backend or 'local'})"
        )
        if self.vl_rec_backend and self.vl_rec_server_url:
            self._probe_remote_backend()
        from paddleocr import PaddleOCRVL

        kwargs: dict = {
            "device": "gpu" if self.use_gpu else "cpu",
            "engine": self.engine,
        }
        if self.vl_rec_backend:
            kwargs["vl_rec_backend"] = self.vl_rec_backend
        if self.vl_rec_server_url:
            kwargs["vl_rec_server_url"] = self.vl_rec_server_url
        if self.vl_rec_api_model_name:
            kwargs["vl_rec_api_model_name"] = self.vl_rec_api_model_name

        self._engine = PaddleOCRVL(**kwargs)
        logger.info("PaddleOCR-VL loaded")

    def _probe_remote_backend(self) -> None:
        """Verify the remote VL server is reachable and serving the expected model.

        Fail loudly here rather than letting PaddleOCR silently fall back to local
        CPU inference when the server is down or misconfigured (wrong URL/model).
        """
        import urllib.error
        import urllib.request
        import json as _json

        base = (self.vl_rec_server_url or "").rstrip("/")
        # MLX-VLM exposes /health and /v1/models; OpenAI-compatible servers expose
        # /v1/models. Accept either by trying /v1/models against the base.
        models_url = base + ("/models" if base.endswith("/v1") else "/v1/models")
        try:
            with urllib.request.urlopen(models_url, timeout=3) as resp:
                payload = _json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise RuntimeError(
                f"VL recognition server unreachable at {models_url} ({exc}). "
                f"Start it with scripts/start_mlx_server.sh or remove "
                f"vl_rec_backend from config.yaml to use local CPU inference."
            ) from exc

        served = {m.get("id") for m in payload.get("data", []) if isinstance(m, dict)}
        if self.vl_rec_api_model_name and self.vl_rec_api_model_name not in served:
            logger.warning(
                f"VL server at {base} does not advertise model "
                f"{self.vl_rec_api_model_name!r}; advertised: {sorted(served)}. "
                "MLX may unload/reload, costing minutes per run."
            )
        else:
            logger.info(
                f"VL recognition server reachable at {base} "
                f"(model={self.vl_rec_api_model_name or 'unspecified'})"
            )

    def extract(self, image: np.ndarray) -> OCRResult:
        if self._engine is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        h, w = image.shape[:2]

        results = list(self._engine.predict(image))
        if not results:
            logger.warning("PaddleOCR-VL returned no results")
            self._last_classified = []
            return OCRResult(text_blocks=[], image_regions=[])

        raw = results[0].json
        page_data = raw.get("res", raw)
        blocks = page_data.get("parsing_res_list", [])
        layout_boxes = page_data.get("layout_det_res", {}).get("boxes", [])

        text_blocks: list[TextBlock] = []
        classified_blocks: list[ClassifiedTextBlock] = []
        image_regions: list[ImageRegion] = []
        tb_idx = 0
        ir_idx = 0

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

        self._last_classified = classified_blocks

        logger.info(
            f"PaddleOCR-VL extracted {len(text_blocks)} text block(s), "
            f"{len(image_regions)} image region(s)"
        )
        return OCRResult(text_blocks=text_blocks, image_regions=image_regions)

    def classify(
        self, text_blocks: list[TextBlock], image: np.ndarray
    ) -> list[ClassifiedTextBlock]:
        """Return pre-computed layout classifications from the last extract() call."""
        return self._last_classified

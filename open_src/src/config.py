from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ModelConfig:
    backend: str
    model_name: str | None = None
    detection: str | None = None
    recognition: str | None = None
    confidence_threshold: float = 0.3
    # PaddleOCR-VL remote VL backend (e.g. MLX-VLM server on Apple Silicon)
    vl_rec_backend: str | None = None
    vl_rec_server_url: str | None = None
    vl_rec_api_model_name: str | None = None
    # DMR alias matcher: path to the SQLite database produced by
    # `scripts/import_dmr_brands.py`. Only consulted when backend == "dmr_alias_matcher".
    dmr_db_path: str | None = None
    # Minimum normalised alias length to index (default 3). Filters single-
    # letter "brand" rows like "A", "I".
    min_alias_length: int = 3
    # Extra normalised forms to exclude from indexing (DMR ships canonical
    # rows whose name is a common English word). Empty = use matcher default.
    alias_stopwords: list[str] = field(default_factory=list)
    # When the DMR matcher is the NER backend, also run an underlying NER model
    # (typically spaCy) for PERSON/GPE/etc. and merge results — DMR spans win on overlap.
    base_ner_backend: str | None = None
    base_ner_model_name: str | None = None


@dataclass
class OutputConfig:
    directory: str = "output"
    include_timestamp: bool = True
    include_model_names: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/pipeline.log"


@dataclass
class DatabaseConfig:
    enabled: bool = True
    path: str = "database/results.db"


@dataclass
class PublicationExtractionConfig:
    """Backend that derives (magazine_name, issue_date) from a publication folder."""

    backend: str = "folder_name_regex"


@dataclass
class PageClassificationConfig:
    """Thresholds for the heuristic that labels a page editorial vs advertising."""

    advertisement_block_ratio: float = 0.5
    advertisement_detection_confidence: float = 0.5
    advertisement_detection_labels: list[str] = field(
        default_factory=lambda: ["advertisement", "product advertisement"]
    )
    # Primary PR/advertorial label keywords (any match → advertorial unless
    # overridden by the Japan/Korea structural rule).  Case-insensitive substring
    # match against each text block's full text.
    pr_keywords: list[str] = field(
        default_factory=lambda: [
            "advertorial",
            "advertising feature",
            "advertising section",
            "sponsored by",
            "sponsored content",
            "presented by",
            "in collaboration with",
            "promotion",
            "publicité",
            "messaggio promozionale",
            "informazione pubblicitaria",
            "publiredazionale",
            # Chinese equivalents
            "廣編特輯",
            "特約專輯",
            "全頁廣告",
            "商稿",
            "專刊",
            "廣編特企",
        ]
    )
    # Substrings matched (case-insensitive) against the publication's magazine_name
    # or folder name to identify Japan/Korea publications. For these publishers,
    # "Sponsored" / "In Collaboration With" labels alone do not trigger PR
    # classification — the page must also lack editorial structure (byline block)
    # before being called advertorial.
    japan_korea_publisher_keywords: list[str] = field(
        default_factory=lambda: [
            "japan",
            "korea",
            "japanese",
            "korean",
            "japon",
            "giappone",
        ]
    )


@dataclass
class PipelineConfig:
    models: dict[str, ModelConfig] = field(default_factory=dict)
    detection_prompts: dict[str, list[str]] = field(default_factory=dict)
    label_remapping: dict[str, str] = field(default_factory=dict)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    publication_extraction: PublicationExtractionConfig = field(
        default_factory=PublicationExtractionConfig
    )
    page_classification: PageClassificationConfig = field(
        default_factory=PageClassificationConfig
    )

    @staticmethod
    def from_yaml(path: str | Path) -> PipelineConfig:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path) as f:
            raw = yaml.safe_load(f)
        return PipelineConfig._parse(raw)

    @staticmethod
    def _parse(raw: dict[str, Any]) -> PipelineConfig:
        models = {}
        for stage, cfg in raw.get("models", {}).items():
            models[stage] = ModelConfig(
                backend=cfg.get("backend", ""),
                model_name=cfg.get("model_name"),
                detection=cfg.get("detection"),
                recognition=cfg.get("recognition"),
                confidence_threshold=cfg.get("confidence_threshold", 0.3),
                vl_rec_backend=cfg.get("vl_rec_backend"),
                vl_rec_server_url=cfg.get("vl_rec_server_url"),
                vl_rec_api_model_name=cfg.get("vl_rec_api_model_name"),
                dmr_db_path=cfg.get("dmr_db_path"),
                base_ner_backend=cfg.get("base_ner_backend"),
                base_ner_model_name=cfg.get("base_ner_model_name"),
                min_alias_length=cfg.get("min_alias_length", 3),
                alias_stopwords=list(cfg.get("alias_stopwords", [])),
            )

        detection_prompts: dict[str, list[str]] = {}
        for category, prompts in raw.get("detection_prompts", {}).items():
            detection_prompts[category] = list(prompts)

        label_remapping: dict[str, str] = dict(raw.get("label_remapping", {}))

        output_raw = raw.get("output", {})
        output = OutputConfig(
            directory=output_raw.get("directory", "output"),
            include_timestamp=output_raw.get("include_timestamp", True),
            include_model_names=output_raw.get("include_model_names", True),
        )

        logging_raw = raw.get("logging", {})
        logging_cfg = LoggingConfig(
            level=logging_raw.get("level", "INFO"),
            file=logging_raw.get("file", "logs/pipeline.log"),
        )

        database_raw = raw.get("database", {})
        database = DatabaseConfig(
            enabled=database_raw.get("enabled", True),
            path=database_raw.get("path", "database/results.db"),
        )

        pub_extract_raw = raw.get("publication_extraction", {})
        publication_extraction = PublicationExtractionConfig(
            backend=pub_extract_raw.get("backend", "folder_name_regex"),
        )

        page_class_raw = raw.get("page_classification", {})
        _default_pr_kw = PageClassificationConfig.__dataclass_fields__[
            "pr_keywords"
        ].default_factory()  # type: ignore[misc]
        _default_jk_kw = PageClassificationConfig.__dataclass_fields__[
            "japan_korea_publisher_keywords"
        ].default_factory()  # type: ignore[misc]
        page_classification = PageClassificationConfig(
            advertisement_block_ratio=page_class_raw.get(
                "advertisement_block_ratio", 0.5
            ),
            advertisement_detection_confidence=page_class_raw.get(
                "advertisement_detection_confidence", 0.5
            ),
            advertisement_detection_labels=list(
                page_class_raw.get(
                    "advertisement_detection_labels",
                    ["advertisement", "product advertisement"],
                )
            ),
            pr_keywords=list(page_class_raw.get("pr_keywords", _default_pr_kw)),
            japan_korea_publisher_keywords=list(
                page_class_raw.get("japan_korea_publisher_keywords", _default_jk_kw)
            ),
        )

        return PipelineConfig(
            models=models,
            detection_prompts=detection_prompts,
            label_remapping=label_remapping,
            output=output,
            logging=logging_cfg,
            database=database,
            publication_extraction=publication_extraction,
            page_classification=page_classification,
        )

    def apply_cli_overrides(self, **kwargs: Any) -> None:
        """Apply CLI argument overrides on top of config file values."""
        if kwargs.get("output"):
            self.output.directory = kwargs["output"]
        if kwargs.get("log_level"):
            self.logging.level = kwargs["log_level"]
        if kwargs.get("ocr_model"):
            if "ocr" in self.models:
                self.models["ocr"].backend = kwargs["ocr_model"]
        if kwargs.get("layout_model"):
            if "layout" in self.models:
                self.models["layout"].model_name = kwargs["layout_model"]
        if kwargs.get("ner_model"):
            if "ner" in self.models:
                self.models["ner"].model_name = kwargs["ner_model"]
        if kwargs.get("image_model"):
            if "image_analysis" in self.models:
                self.models["image_analysis"].model_name = kwargs["image_model"]

    def get_all_prompts_flat(self) -> list[str]:
        """Return all detection prompts as a flat list."""
        prompts = []
        for category_prompts in self.detection_prompts.values():
            prompts.extend(category_prompts)
        return prompts

    def get_model_summary(self) -> dict[str, str]:
        """Return a dict summarising which models are active."""
        summary = {}
        for stage, cfg in self.models.items():
            if cfg.model_name:
                summary[stage] = f"{cfg.backend}:{cfg.model_name}"
            elif cfg.detection and cfg.recognition:
                summary[stage] = f"{cfg.backend}:{cfg.detection}+{cfg.recognition}"
            else:
                summary[stage] = cfg.backend
        return summary

    def get_model_name_slug(self) -> str:
        """Return a short slug of model names for output filenames."""
        parts = []
        for cfg in self.models.values():
            parts.append(cfg.backend)
        return "_".join(parts)

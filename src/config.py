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
class PipelineConfig:
    models: dict[str, ModelConfig] = field(default_factory=dict)
    detection_prompts: dict[str, list[str]] = field(default_factory=dict)
    label_remapping: dict[str, str] = field(default_factory=dict)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

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

        return PipelineConfig(
            models=models,
            detection_prompts=detection_prompts,
            label_remapping=label_remapping,
            output=output,
            logging=logging_cfg,
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

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from loguru import logger

from src.config import PipelineConfig
from src.pipeline import Pipeline


def setup_logging(config: PipelineConfig) -> None:
    """Configure Loguru with the settings from the pipeline config."""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=config.logging.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> — <level>{message}</level>",
    )
    # Also log to file
    log_path = Path(config.logging.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_path),
        level="DEBUG",  # Always capture full debug to file
        rotation="10 MB",
        retention="7 days",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print Document Intelligence Pipeline — extract structured information from scanned pages",
    )
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument(
        "--input",
        "-i",
        help="Path to an image file, PDF, or folder of scans (full pipeline including OCR)",
    )
    src_group.add_argument(
        "--from-ocr",
        dest="from_ocr",
        help=(
            "Path to an ocr_eval OcrOutput JSON file or folder. "
            "Skips the OCR + layout stages and runs NER + image analysis only."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output directory (overrides config)",
    )
    parser.add_argument(
        "--config",
        "-c",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (overrides config)",
    )
    parser.add_argument(
        "--ocr-model",
        default=None,
        help="Override OCR backend name",
    )
    parser.add_argument(
        "--layout-model",
        default=None,
        help="Override layout model name",
    )
    parser.add_argument(
        "--ner-model",
        default=None,
        help="Override NER model name",
    )
    parser.add_argument(
        "--image-model",
        default=None,
        help="Override image analysis model name",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Anchor all relative paths (config.yaml, output/, database/, logs/,
    # dmr_db_path) to the directory containing this script, so the pipeline
    # behaves identically whether invoked via `cd open_src && python main.py`,
    # the installed `pipeline` entrypoint from the project root, or any other
    # cwd. User-supplied --input / --output / --config paths are resolved to
    # absolute paths first so they remain anchored to the caller's cwd.
    script_dir = Path(__file__).resolve().parent
    if args.input:
        args.input = str(Path(args.input).expanduser().resolve())
    if args.from_ocr:
        args.from_ocr = str(Path(args.from_ocr).expanduser().resolve())
    if args.output:
        args.output = str(Path(args.output).expanduser().resolve())
    args.config = str(
        (
            Path(args.config).expanduser().resolve()
            if Path(args.config).is_absolute() or Path(args.config).exists()
            else script_dir / args.config
        )
    )
    os.chdir(script_dir)

    # Load config
    config = PipelineConfig.from_yaml(args.config)
    config.apply_cli_overrides(
        output=args.output,
        log_level=args.log_level,
        ocr_model=args.ocr_model,
        layout_model=args.layout_model,
        ner_model=args.ner_model,
        image_model=args.image_model,
    )

    setup_logging(config)
    logger.info("Pipeline configuration loaded")
    logger.debug(f"Models: {config.get_model_summary()}")

    # Run pipeline
    pipeline = Pipeline(config)
    if args.from_ocr:
        output_paths = pipeline.run_from_ocr(args.from_ocr)
    else:
        output_paths = pipeline.run(args.input)

    if output_paths:
        logger.info(f"Done! {len(output_paths)} result(s) written:")
        for p in output_paths:
            logger.info(f"  → {p}")
    else:
        logger.warning("No results produced")


if __name__ == "__main__":
    main()

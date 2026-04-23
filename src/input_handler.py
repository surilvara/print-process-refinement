from __future__ import annotations

from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from loguru import logger
from PIL import Image

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_PDF_EXTENSIONS


def load_image(path: Path) -> np.ndarray:
    """Load an image file and return as a numpy RGB array."""
    img = Image.open(path).convert("RGB")
    return np.array(img)


def load_pdf_pages(path: Path, dpi: int = 300) -> list[np.ndarray]:
    """Convert each page of a PDF to a numpy RGB array."""
    pdf = pdfium.PdfDocument(path)
    pages = []
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=dpi / 72)
        pil_image = bitmap.to_pil().convert("RGB")
        pages.append(np.array(pil_image))
    return pages


def resolve_inputs(input_path: str | Path) -> list[Path]:
    """Resolve an input path to a list of supported files.

    Accepts a single file path or a directory. For directories, finds all
    supported files (non-recursive).
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {path.suffix}. "
                f"Supported: {SUPPORTED_EXTENSIONS}"
            )
        return [path]

    if path.is_dir():
        files = sorted(
            f
            for f in path.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if not files:
            logger.warning(f"No supported files found in {path}")
        else:
            logger.info(f"Found {len(files)} supported file(s) in {path}")
        return files

    raise ValueError(f"Input path is neither a file nor a directory: {path}")


def load_file_pages(path: Path) -> list[np.ndarray]:
    """Load a file and return a list of page images (numpy RGB arrays).

    For image files, returns a single-element list.
    For PDFs, returns one array per page.
    """
    suffix = path.suffix.lower()
    if suffix in SUPPORTED_IMAGE_EXTENSIONS:
        logger.info(f"Loading image: {path.name}")
        return [load_image(path)]
    elif suffix in SUPPORTED_PDF_EXTENSIONS:
        logger.info(f"Loading PDF: {path.name}")
        pages = load_pdf_pages(path)
        logger.info(f"  → {len(pages)} page(s) extracted")
        return pages
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

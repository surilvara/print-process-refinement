from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from loguru import logger
from PIL import Image

from src.publication import (
    FolderNameRegexExtractor,
    PublicationMetadataExtractor,
)

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_PDF_EXTENSIONS


@dataclass(frozen=True)
class PublicationInfo:
    """Identity + extracted metadata for a publication (folder of pages)."""

    name: str  # folder basename — UNIQUE identity in publications table
    source_path: str  # absolute path to the publication folder
    magazine_name: str  # from extractor; falls back to `name` on extraction failure
    issue_date: str | None  # from extractor (YYYY-MM-DD or YYYY-MM), or None


@dataclass(frozen=True)
class InputItem:
    """A single file to be processed.

    `publication` is None for standalone files (loose files in the input root,
    or a single-file --input). When set, page_label and total_pages_in_publication
    locate this file within its publication.
    """

    path: Path
    publication: PublicationInfo | None = None
    page_label: str | None = None
    total_pages_in_publication: int | None = None


def _supported_files_in(directory: Path) -> list[Path]:
    return sorted(
        f
        for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def load_image(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    return np.array(img)


def load_pdf_pages(path: Path, dpi: int = 300) -> list[np.ndarray]:
    pdf = pdfium.PdfDocument(path)
    pages = []
    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=dpi / 72)
        pil_image = bitmap.to_pil().convert("RGB")
        pages.append(np.array(pil_image))
    return pages


def resolve_inputs(
    input_path: str | Path,
    extractor: PublicationMetadataExtractor | None = None,
) -> list[InputItem]:
    """Resolve an input path to an ordered list of InputItem.

    Rules:
      - A file path → one standalone item (no publication).
      - A directory → its contents are walked one level deep:
          * Files directly inside become standalone items.
          * Subdirectories become publications; their supported files are
            sorted alphabetically and assigned page_label "1", "2", ... .
            Empty subdirectories are skipped with a warning.

    `extractor` decides how a publication folder yields (magazine_name,
    issue_date). Defaults to FolderNameRegexExtractor; swap via Pipeline
    config or by passing a different instance directly.
    """
    if extractor is None:
        extractor = FolderNameRegexExtractor()
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {path.suffix}. "
                f"Supported: {SUPPORTED_EXTENSIONS}"
            )
        return [InputItem(path=path)]

    if path.is_dir():
        items: list[InputItem] = []

        loose_files = _supported_files_in(path)
        publication_subdirs: list[tuple[Path, list[Path]]] = []
        for sub in sorted(p for p in path.iterdir() if p.is_dir()):
            page_files = _supported_files_in(sub)
            if not page_files:
                logger.warning(f"Publication folder is empty, skipping: {sub}")
                continue
            publication_subdirs.append((sub, page_files))

        # If the input directory itself only contains supported files (no
        # publication subdirs), treat it AS the publication. This matches
        # the natural "I pointed it at the magazine folder" mental model.
        # The previous rule ("input root is never a publication") only kicks
        # in when there's at least one publication subdir.
        if loose_files and not publication_subdirs:
            meta = extractor.extract(path)
            pub = PublicationInfo(
                name=path.name,
                source_path=str(path.resolve()),
                magazine_name=meta.magazine_name,
                issue_date=meta.issue_date,
            )
            total = len(loose_files)
            for i, f in enumerate(loose_files, start=1):
                items.append(
                    InputItem(
                        path=f,
                        publication=pub,
                        page_label=str(i),
                        total_pages_in_publication=total,
                    )
                )
        else:
            # Mixed mode (or pure-subdirs mode): loose files stay standalone,
            # subdirs are publications. Preserves prior behaviour.
            items.extend(InputItem(path=f) for f in loose_files)
            for sub, page_files in publication_subdirs:
                meta = extractor.extract(sub)
                pub = PublicationInfo(
                    name=sub.name,
                    source_path=str(sub.resolve()),
                    magazine_name=meta.magazine_name,
                    issue_date=meta.issue_date,
                )
                total = len(page_files)
                for i, f in enumerate(page_files, start=1):
                    items.append(
                        InputItem(
                            path=f,
                            publication=pub,
                            page_label=str(i),
                            total_pages_in_publication=total,
                        )
                    )

        if not items:
            logger.warning(f"No supported files found under {path}")
        else:
            n_pubs = len({i.publication.name for i in items if i.publication})
            n_loose = sum(1 for i in items if i.publication is None)
            logger.info(
                f"Resolved {len(items)} item(s) from {path} "
                f"({n_pubs} publication(s), {n_loose} loose file(s))"
            )
        return items

    raise ValueError(f"Input path is neither a file nor a directory: {path}")


def load_file_pages(path: Path) -> list[np.ndarray]:
    """Load a file and return a list of page images (numpy RGB arrays).

    Image files return a single-element list; PDFs return one array per page.
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

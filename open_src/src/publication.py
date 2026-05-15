"""Pluggable extractors for publication metadata.

A `PublicationMetadataExtractor` derives `(magazine_name, issue_date)` for a
publication folder. The default (`FolderNameRegexExtractor`) parses the folder
basename against a strict naming convention; alternative implementations can
inspect a sidecar file, query an LLM, etc., without changing the rest of the
pipeline.

Pattern mirrors the OCR / layout / NER backend registries in `pipeline.py`:
implement the ABC, register in PUBLICATION_EXTRACTORS, pick via config.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass(frozen=True)
class PublicationMetadata:
    """The fields an extractor derives for a publication folder.

    Distinct from `input_handler.PublicationInfo`, which also carries the
    folder's identity (basename, source_path).
    """

    magazine_name: str
    issue_date: str | None  # YYYY-MM-DD, YYYY-MM, or None


class PublicationMetadataExtractor(ABC):
    """Strategy for deriving publication metadata from a folder.

    Receives the full folder path so implementations can inspect contents
    (e.g. a sidecar `publication.yaml`) in addition to the basename.
    """

    @abstractmethod
    def extract(self, folder_path: Path) -> PublicationMetadata:
        """Derive (magazine_name, issue_date) for `folder_path`.

        Must always return a `PublicationMetadata`; if extraction fails,
        return the folder basename as `magazine_name` and `None` as
        `issue_date` so the pipeline can still proceed.
        """


_FOLDER_NAME_RE = re.compile(
    r"^(?P<magazine>.+)_(?P<date>\d{4}-\d{2}(?:-\d{2})?)$"
)


class FolderNameRegexExtractor(PublicationMetadataExtractor):
    """Default extractor — parses the folder basename against a strict convention.

    Recognised shapes:
      - `<magazine>_<YYYY-MM-DD>`
      - `<magazine>_<YYYY-MM>`

    Magazine name may itself contain underscores (e.g. `Vogue_Italia_2026-04-15`
    → magazine `Vogue_Italia`). Anything that doesn't match returns
    `(folder_basename, None)` with a warning so downstream code still sees
    a valid value.
    """

    def extract(self, folder_path: Path) -> PublicationMetadata:
        name = folder_path.name
        m = _FOLDER_NAME_RE.match(name)
        if m is None:
            logger.warning(
                f"Publication folder '{name}' does not match the convention "
                f"<magazine>_<YYYY-MM-DD> or <magazine>_<YYYY-MM>. "
                f"magazine_name will fall back to the folder basename and "
                f"issue_date will be NULL."
            )
            return PublicationMetadata(magazine_name=name, issue_date=None)
        return PublicationMetadata(
            magazine_name=m.group("magazine"),
            issue_date=m.group("date"),
        )


PUBLICATION_EXTRACTORS: dict[str, type[PublicationMetadataExtractor]] = {
    "folder_name_regex": FolderNameRegexExtractor,
}


def create_publication_extractor(backend: str) -> PublicationMetadataExtractor:
    """Instantiate the publication metadata extractor for the given backend name."""
    cls = PUBLICATION_EXTRACTORS.get(backend)
    if cls is None:
        raise ValueError(
            f"Unknown publication extractor backend: {backend}. "
            f"Available: {list(PUBLICATION_EXTRACTORS)}"
        )
    return cls()

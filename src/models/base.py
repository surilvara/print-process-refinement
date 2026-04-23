from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
from PIL import Image


# ── Data types shared across the pipeline ──


@dataclass
class BBox:
    """Normalised bounding box [x_min, y_min, x_max, y_max] in 0-1 range."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def to_list(self) -> list[float]:
        return [self.x_min, self.y_min, self.x_max, self.y_max]


@dataclass
class TextBlock:
    id: str
    text: str
    bbox: BBox
    confidence: float = 0.0


@dataclass
class ClassifiedTextBlock:
    id: str
    text: str
    bbox: BBox
    block_type: (
        str  # headline, subheadline, body, caption, byline, advertisement_copy, other
    )
    confidence: float = 0.0


@dataclass
class Entity:
    text: str
    label: str
    start: int
    end: int


@dataclass
class TextBlockWithEntities:
    id: str
    text: str
    bbox: BBox
    block_type: str
    entities: list[Entity] = field(default_factory=list)


@dataclass
class ImageRegion:
    id: str
    bbox: BBox
    image: np.ndarray  # Cropped image as numpy array


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: BBox


@dataclass
class ImageRegionWithDetections:
    id: str
    bbox: BBox  # Region bbox on the original page
    detections: list[Detection] = field(default_factory=list)


@dataclass
class OCRResult:
    text_blocks: list[TextBlock]
    image_regions: list[ImageRegion]


@dataclass
class PageResult:
    page_number: int
    text_blocks: list[TextBlockWithEntities]
    image_regions: list[ImageRegionWithDetections]


@dataclass
class DocumentResult:
    input_file: str
    pages: list[PageResult]
    errors: list[str] = field(default_factory=list)


# ── Abstract base classes for swappable models ──


class OCRModel(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load model weights / initialise."""

    @abstractmethod
    def extract(self, image: np.ndarray) -> OCRResult:
        """Extract text blocks and image regions from a page image."""


class LayoutModel(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load model weights / initialise."""

    @abstractmethod
    def classify(
        self, text_blocks: list[TextBlock], image: np.ndarray
    ) -> list[ClassifiedTextBlock]:
        """Classify text blocks by type (headline, body, caption, etc.)."""


class NERModel(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load model / initialise."""

    @abstractmethod
    def extract_entities(
        self, text_blocks: list[ClassifiedTextBlock]
    ) -> list[TextBlockWithEntities]:
        """Extract named entities from classified text blocks."""


class ImageAnalysisModel(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load model weights / initialise."""

    @abstractmethod
    def detect(
        self, image_regions: list[ImageRegion], prompts: list[str]
    ) -> list[ImageRegionWithDetections]:
        """Detect objects in image regions using text prompts."""

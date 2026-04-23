from __future__ import annotations

import spacy
from loguru import logger

from src.models.base import (
    ClassifiedTextBlock,
    Entity,
    NERModel,
    TextBlockWithEntities,
)


class SpacyNER(NERModel):
    """Named entity recognition using spaCy."""

    def __init__(
        self,
        model_name: str = "en_core_web_trf",
        label_remapping: dict[str, str] | None = None,
    ):
        self.model_name = model_name
        self.label_remapping: dict[str, str] = label_remapping or {}
        self.nlp = None

    def load(self) -> None:
        logger.info(f"Loading spaCy model: {self.model_name}")
        try:
            self.nlp = spacy.load(self.model_name)
        except OSError:
            logger.warning(
                f"spaCy model '{self.model_name}' not found. "
                f"Attempting to download..."
            )
            spacy.cli.download(self.model_name)
            self.nlp = spacy.load(self.model_name)
        logger.info(f"spaCy model loaded: {self.model_name}")

    def extract_entities(
        self, text_blocks: list[ClassifiedTextBlock]
    ) -> list[TextBlockWithEntities]:
        if self.nlp is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        results: list[TextBlockWithEntities] = []
        total_entities = 0

        for tb in text_blocks:
            doc = self.nlp(tb.text)
            entities = [
                Entity(
                    text=ent.text,
                    label=self.label_remapping.get(ent.label_, ent.label_),
                    start=ent.start_char,
                    end=ent.end_char,
                )
                for ent in doc.ents
            ]
            total_entities += len(entities)

            results.append(
                TextBlockWithEntities(
                    id=tb.id,
                    text=tb.text,
                    bbox=tb.bbox,
                    block_type=tb.block_type,
                    entities=entities,
                )
            )

        logger.info(
            f"spaCy extracted {total_entities} entities from "
            f"{len(text_blocks)} text block(s)"
        )
        return results

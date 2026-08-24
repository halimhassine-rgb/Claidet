"""Moteur d'extraction de recettes.

Ce package ne doit dépendre d'AUCUN toolkit d'interface (pas de PySide6,
pas de Flask/FastAPI, etc.). Il expose une API purement Python
(`engine.pipeline.ExtractionPipeline`) que consomment aujourd'hui
l'application de bureau (`desktop/`) et, demain, un serveur exposant la
même logique aux clients mobiles.
"""

from engine.models import (
    ExtractionResult,
    ExtractionStatus,
    Ingredient,
    PipelineStage,
    Recipe,
    Step,
)

__all__ = [
    "ExtractionResult",
    "ExtractionStatus",
    "Ingredient",
    "PipelineStage",
    "Recipe",
    "Step",
]

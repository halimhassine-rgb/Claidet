"""Modèles de données du moteur d'extraction.

Ces modèles sont le contrat entre le moteur et n'importe quel appelant
(interface de bureau aujourd'hui, serveur mobile demain). Ils ne doivent
rien connaître de la façon dont ils seront affichés ou persistés.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    """Étapes du pipeline, dans l'ordre d'exécution.

    Utilisé à la fois pour rapporter la progression (callback) et pour
    indiquer, en cas d'échec, à quelle étape l'extraction s'est arrêtée.
    """

    DOWNLOAD = "download"
    AUDIO_EXTRACTION = "audio_extraction"
    FRAME_EXTRACTION = "frame_extraction"
    TRANSCRIPTION = "transcription"
    RECIPE_RECONSTRUCTION = "recipe_reconstruction"


class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    # Le pipeline a échoué mais a récupéré des données exploitables
    # (transcript, légende, images) pour pré-remplir la saisie manuelle.
    PARTIAL = "partial"
    FAILED = "failed"


class Ingredient(BaseModel):
    name: str
    # Texte libre ("200 g", "1/2 cuillère à café", "au goût") plutôt que
    # des champs quantité/unité structurés : les recettes réelles sont
    # trop irrégulières pour un format strict, et un champ texte reste
    # trivialement éditable à la main en mode secours.
    quantity: str | None = None
    note: str | None = None


class Step(BaseModel):
    order: int
    text: str


class Recipe(BaseModel):
    """Une recette, qu'elle vienne de l'extraction automatique ou de la
    saisie manuelle — les deux chemins produisent le même objet, stocké
    de la même façon."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_url: str | None = None
    title: str
    servings: str | None = None
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    notes: str | None = None
    # Chemin vers l'image de couverture sur disque (dans le répertoire de
    # données de l'app), jamais les octets bruts : on ne veut pas de blobs
    # binaires dans un modèle qui transite aussi tel quel vers un futur
    # client mobile en JSON.
    cover_image_path: str | None = None
    extraction_method: Literal["auto", "manual"] = "manual"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExtractionResult(BaseModel):
    """Résultat complet d'une tentative d'extraction.

    `recipe` est toujours peuplé au mieux : sur un échec, il contient un
    brouillon partiel (titre par défaut, ingrédients/étapes vides) que
    l'UI peut passer directement à l'écran de saisie manuelle plutôt que
    de repartir de zéro.
    """

    status: ExtractionStatus
    recipe: Recipe
    transcript: str | None = None
    caption: str | None = None
    frame_paths: list[str] = Field(default_factory=list)
    failed_stage: PipelineStage | None = None
    error_message: str | None = None

    @property
    def needs_manual_review(self) -> bool:
        return self.status is not ExtractionStatus.SUCCESS

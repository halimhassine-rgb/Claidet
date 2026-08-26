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


# Suggestions proposées dans l'UI et au modèle de reconstruction ; le champ
# `Recipe.category` reste du texte libre (l'utilisateur garde la main pour
# taper autre chose), ce n'est qu'une liste de départ.
SUGGESTED_CATEGORIES = (
    "Entrée",
    "Plat",
    "Dessert",
    "Apéritif",
    "Accompagnement",
    "Boisson",
)


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
    # Texte libre plutôt qu'un enum : les suggestions de SUGGESTED_CATEGORIES
    # guident la saisie sans jamais l'empêcher de taper autre chose.
    category: str | None = None
    servings: str | None = None
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    notes: str | None = None
    # Chemin vers l'image de couverture sur disque (dans le répertoire de
    # données de l'app), jamais les octets bruts : on ne veut pas de blobs
    # binaires dans un modèle qui transite aussi tel quel vers un futur
    # client mobile en JSON.
    cover_image_path: str | None = None
    # Vidéo source conservée (contrairement au fichier de travail du
    # pipeline, supprimé une fois l'audio/les images extraits) pour
    # pouvoir la rejouer depuis la fiche détail.
    video_path: str | None = None
    extraction_method: Literal["auto", "manual"] = "manual"
    # Note sur 10, mise à la main ; None tant qu'elle n'a pas été notée.
    rating: int | None = Field(default=None, ge=0, le=10)
    is_favorite: bool = False
    # Position dans la liste "ordre personnalisé" (glisser-déposer sur
    # l'accueil) ; attribuée par le stockage à la création, jamais par
    # l'utilisateur directement.
    sort_order: int = 0
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
    # Reconstruction via Claude (True) ou par règles locales sans IA
    # (False) — piloté par l'utilisateur au moment de l'extraction, pour
    # savoir si l'écran de relecture doit proposer de relancer avec
    # Claude.
    used_ai: bool = True

    @property
    def needs_manual_review(self) -> bool:
        return self.status is not ExtractionStatus.SUCCESS

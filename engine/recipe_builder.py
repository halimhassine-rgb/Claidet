"""Reconstruction de la recette structurée à partir du transcript, de la
légende du post et des images clés (texte incrusté), via un LLM.

Un seul appel multimodal (texte + images) plutôt qu'un OCR séparé suivi
d'un LLM texte-seul : Claude lit directement le texte incrusté dans les
images clés, ce qui évite une dépendance OCR de plus et gère mieux les
polices/mises en forme fantaisistes qu'on trouve dans les reels.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Protocol

from engine.exceptions import RecipeReconstructionError
from engine.models import Ingredient, Recipe, Step, SUGGESTED_CATEGORIES

_SYSTEM_PROMPT = f"""\
Tu extrais une recette de cuisine structurée à partir de trois sources \
possibles, toutes issues de la même vidéo Instagram : la transcription \
audio, la légende du post, et des images clés extraites de la vidéo \
(qui peuvent contenir du texte incrusté : liste d'ingrédients, quantités, \
étapes). Combine ces sources ; en cas de contradiction, préfère le texte \
incrusté à l'écran (généralement plus précis que l'audio) puis la légende.

Réponds UNIQUEMENT avec un objet JSON, sans texte autour, au format exact :
{{
  "title": string,
  "category": string ou null,
  "servings": string ou null,
  "ingredients": [{{"name": string, "quantity": string ou null, "note": string ou null}}],
  "steps": [string, ...],
  "notes": string ou null
}}
Les étapes doivent être dans l'ordre d'exécution, une action par étape.
Pour "category", choisis de préférence parmi : {", ".join(SUGGESTED_CATEGORIES)} \
— ou une autre catégorie courte si aucune ne convient. Ce n'est qu'une \
suggestion que l'utilisateur pourra corriger, ne force pas une catégorie \
si le contenu est ambigu : mets null dans ce cas.
Si une information est réellement absente des sources, mets null plutôt \
que d'inventer."""


class RecipeReconstructor(Protocol):
    def reconstruct(
        self,
        *,
        transcript: str | None,
        caption: str | None,
        frame_paths: list[Path],
        source_url: str | None,
    ) -> Recipe: ...


class ClaudeRecipeReconstructor:
    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover
                raise RecipeReconstructionError(
                    "Le SDK anthropic n'est pas installé (extra 'engine' requis)."
                ) from exc
            if not self._api_key:
                raise RecipeReconstructionError(
                    "ANTHROPIC_API_KEY manquant : impossible de reconstruire la "
                    "recette automatiquement."
                )
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def reconstruct(
        self,
        *,
        transcript: str | None,
        caption: str | None,
        frame_paths: list[Path],
        source_url: str | None,
    ) -> Recipe:
        client = self._get_client()

        text_parts = []
        if caption:
            text_parts.append(f"Légende du post :\n{caption}")
        if transcript:
            text_parts.append(f"Transcription audio :\n{transcript}")
        if not text_parts:
            text_parts.append(
                "(Aucune légende ni transcription disponible : base-toi "
                "uniquement sur les images.)"
            )

        content: list[dict] = [{"type": "text", "text": "\n\n".join(text_parts)}]
        for path in frame_paths:
            content.append(_encode_image_block(path))

        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
        except Exception as exc:
            raise RecipeReconstructionError(f"Échec de l'appel au modèle : {exc}") from exc

        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        payload = _extract_json(raw_text)
        return _payload_to_recipe(payload, source_url=source_url)


def _encode_image_block(path: Path) -> dict:
    media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise RecipeReconstructionError(
            f"Réponse du modèle sans JSON exploitable : {text[:200]!r}"
        )
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise RecipeReconstructionError(f"JSON invalide renvoyé par le modèle : {exc}") from exc


def _payload_to_recipe(payload: dict, *, source_url: str | None) -> Recipe:
    try:
        ingredients = [
            Ingredient(
                name=item["name"],
                quantity=item.get("quantity"),
                note=item.get("note"),
            )
            for item in payload.get("ingredients", [])
        ]
        steps = [
            Step(order=index + 1, text=text)
            for index, text in enumerate(payload.get("steps", []))
        ]
        title = payload.get("title") or "Recette sans titre"
    except (KeyError, TypeError) as exc:
        raise RecipeReconstructionError(f"Structure JSON inattendue : {exc}") from exc

    return Recipe(
        source_url=source_url,
        title=title,
        category=payload.get("category"),
        servings=payload.get("servings"),
        ingredients=ingredients,
        steps=steps,
        notes=payload.get("notes"),
        extraction_method="auto",
    )


# -- Reconstruction sans IA (gratuite, par règles) ---------------------
#
# Aucun appel réseau, aucun coût : on s'appuie sur le fait que beaucoup de
# créateurs structurent déjà leur légende Instagram (liste à puces,
# quantités visibles) et que la transcription audio suit à peu près
# l'ordre des étapes. Le résultat est nécessairement moins fiable qu'une
# reconstruction par Claude — c'est un brouillon à vérifier, pas un
# substitut garanti.

_BULLET_PREFIX = re.compile(r"^\s*(?:[-•*✅🔸▪️♦️]|\d+[.)])\s*")
_QUANTITY_UNIT = (
    r"(?:g|kg|mg|ml|cl|dl|l|c\.?à\.?s\.?|c\.?à\.?c\.?|cuillères?(?:\s*à\s*\w+)?|"
    r"tasses?|pincées?|gousses?|tranches?|verres?|sachets?|unités?)"
)
_QUANTITY_LEAD = re.compile(
    rf"^\s*(\d+(?:[.,/]\d+)?\s*(?:-\s*\d+(?:[.,/]\d+)?)?\s*{_QUANTITY_UNIT}?\.?)\s*(?:de |d')?\s*(.+)$",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


class HeuristicRecipeReconstructor:
    """Reconstruction par règles simples, sans appel à un LLM.

    Alternative gratuite à `ClaudeRecipeReconstructor` : moins précise
    (pas de lecture du texte incrusté dans les images, pas de vraie
    compréhension du contenu), mais suffisante quand la légende du post
    est déjà bien structurée. L'utilisateur choisit cette option pour
    éviter le coût d'un appel IA, puis peut relancer avec Claude depuis
    l'écran de relecture si le résultat ne lui convient pas.
    """

    def reconstruct(
        self,
        *,
        transcript: str | None,
        caption: str | None,
        frame_paths: list[Path],
        source_url: str | None,
    ) -> Recipe:
        caption_lines = [line.strip() for line in (caption or "").splitlines() if line.strip()]
        ingredient_lines, other_caption_lines = _split_ingredient_lines(caption_lines)

        return Recipe(
            source_url=source_url,
            title=_guess_title(caption_lines),
            ingredients=_parse_ingredients(ingredient_lines),
            steps=_guess_steps(transcript, other_caption_lines),
            notes=caption,
            extraction_method="auto",
        )


def _guess_title(caption_lines: list[str]) -> str:
    if not caption_lines:
        return "Recette sans titre"
    # La légende commence en général par le nom du plat, avant la liste
    # d'ingrédients ou les hashtags.
    first = caption_lines[0].lstrip("#").strip()
    return first[:120] if first else "Recette sans titre"


def _split_ingredient_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    ingredient_lines, other_lines = [], []
    for line in lines:
        if line.startswith("#"):
            continue
        if _BULLET_PREFIX.match(line) or _QUANTITY_LEAD.match(line):
            ingredient_lines.append(_BULLET_PREFIX.sub("", line).strip())
        else:
            other_lines.append(line)
    return ingredient_lines, other_lines


def _parse_ingredients(lines: list[str]) -> list[Ingredient]:
    ingredients = []
    for line in lines:
        match = _QUANTITY_LEAD.match(line)
        if match:
            quantity, name = match.group(1).strip(), match.group(2).strip()
        else:
            quantity, name = None, line
        if name:
            ingredients.append(Ingredient(name=name, quantity=quantity))
    return ingredients


def _guess_steps(transcript: str | None, fallback_lines: list[str]) -> list[Step]:
    source = transcript.strip() if transcript and transcript.strip() else "\n".join(fallback_lines)
    sentences = [s.strip(" -–—") for s in _SENTENCE_SPLIT.split(source) if s.strip(" -–—")]
    return [Step(order=index + 1, text=text) for index, text in enumerate(sentences)]

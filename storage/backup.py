"""Export/import portable de la base de recettes.

Un simple fichier .zip (un manifeste JSON + les images de couverture)
plutôt qu'un format propriétaire : l'utilisateur peut le déplacer d'un
ordinateur à l'autre par clé USB, cloud ou email, sans rien connaître
de la structure interne de la base SQLite.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from engine.models import Recipe
from storage.repository import RecipeRepository

_MANIFEST_NAME = "recipes.json"
_COVERS_DIR_NAME = "covers"


class BackupError(Exception):
    """Archive d'export illisible ou invalide."""


def export_to_zip(repository: RecipeRepository, dest_path: Path) -> int:
    """Écrit toutes les recettes de `repository` dans une archive à
    `dest_path`. Renvoie le nombre de recettes exportées."""

    recipes = repository.list_all()

    with tempfile.TemporaryDirectory(prefix="reelicious_export_") as tmp:
        tmp_dir = Path(tmp)
        covers_dir = tmp_dir / _COVERS_DIR_NAME
        covers_dir.mkdir()

        manifest = []
        for recipe in recipes:
            data = recipe.model_dump(mode="json")
            data["cover_image_path"] = _export_cover(recipe, covers_dir)
            manifest.append(data)

        manifest_path = tmp_dir / _MANIFEST_NAME
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(manifest_path, _MANIFEST_NAME)
            for cover_file in covers_dir.iterdir():
                archive.write(cover_file, f"{_COVERS_DIR_NAME}/{cover_file.name}")

    return len(recipes)


def import_from_zip(repository: RecipeRepository, source_path: Path) -> int:
    """Importe (ou met à jour, même id = même recette) les recettes de
    l'archive `source_path`. Renvoie le nombre de recettes importées."""

    with tempfile.TemporaryDirectory(prefix="reelicious_import_") as tmp:
        tmp_dir = Path(tmp)
        try:
            with zipfile.ZipFile(source_path) as archive:
                archive.extractall(tmp_dir)
        except zipfile.BadZipFile as exc:
            raise BackupError(f"{source_path.name} n'est pas une archive valide.") from exc

        manifest_path = tmp_dir / _MANIFEST_NAME
        if not manifest_path.exists():
            raise BackupError(
                f"Archive invalide : {_MANIFEST_NAME!r} introuvable dans {source_path.name}."
            )

        try:
            entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BackupError(f"Contenu illisible dans {source_path.name}.") from exc

        count = 0
        for entry in entries:
            cover_rel = entry.get("cover_image_path")
            if cover_rel:
                cover_path = tmp_dir / cover_rel
                entry["cover_image_path"] = str(cover_path) if cover_path.exists() else None
            try:
                recipe = Recipe(**entry)
            except (TypeError, ValueError) as exc:
                # ValueError couvre aussi pydantic.ValidationError, qui en hérite.
                raise BackupError(f"Recette invalide dans {source_path.name} : {exc}") from exc
            repository.save(recipe)
            count += 1

    return count


def _export_cover(recipe: Recipe, covers_dir: Path) -> str | None:
    if not recipe.cover_image_path:
        return None
    source = Path(recipe.cover_image_path)
    if not source.exists():
        return None
    dest_name = f"{recipe.id}{source.suffix}"
    shutil.copyfile(source, covers_dir / dest_name)
    return f"{_COVERS_DIR_NAME}/{dest_name}"

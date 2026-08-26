"""Accès aux recettes persistées localement.

`RecipeRepository` est la seule porte d'entrée vers la base : ni
`engine` ni `desktop` ne touchent SQLite directement. C'est aussi ici,
et nulle part ailleurs, que l'image de couverture choisie pendant
l'extraction (dans un répertoire de travail temporaire) est copiée vers
un emplacement durable — l'`engine` n'a pas à connaître la disposition
du stockage persistant.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from engine.models import Ingredient, Recipe, Step
from storage.db import connect

_CATEGORY_ORDER_KEY = "category_order"
_SORT_MODE_KEY = "sort_mode"
DEFAULT_SORT_MODE = "manual"


class RecipeRepository:
    def __init__(
        self,
        db_path: Path,
        covers_dir: Path | None = None,
        videos_dir: Path | None = None,
    ) -> None:
        self._db_path = db_path
        self._covers_dir = covers_dir
        self._videos_dir = videos_dir
        if covers_dir is not None:
            covers_dir.mkdir(parents=True, exist_ok=True)
        if videos_dir is not None:
            videos_dir.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = connect(db_path)

    def close(self) -> None:
        self._conn.close()

    def save(self, recipe: Recipe) -> Recipe:
        existing_row = self._conn.execute(
            "SELECT created_at, sort_order FROM recipes WHERE id = ?", (recipe.id,)
        ).fetchone()
        if existing_row is not None:
            created_at = datetime.fromisoformat(existing_row["created_at"])
            sort_order = existing_row["sort_order"]
        else:
            created_at = recipe.created_at
            next_row = self._conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 AS next FROM recipes"
            ).fetchone()
            sort_order = next_row["next"]

        persisted = recipe.model_copy(
            update={
                "cover_image_path": self._persist_cover_image(recipe),
                "video_path": self._persist_video(recipe),
                "created_at": created_at,
                "updated_at": datetime.now(timezone.utc),
                "sort_order": sort_order,
            }
        )

        self._conn.execute(
            """
            INSERT INTO recipes (
                id, source_url, title, category, servings, ingredients_json,
                steps_json, notes, cover_image_path, video_path, extraction_method,
                rating, is_favorite, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source_url=excluded.source_url,
                title=excluded.title,
                category=excluded.category,
                servings=excluded.servings,
                ingredients_json=excluded.ingredients_json,
                steps_json=excluded.steps_json,
                notes=excluded.notes,
                cover_image_path=excluded.cover_image_path,
                video_path=excluded.video_path,
                extraction_method=excluded.extraction_method,
                rating=excluded.rating,
                is_favorite=excluded.is_favorite,
                sort_order=excluded.sort_order,
                updated_at=excluded.updated_at
            """,
            (
                persisted.id,
                persisted.source_url,
                persisted.title,
                persisted.category,
                persisted.servings,
                json.dumps([i.model_dump() for i in persisted.ingredients]),
                json.dumps([s.model_dump() for s in persisted.steps]),
                persisted.notes,
                persisted.cover_image_path,
                persisted.video_path,
                persisted.extraction_method,
                persisted.rating,
                1 if persisted.is_favorite else 0,
                persisted.sort_order,
                created_at.isoformat(),
                persisted.updated_at.isoformat(),
            ),
        )
        self._conn.commit()
        return persisted

    def get(self, recipe_id: str) -> Recipe | None:
        row = self._conn.execute(
            "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
        return _row_to_recipe(row) if row is not None else None

    def list_all(self) -> list[Recipe]:
        """Renvoie les recettes dans l'ordre personnalisé (glisser-déposer).
        Les autres tris (par note...) sont appliqués côté interface."""
        rows = self._conn.execute(
            "SELECT * FROM recipes ORDER BY sort_order ASC, updated_at DESC"
        ).fetchall()
        return [_row_to_recipe(row) for row in rows]

    def list_categories(self) -> list[str]:
        """Catégories réellement utilisées dans la base, y compris celles
        tapées à la main par l'utilisateur (pas seulement SUGGESTED_CATEGORIES)."""
        rows = self._conn.execute(
            "SELECT DISTINCT category FROM recipes WHERE category IS NOT NULL "
            "AND category != '' ORDER BY category"
        ).fetchall()
        return [row["category"] for row in rows]

    def find_by_source_url(self, source_url: str) -> Recipe | None:
        """Recherche une recette déjà enregistrée pour ce même lien source
        (utilisé pour avertir avant de ré-extraire un reel déjà importé)."""
        row = self._conn.execute(
            "SELECT * FROM recipes WHERE source_url = ? LIMIT 1", (source_url,)
        ).fetchone()
        return _row_to_recipe(row) if row is not None else None

    def delete(self, recipe_id: str) -> None:
        recipe = self.get(recipe_id)
        self._conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        self._conn.commit()
        if recipe and recipe.cover_image_path and self._covers_dir is not None:
            cover = Path(recipe.cover_image_path)
            if self._covers_dir in cover.parents:
                cover.unlink(missing_ok=True)
        if recipe and recipe.video_path and self._videos_dir is not None:
            video = Path(recipe.video_path)
            if self._videos_dir in video.parents:
                video.unlink(missing_ok=True)

    def set_favorite(self, recipe_id: str, is_favorite: bool) -> None:
        self._conn.execute(
            "UPDATE recipes SET is_favorite = ?, updated_at = ? WHERE id = ?",
            (1 if is_favorite else 0, datetime.now(timezone.utc).isoformat(), recipe_id),
        )
        self._conn.commit()

    def reorder_recipes(self, ordered_ids: list[str]) -> None:
        """Réassigne sort_order d'après la position de chaque id dans
        `ordered_ids` (glisser-déposer sur l'écran d'accueil)."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.executemany(
            "UPDATE recipes SET sort_order = ?, updated_at = ? WHERE id = ?",
            [(index, now, recipe_id) for index, recipe_id in enumerate(ordered_ids)],
        )
        self._conn.commit()

    # -- Préférences (ordre des catégories, mode de tri) -----------------
    # Persistées comme les recettes, dans la même base : elles survivent
    # donc naturellement à la fermeture de l'application.

    def get_category_order(self) -> list[str]:
        value = self._get_setting(_CATEGORY_ORDER_KEY)
        if value is None:
            return []
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []

    def set_category_order(self, order: list[str]) -> None:
        self._set_setting(_CATEGORY_ORDER_KEY, json.dumps(list(order), ensure_ascii=False))

    def get_sort_mode(self) -> str:
        return self._get_setting(_SORT_MODE_KEY) or DEFAULT_SORT_MODE

    def set_sort_mode(self, mode: str) -> None:
        self._set_setting(_SORT_MODE_KEY, mode)

    def _get_setting(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row is not None else None

    def _set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()

    def _persist_cover_image(self, recipe: Recipe) -> str | None:
        if not recipe.cover_image_path or self._covers_dir is None:
            return recipe.cover_image_path

        source = Path(recipe.cover_image_path)
        if self._covers_dir in source.parents:
            return recipe.cover_image_path  # déjà persisté

        if not source.exists():
            return None

        dest = self._covers_dir / f"{recipe.id}{source.suffix}"
        shutil.copyfile(source, dest)
        return str(dest)

    def _persist_video(self, recipe: Recipe) -> str | None:
        if not recipe.video_path or self._videos_dir is None:
            return recipe.video_path

        source = Path(recipe.video_path)
        if self._videos_dir in source.parents:
            return recipe.video_path  # déjà persistée

        if not source.exists():
            return None

        dest = self._videos_dir / f"{recipe.id}{source.suffix}"
        shutil.move(str(source), dest)
        return str(dest)


def _row_to_recipe(row: sqlite3.Row) -> Recipe:
    return Recipe(
        id=row["id"],
        source_url=row["source_url"],
        title=row["title"],
        category=row["category"],
        servings=row["servings"],
        ingredients=[Ingredient(**d) for d in json.loads(row["ingredients_json"])],
        steps=[Step(**d) for d in json.loads(row["steps_json"])],
        notes=row["notes"],
        cover_image_path=row["cover_image_path"],
        video_path=row["video_path"],
        extraction_method=row["extraction_method"],
        rating=row["rating"],
        is_favorite=bool(row["is_favorite"]),
        sort_order=row["sort_order"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )

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


class RecipeRepository:
    def __init__(self, db_path: Path, covers_dir: Path | None = None) -> None:
        self._db_path = db_path
        self._covers_dir = covers_dir
        if covers_dir is not None:
            covers_dir.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = connect(db_path)

    def close(self) -> None:
        self._conn.close()

    def save(self, recipe: Recipe) -> Recipe:
        existing_row = self._conn.execute(
            "SELECT created_at FROM recipes WHERE id = ?", (recipe.id,)
        ).fetchone()
        created_at = (
            datetime.fromisoformat(existing_row["created_at"])
            if existing_row is not None
            else recipe.created_at
        )

        persisted = recipe.model_copy(
            update={
                "cover_image_path": self._persist_cover_image(recipe),
                "created_at": created_at,
                "updated_at": datetime.now(timezone.utc),
            }
        )

        self._conn.execute(
            """
            INSERT INTO recipes (
                id, source_url, title, servings, ingredients_json, steps_json,
                notes, cover_image_path, extraction_method, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source_url=excluded.source_url,
                title=excluded.title,
                servings=excluded.servings,
                ingredients_json=excluded.ingredients_json,
                steps_json=excluded.steps_json,
                notes=excluded.notes,
                cover_image_path=excluded.cover_image_path,
                extraction_method=excluded.extraction_method,
                updated_at=excluded.updated_at
            """,
            (
                persisted.id,
                persisted.source_url,
                persisted.title,
                persisted.servings,
                json.dumps([i.model_dump() for i in persisted.ingredients]),
                json.dumps([s.model_dump() for s in persisted.steps]),
                persisted.notes,
                persisted.cover_image_path,
                persisted.extraction_method,
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
        rows = self._conn.execute(
            "SELECT * FROM recipes ORDER BY updated_at DESC"
        ).fetchall()
        return [_row_to_recipe(row) for row in rows]

    def delete(self, recipe_id: str) -> None:
        recipe = self.get(recipe_id)
        self._conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        self._conn.commit()
        if recipe and recipe.cover_image_path and self._covers_dir is not None:
            cover = Path(recipe.cover_image_path)
            if self._covers_dir in cover.parents:
                cover.unlink(missing_ok=True)

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


def _row_to_recipe(row: sqlite3.Row) -> Recipe:
    return Recipe(
        id=row["id"],
        source_url=row["source_url"],
        title=row["title"],
        servings=row["servings"],
        ingredients=[Ingredient(**d) for d in json.loads(row["ingredients_json"])],
        steps=[Step(**d) for d in json.loads(row["steps_json"])],
        notes=row["notes"],
        cover_image_path=row["cover_image_path"],
        extraction_method=row["extraction_method"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )

"""Connexion SQLite et schéma."""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id TEXT PRIMARY KEY,
    source_url TEXT,
    title TEXT NOT NULL,
    category TEXT,
    servings TEXT,
    ingredients_json TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    notes TEXT,
    cover_image_path TEXT,
    extraction_method TEXT NOT NULL,
    rating INTEGER,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Colonnes ajoutées après la version initiale du schéma : appliquées aux
# bases déjà existantes sans effacer les recettes qui y sont déjà.
_MIGRATIONS = (
    "ALTER TABLE recipes ADD COLUMN category TEXT",
    "ALTER TABLE recipes ADD COLUMN rating INTEGER",
    "ALTER TABLE recipes ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE recipes ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0",
)


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    for migration in _MIGRATIONS:
        try:
            conn.execute(migration)
        except sqlite3.OperationalError:
            pass  # colonne déjà présente (base créée avec le schéma à jour)
    conn.commit()
    return conn

"""Localisation des fichiers statiques (icône...), que l'app tourne
depuis les sources ou depuis un exécutable empaqueté par PyInstaller."""

from __future__ import annotations

import sys
from pathlib import Path


def asset_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / name

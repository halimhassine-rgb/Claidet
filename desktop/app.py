"""Point d'entrée de l'application de bureau."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from desktop.main_window import MainWindow
from engine.config import EngineConfig
from storage.repository import RecipeRepository


def main() -> int:
    config = EngineConfig.from_env()
    config.ensure_dirs()
    repository = RecipeRepository(config.db_path, covers_dir=config.covers_dir)

    app = QApplication(sys.argv)
    window = MainWindow(config, repository)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

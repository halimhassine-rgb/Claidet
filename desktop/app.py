"""Point d'entrée de l'application de bureau."""

from __future__ import annotations

import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from desktop import theme
from desktop.main_window import MainWindow
from desktop.resources import asset_path
from engine.config import EngineConfig
from storage.repository import RecipeRepository


def main() -> int:
    config = EngineConfig.from_env()
    config.ensure_dirs()
    repository = RecipeRepository(config.db_path, covers_dir=config.covers_dir)

    app = QApplication(sys.argv)
    app.setStyleSheet(theme.build_stylesheet())
    app.setFont(QFont("Segoe UI", 10))
    app.setWindowIcon(QIcon(str(asset_path("icon.png"))))
    window = MainWindow(config, repository)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

"""Vérifie que le dépôt reste utilisable depuis le QThread d'arrière-plan
de l'estimation des calories — régression pour un bug où le dépôt SQLite,
connecté sur le thread principal avec le réglage par défaut de sqlite3,
refusait silencieusement toute requête faite depuis un autre thread
(aucune erreur visible, aucune mise à jour appliquée)."""

from __future__ import annotations

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication

from desktop.controllers.calories_backfill_worker import CaloriesBackfillWorker
from engine.models import Ingredient, Recipe
from storage.repository import RecipeRepository


class _FakeReconstructor:
    def estimate_calories(self, *, ingredients, servings):
        return 400, "per_serving"


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_backfill_worker_updates_repository_from_background_thread(tmp_path):
    _ensure_app()
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    saved = repo.save(
        Recipe(title="Salade", ingredients=[Ingredient(name="Pâtes", quantity="200 g")])
    )

    worker = CaloriesBackfillWorker(repo, _FakeReconstructor(), [saved.id])

    loop = QEventLoop()
    result: dict[str, int] = {}

    def on_finished(updated: int) -> None:
        result["updated"] = updated
        loop.quit()

    worker.finished_ok.connect(on_finished)
    worker.start()
    loop.exec()

    assert result["updated"] == 1
    fetched = repo.get(saved.id)
    assert fetched.calories == 400
    assert fetched.calories_basis == "per_serving"
    assert fetched.calories_source == "estimated"

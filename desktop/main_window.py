"""Fenêtre principale : navigation entre les écrans et câblage vers le
moteur d'extraction et le stockage local.

C'est la seule classe de `desktop` qui appelle `engine`/`storage`
directement — les vues (`desktop/views/`) n'en connaissent rien, elles
ne font qu'émettre des signaux et exposer des méthodes de
chargement/construction sur des objets `Recipe`/`ExtractionResult`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from desktop.controllers.extraction_worker import ExtractionWorker
from desktop.views.recipe_detail_view import RecipeDetailView
from desktop.views.recipe_list_view import RecipeListView
from desktop.views.recipe_review_view import RecipeReviewView
from desktop.views.url_input_view import UrlInputView
from engine.config import EngineConfig
from engine.models import ExtractionResult, Recipe
from engine.pipeline import ExtractionPipeline
from storage.repository import RecipeRepository


class MainWindow(QMainWindow):
    def __init__(self, config: EngineConfig, repository: RecipeRepository) -> None:
        super().__init__()
        self.setWindowTitle("Reelicious — Recettes Instagram")
        self.resize(900, 700)

        self._repository = repository
        self._pipeline = ExtractionPipeline(config)
        self._worker: ExtractionWorker | None = None

        self._list_view = RecipeListView()
        self._url_view = UrlInputView()
        self._review_view = RecipeReviewView()
        self._detail_view = RecipeDetailView()

        self._stack = QStackedWidget()
        for view in (self._list_view, self._url_view, self._review_view, self._detail_view):
            self._stack.addWidget(view)
        self.setCentralWidget(self._stack)

        self._list_view.new_recipe_requested.connect(self._show_url_view)
        self._list_view.recipe_selected.connect(self._show_detail_view)

        self._url_view.extract_requested.connect(self._start_extraction)
        self._url_view.manual_requested.connect(self._start_manual_entry)

        self._review_view.save_requested.connect(self._save_recipe)
        self._review_view.cancel_requested.connect(self._show_list_view)

        self._detail_view.edit_requested.connect(self._edit_recipe)
        self._detail_view.delete_requested.connect(self._delete_recipe)
        self._detail_view.back_requested.connect(self._show_list_view)

        self._show_list_view()

    # -- Navigation -------------------------------------------------

    def _show_list_view(self) -> None:
        self._list_view.set_recipes(self._repository.list_all())
        self._stack.setCurrentWidget(self._list_view)

    def _show_url_view(self) -> None:
        self._url_view.reset()
        self._stack.setCurrentWidget(self._url_view)

    def _show_detail_view(self, recipe_id: str) -> None:
        recipe = self._repository.get(recipe_id)
        if recipe is None:
            self._show_list_view()
            return
        self._detail_view.load_recipe(recipe)
        self._stack.setCurrentWidget(self._detail_view)

    # -- Extraction ---------------------------------------------------

    def _start_extraction(self, url: str) -> None:
        self._url_view.set_busy(True, "Démarrage…")
        self._worker = ExtractionWorker(self._pipeline, url)
        self._worker.stage_changed.connect(lambda text: self._url_view.set_busy(True, text))
        self._worker.succeeded.connect(self._on_extraction_succeeded)
        self._worker.crashed.connect(self._on_extraction_crashed)
        self._worker.start()

    def _on_extraction_succeeded(self, result: ExtractionResult) -> None:
        self._url_view.set_busy(False)
        self._review_view.set_available_categories(self._repository.list_categories())
        self._review_view.load_from_result(result)
        self._stack.setCurrentWidget(self._review_view)

    def _on_extraction_crashed(self, message: str) -> None:
        self._url_view.set_busy(False)
        QMessageBox.critical(
            self,
            "Erreur inattendue",
            "L'extraction a rencontré une erreur imprévue :\n"
            f"{message}\n\nVous pouvez réessayer ou saisir la recette manuellement.",
        )

    def _start_manual_entry(self) -> None:
        self._review_view.set_available_categories(self._repository.list_categories())
        self._review_view.load_blank()
        self._stack.setCurrentWidget(self._review_view)

    # -- CRUD -----------------------------------------------------------

    def _save_recipe(self, recipe: Recipe) -> None:
        saved = self._repository.save(recipe)
        self._show_detail_view(saved.id)

    def _edit_recipe(self, recipe_id: str) -> None:
        recipe = self._repository.get(recipe_id)
        if recipe is None:
            return
        self._review_view.set_available_categories(self._repository.list_categories())
        self._review_view.load_from_recipe(recipe)
        self._stack.setCurrentWidget(self._review_view)

    def _delete_recipe(self, recipe_id: str) -> None:
        confirm = QMessageBox.question(
            self, "Supprimer la recette", "Supprimer définitivement cette recette ?"
        )
        if confirm == QMessageBox.Yes:
            self._repository.delete(recipe_id)
            self._show_list_view()

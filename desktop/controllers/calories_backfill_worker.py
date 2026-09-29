"""Estimation rétroactive des calories manquantes, en tâche de fond.

Séparé du reste du pipeline d'extraction : ici on ne repart pas d'une
vidéo, seulement des ingrédients déjà enregistrés d'une recette
existante (`ClaudeRecipeReconstructor.estimate_calories`).
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from engine.exceptions import RecipeReconstructionError
from engine.recipe_builder import ClaudeRecipeReconstructor
from storage.repository import RecipeRepository


class CaloriesBackfillWorker(QThread):
    progress = Signal(int, int)  # traité, total
    finished_ok = Signal(int)  # nombre de recettes mises à jour

    def __init__(
        self,
        repository: RecipeRepository,
        reconstructor: ClaudeRecipeReconstructor,
        recipe_ids: list[str],
    ) -> None:
        super().__init__()
        self._repository = repository
        self._reconstructor = reconstructor
        self._recipe_ids = recipe_ids

    def run(self) -> None:
        updated = 0
        total = len(self._recipe_ids)
        for index, recipe_id in enumerate(self._recipe_ids, start=1):
            recipe = self._repository.get(recipe_id)
            if recipe is not None and recipe.calories is None:
                try:
                    calories, basis = self._reconstructor.estimate_calories(
                        ingredients=recipe.ingredients, servings=recipe.servings
                    )
                except RecipeReconstructionError:
                    calories, basis = None, None
                if calories:
                    self._repository.update_calories(recipe_id, calories, basis, "estimated")
                    updated += 1
            self.progress.emit(index, total)
        self.finished_ok.emit(updated)

"""Tri des recettes sur l'écran d'accueil."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from desktop.views.recipe_list_view import RecipeListView
from engine.models import Recipe


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_sorts_by_calories_ascending_with_unset_last():
    _ensure_app()
    view = RecipeListView()
    view.set_recipes(
        [
            Recipe(title="Sans calories", sort_order=0),
            Recipe(title="Riche", calories=800, sort_order=1),
            Recipe(title="Léger", calories=200, sort_order=2),
        ]
    )
    view.set_sort_mode("calories_asc")

    ordered = view._sorted_recipes()

    assert [r.title for r in ordered] == ["Léger", "Riche", "Sans calories"]


def test_sorts_by_calories_descending_with_unset_last():
    _ensure_app()
    view = RecipeListView()
    view.set_recipes(
        [
            Recipe(title="Sans calories", sort_order=0),
            Recipe(title="Riche", calories=800, sort_order=1),
            Recipe(title="Léger", calories=200, sort_order=2),
        ]
    )
    view.set_sort_mode("calories_desc")

    ordered = view._sorted_recipes()

    assert [r.title for r in ordered] == ["Riche", "Léger", "Sans calories"]

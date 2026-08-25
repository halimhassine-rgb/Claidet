"""Écran d'accueil : la base locale des recettes déjà enregistrées."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from engine.models import Recipe

_ALL_CATEGORIES = "Toutes les catégories"
_NO_CATEGORY = "Sans catégorie"


class RecipeListView(QWidget):
    recipe_selected = Signal(str)  # recipe id
    new_recipe_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipes: list[Recipe] = []

        title = QLabel("Mes recettes")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        new_button = QPushButton("+ Nouvelle recette")
        new_button.clicked.connect(self.new_recipe_requested.emit)

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(new_button)

        self._category_filter = QComboBox()
        self._category_filter.addItem(_ALL_CATEGORIES)
        self._category_filter.currentIndexChanged.connect(lambda _: self._render())
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Catégorie :"))
        filter_row.addWidget(self._category_filter, 1)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.itemActivated.connect(self._on_item_activated)

        self._empty_label = QLabel("Aucune recette enregistrée pour l'instant.")
        self._empty_label.hide()

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(filter_row)
        layout.addWidget(self._empty_label)
        layout.addWidget(self._list)

    def set_recipes(self, recipes: list[Recipe]) -> None:
        self._recipes = recipes
        self._refresh_category_filter()
        self._render()

    def _refresh_category_filter(self) -> None:
        categories = sorted({r.category for r in self._recipes if r.category})
        has_uncategorized = any(not r.category for r in self._recipes)

        previous = self._category_filter.currentText()
        self._category_filter.blockSignals(True)
        self._category_filter.clear()
        self._category_filter.addItem(_ALL_CATEGORIES)
        self._category_filter.addItems(categories)
        if has_uncategorized:
            self._category_filter.addItem(_NO_CATEGORY)
        restored_index = self._category_filter.findText(previous)
        self._category_filter.setCurrentIndex(max(restored_index, 0))
        self._category_filter.blockSignals(False)

    def _render(self) -> None:
        selected = self._category_filter.currentText()
        if selected == _ALL_CATEGORIES or not selected:
            visible = self._recipes
        elif selected == _NO_CATEGORY:
            visible = [r for r in self._recipes if not r.category]
        else:
            visible = [r for r in self._recipes if r.category == selected]

        self._list.clear()
        self._empty_label.setVisible(len(self._recipes) == 0)
        for recipe in visible:
            details = " · ".join(filter(None, (recipe.category, recipe.servings)))
            label = recipe.title + (f"  —  {details}" if details else "")
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, recipe.id)
            self._list.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        self.recipe_selected.emit(item.data(Qt.UserRole))

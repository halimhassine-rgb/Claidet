"""Écran d'accueil : la base locale des recettes déjà enregistrées."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from engine.models import Recipe


class RecipeListView(QWidget):
    recipe_selected = Signal(str)  # recipe id
    new_recipe_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        title = QLabel("Mes recettes")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        new_button = QPushButton("+ Nouvelle recette")
        new_button.clicked.connect(self.new_recipe_requested.emit)

        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(new_button)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.itemActivated.connect(self._on_item_activated)

        self._empty_label = QLabel("Aucune recette enregistrée pour l'instant.")
        self._empty_label.hide()

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self._empty_label)
        layout.addWidget(self._list)

    def set_recipes(self, recipes: list[Recipe]) -> None:
        self._list.clear()
        self._empty_label.setVisible(len(recipes) == 0)
        for recipe in recipes:
            subtitle = recipe.servings or ""
            label = f"{recipe.title}" + (f"  —  {subtitle}" if subtitle else "")
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, recipe.id)
            self._list.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        self.recipe_selected.emit(item.data(Qt.UserRole))

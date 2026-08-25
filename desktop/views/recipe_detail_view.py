"""Affichage en lecture seule d'une recette de la base locale."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from engine.models import Recipe


class RecipeDetailView(QWidget):
    edit_requested = Signal(str)  # recipe id
    delete_requested = Signal(str)  # recipe id
    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipe_id: str | None = None

        back_button = QPushButton("← Retour")
        back_button.clicked.connect(self.back_requested.emit)
        edit_button = QPushButton("Modifier")
        edit_button.clicked.connect(lambda: self.edit_requested.emit(self._recipe_id))
        delete_button = QPushButton("Supprimer")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._recipe_id))
        header = QHBoxLayout()
        header.addWidget(back_button)
        header.addStretch(1)
        header.addWidget(edit_button)
        header.addWidget(delete_button)

        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self._category_label = QLabel()
        self._category_label.setStyleSheet("color: #555; font-weight: bold;")
        self._servings_label = QLabel()
        self._cover_label = QLabel()
        self._cover_label.setFixedSize(200, 200)
        self._cover_label.setAlignment(Qt.AlignCenter)
        self._cover_label.setStyleSheet("border: 1px solid #999;")

        top_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.addWidget(self._title_label)
        title_col.addWidget(self._category_label)
        title_col.addWidget(self._servings_label)
        title_col.addStretch(1)
        top_row.addLayout(title_col, 3)
        top_row.addWidget(self._cover_label, 1)

        self._ingredients_label = QLabel()
        self._ingredients_label.setWordWrap(True)
        self._steps_label = QLabel()
        self._steps_label.setWordWrap(True)
        self._notes_label = QLabel()
        self._notes_label.setWordWrap(True)
        self._source_label = QLabel()
        self._source_label.setOpenExternalLinks(True)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(top_row)
        layout.addWidget(QLabel("<b>Ingrédients</b>"))
        layout.addWidget(self._ingredients_label)
        layout.addWidget(QLabel("<b>Étapes</b>"))
        layout.addWidget(self._steps_label)
        layout.addWidget(QLabel("<b>Notes</b>"))
        layout.addWidget(self._notes_label)
        layout.addWidget(self._source_label)
        layout.addStretch(1)

    def load_recipe(self, recipe: Recipe) -> None:
        self._recipe_id = recipe.id
        self._title_label.setText(recipe.title)
        self._category_label.setText(recipe.category or "")
        self._category_label.setVisible(bool(recipe.category))
        self._servings_label.setText(recipe.servings or "")

        if recipe.cover_image_path and Path(recipe.cover_image_path).exists():
            pixmap = QPixmap(recipe.cover_image_path).scaled(
                200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self._cover_label.setPixmap(pixmap)
        else:
            self._cover_label.setPixmap(QPixmap())
            self._cover_label.setText("Pas d'image")

        if recipe.ingredients:
            lines = [
                f"• {ingredient.name}"
                + (f" — {ingredient.quantity}" if ingredient.quantity else "")
                + (f" ({ingredient.note})" if ingredient.note else "")
                for ingredient in recipe.ingredients
            ]
            self._ingredients_label.setText("<br>".join(lines))
        else:
            self._ingredients_label.setText("(aucun)")

        if recipe.steps:
            ordered = sorted(recipe.steps, key=lambda s: s.order)
            self._steps_label.setText(
                "<br>".join(f"{step.order}. {step.text}" for step in ordered)
            )
        else:
            self._steps_label.setText("(aucune)")

        self._notes_label.setText(recipe.notes or "")
        self._notes_label.setVisible(bool(recipe.notes))

        if recipe.source_url:
            self._source_label.setText(
                f'Source : <a href="{recipe.source_url}">{recipe.source_url}</a>'
            )
        else:
            self._source_label.setText("Source : saisie manuelle")

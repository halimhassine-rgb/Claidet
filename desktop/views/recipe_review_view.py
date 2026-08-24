"""Écran de relecture / édition d'une recette.

Cet écran unique sert trois usages, tous alimentés par la même méthode
`build_recipe()` :
  1. Valider (et corriger si besoin) une recette extraite automatiquement.
  2. Compléter à la main une extraction partielle, avec le transcript, la
     légende Instagram et les images clés affichés comme référence.
  3. Le mode de secours manuel pur, quand l'extraction n'a pas du tout
     été tentée ou a totalement échoué.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.models import ExtractionResult, ExtractionStatus, Ingredient, Recipe, Step

_INGREDIENT_COLUMNS = ("Ingrédient", "Quantité", "Note")


class RecipeReviewView(QWidget):
    save_requested = Signal(object)  # Recipe
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_recipe: Recipe | None = None
        self._cover_image_path: str | None = None

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: #b00020; font-weight: bold;")
        self._error_label.hide()

        self._title_edit = QLineEdit()
        self._servings_edit = QLineEdit()
        self._servings_edit.setPlaceholderText("ex : 4 personnes")

        self._cover_label = QLabel("Pas d'image")
        self._cover_label.setFixedSize(160, 160)
        self._cover_label.setAlignment(Qt.AlignCenter)
        self._cover_label.setStyleSheet("border: 1px solid #999;")
        cover_button = QPushButton("Choisir une image…")
        cover_button.clicked.connect(self._choose_cover_image)
        cover_col = QVBoxLayout()
        cover_col.addWidget(self._cover_label)
        cover_col.addWidget(cover_button)

        self._ingredients_table = QTableWidget(0, len(_INGREDIENT_COLUMNS))
        self._ingredients_table.setHorizontalHeaderLabels(_INGREDIENT_COLUMNS)
        self._ingredients_table.horizontalHeader().setStretchLastSection(True)
        add_ingredient_btn = QPushButton("+ Ingrédient")
        add_ingredient_btn.clicked.connect(lambda: self._add_ingredient_row())
        remove_ingredient_btn = QPushButton("Supprimer la ligne")
        remove_ingredient_btn.clicked.connect(self._remove_selected_ingredient_row)
        ingredients_buttons = QHBoxLayout()
        ingredients_buttons.addWidget(add_ingredient_btn)
        ingredients_buttons.addWidget(remove_ingredient_btn)
        ingredients_buttons.addStretch(1)

        self._steps_edit = QPlainTextEdit()
        self._steps_edit.setPlaceholderText("Une étape par ligne, dans l'ordre.")

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setPlaceholderText("Notes libres (facultatif)")

        self._raw_group = QGroupBox("Données brutes extraites (référence)")
        self._transcript_view = QPlainTextEdit()
        self._transcript_view.setReadOnly(True)
        self._caption_view = QPlainTextEdit()
        self._caption_view.setReadOnly(True)
        raw_layout = QVBoxLayout(self._raw_group)
        raw_layout.addWidget(QLabel("Transcription audio :"))
        raw_layout.addWidget(self._transcript_view)
        raw_layout.addWidget(QLabel("Légende du post :"))
        raw_layout.addWidget(self._caption_view)
        self._raw_group.hide()

        save_button = QPushButton("Enregistrer")
        save_button.clicked.connect(self._on_save_clicked)
        cancel_button = QPushButton("Annuler")
        cancel_button.clicked.connect(self.cancel_requested.emit)
        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)
        buttons_row.addWidget(cancel_button)
        buttons_row.addWidget(save_button)

        top_row = QHBoxLayout()
        form_col = QVBoxLayout()
        form_col.addWidget(QLabel("Titre"))
        form_col.addWidget(self._title_edit)
        form_col.addWidget(QLabel("Portions"))
        form_col.addWidget(self._servings_edit)
        top_row.addLayout(form_col, 3)
        top_row.addLayout(cover_col, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._error_label)
        layout.addLayout(top_row)
        layout.addWidget(QLabel("Ingrédients"))
        layout.addWidget(self._ingredients_table)
        layout.addLayout(ingredients_buttons)
        layout.addWidget(QLabel("Étapes"))
        layout.addWidget(self._steps_edit)
        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self._notes_edit)
        layout.addWidget(self._raw_group)
        layout.addLayout(buttons_row)

    # -- Chargement -------------------------------------------------

    def load_blank(self, source_url: str | None = None) -> None:
        self._base_recipe = None
        self._reset_fields()
        self._title_edit.setText("")
        if source_url:
            self._base_recipe = Recipe(source_url=source_url, title="", extraction_method="manual")

    def load_from_result(self, result: ExtractionResult) -> None:
        self._load_recipe_fields(result.recipe)
        self._base_recipe = result.recipe

        if result.status is ExtractionStatus.SUCCESS:
            self._error_label.hide()
        else:
            message = result.error_message or "L'extraction automatique a échoué."
            hint = " Complétez ou corrigez les champs ci-dessous à la main."
            self._error_label.setText(f"⚠ {message}{hint}")
            self._error_label.show()

        has_raw_data = bool(result.transcript or result.caption)
        self._transcript_view.setPlainText(result.transcript or "(aucune transcription)")
        self._caption_view.setPlainText(result.caption or "(aucune légende)")
        self._raw_group.setVisible(has_raw_data)

    def load_from_recipe(self, recipe: Recipe) -> None:
        self._load_recipe_fields(recipe)
        self._base_recipe = recipe
        self._error_label.hide()
        self._raw_group.hide()

    def _load_recipe_fields(self, recipe: Recipe) -> None:
        self._reset_fields()
        self._title_edit.setText(recipe.title)
        self._servings_edit.setText(recipe.servings or "")
        for ingredient in recipe.ingredients:
            self._add_ingredient_row(ingredient.name, ingredient.quantity or "", ingredient.note or "")
        self._steps_edit.setPlainText(
            "\n".join(step.text for step in sorted(recipe.steps, key=lambda s: s.order))
        )
        self._notes_edit.setPlainText(recipe.notes or "")
        self._set_cover_image(recipe.cover_image_path)

    def _reset_fields(self) -> None:
        self._cover_image_path = None
        self._cover_label.setPixmap(QPixmap())
        self._cover_label.setText("Pas d'image")
        self._title_edit.clear()
        self._servings_edit.clear()
        self._ingredients_table.setRowCount(0)
        self._steps_edit.clear()
        self._notes_edit.clear()
        self._error_label.hide()
        self._raw_group.hide()

    # -- Construction du résultat ------------------------------------

    def build_recipe(self) -> Recipe:
        ingredients = []
        for row in range(self._ingredients_table.rowCount()):
            name = self._cell_text(row, 0)
            if not name:
                continue
            ingredients.append(
                Ingredient(
                    name=name,
                    quantity=self._cell_text(row, 1) or None,
                    note=self._cell_text(row, 2) or None,
                )
            )

        steps = [
            Step(order=index + 1, text=line.strip())
            for index, line in enumerate(self._steps_edit.toPlainText().splitlines())
            if line.strip()
        ]

        base = self._base_recipe
        kwargs = dict(
            title=self._title_edit.text().strip() or "Recette sans titre",
            servings=self._servings_edit.text().strip() or None,
            ingredients=ingredients,
            steps=steps,
            notes=self._notes_edit.toPlainText().strip() or None,
            cover_image_path=self._cover_image_path,
        )
        if base is not None:
            return base.model_copy(update=kwargs)
        return Recipe(extraction_method="manual", **kwargs)

    def _on_save_clicked(self) -> None:
        self.save_requested.emit(self.build_recipe())

    # -- Ingrédients ---------------------------------------------------

    def _add_ingredient_row(self, name: str = "", quantity: str = "", note: str = "") -> None:
        row = self._ingredients_table.rowCount()
        self._ingredients_table.insertRow(row)
        for col, value in enumerate((name, quantity, note)):
            self._ingredients_table.setItem(row, col, QTableWidgetItem(value))

    def _remove_selected_ingredient_row(self) -> None:
        rows = {index.row() for index in self._ingredients_table.selectedIndexes()}
        for row in sorted(rows, reverse=True):
            self._ingredients_table.removeRow(row)

    def _cell_text(self, row: int, col: int) -> str:
        item = self._ingredients_table.item(row, col)
        return item.text().strip() if item is not None else ""

    # -- Image de couverture --------------------------------------------

    def _choose_cover_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir une image de couverture", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self._set_cover_image(path)

    def _set_cover_image(self, path: str | None) -> None:
        self._cover_image_path = path
        if path and Path(path).exists():
            pixmap = QPixmap(path).scaled(
                160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self._cover_label.setPixmap(pixmap)
            self._cover_label.setText("")
        else:
            self._cover_label.setPixmap(QPixmap())
            self._cover_label.setText("Pas d'image")

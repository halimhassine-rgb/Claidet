"""Écran de relecture / édition d'une recette.

Cet écran unique sert trois usages, tous alimentés par la même méthode
`build_recipe()` :
  1. Valider (et corriger si besoin) une recette extraite automatiquement.
  2. Compléter à la main une extraction partielle, avec le transcript, la
     légende Instagram et les images clés affichés comme référence.
  3. Le mode de secours manuel pur, quand l'extraction n'a pas du tout
     été tentée ou a totalement échoué.

Rien ici ne doit défiler « à l'intérieur » d'un champ : le tableau
d'ingrédients et les zones de texte s'agrandissent avec leur contenu, et
c'est la page entière (via la QScrollArea de premier niveau) qui défile
si tout ne tient pas à l'écran.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from desktop import theme
from engine.models import (
    ExtractionResult,
    ExtractionStatus,
    Ingredient,
    Recipe,
    Step,
    SUGGESTED_CATEGORIES,
)

_INGREDIENT_COLUMNS = ("Ingrédient", "Quantité", "Note")
_THUMB_SIZE = 72


def _field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "section-label")
    return label


class _AutoGrowPlainTextEdit(QPlainTextEdit):
    """QPlainTextEdit qui s'agrandit avec son contenu au lieu de défiler."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setMinimumHeight(72)
        self.textChanged.connect(self._autosize)

    def resizeEvent(self, event) -> None:  # noqa: N802 (nom imposé par Qt)
        super().resizeEvent(event)
        self._autosize()

    def _autosize(self) -> None:
        doc_height = self.document().size().height()
        frame = 2 * self.frameWidth()
        margins = self.contentsMargins()
        height = int(doc_height) + margins.top() + margins.bottom() + frame + 10
        self.setFixedHeight(max(72, height))


class _AutoHeightTableWidget(QTableWidget):
    """QTableWidget qui s'agrandit pour montrer toutes ses lignes sans
    barre de défilement interne."""

    def resizeEvent(self, event) -> None:  # noqa: N802 (nom imposé par Qt)
        super().resizeEvent(event)
        self.autosize()

    def autosize(self) -> None:
        self.resizeRowsToContents()
        total = self.horizontalHeader().height() + 2 * self.frameWidth()
        for row in range(self.rowCount()):
            total += self.rowHeight(row)
        self.setFixedHeight(max(total, self.horizontalHeader().height() + 40))


class RecipeReviewView(QWidget):
    save_requested = Signal(object)  # Recipe
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_recipe: Recipe | None = None
        self._cover_image_path: str | None = None

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            f"color: {theme.DANGER_TEXT}; background: {theme.DANGER_TINT}; "
            "font-weight: 600; border-radius: 10px; padding: 12px 14px;"
        )
        self._error_label.hide()

        self._title_edit = QLineEdit()
        self._category_combo = QComboBox()
        self._category_combo.setEditable(True)
        self._category_combo.addItem("")  # aucune catégorie
        self._category_combo.addItems(SUGGESTED_CATEGORIES)
        self._category_combo.lineEdit().setPlaceholderText("Aucune, ou tapez la vôtre")
        self._servings_edit = QLineEdit()
        self._servings_edit.setPlaceholderText("ex : 4 personnes")

        self._cover_label = QLabel("Pas d'image")
        self._cover_label.setFixedSize(160, 160)
        self._cover_label.setAlignment(Qt.AlignCenter)
        self._cover_label.setStyleSheet(
            f"border: 1px solid {theme.LINE}; border-radius: 14px; "
            f"background: {theme.SURFACE}; color: {theme.INK_FAINT};"
        )
        cover_button = QPushButton("Choisir une image…")
        cover_button.setProperty("variant", "secondary")
        cover_button.clicked.connect(self._choose_cover_image)
        cover_col = QVBoxLayout()
        cover_col.addWidget(self._cover_label)
        cover_col.addWidget(cover_button)

        self._frame_group = QButtonGroup(self)
        self._frame_group.setExclusive(True)
        self._frame_row = QHBoxLayout()
        self._frame_row.setSpacing(8)
        frame_section_layout = QVBoxLayout()
        frame_section_layout.setSpacing(8)
        frame_section_layout.addWidget(
            _field_label("Choisir l'image de couverture parmi les images extraites")
        )
        frame_section_layout.addLayout(self._frame_row)
        self._frame_section = QWidget()
        self._frame_section.setLayout(frame_section_layout)
        self._frame_section.hide()

        self._ingredients_table = _AutoHeightTableWidget(0, len(_INGREDIENT_COLUMNS))
        self._ingredients_table.setHorizontalHeaderLabels(_INGREDIENT_COLUMNS)
        self._ingredients_table.setWordWrap(True)
        self._ingredients_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._ingredients_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        header = self._ingredients_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setStretchLastSection(True)
        self._ingredients_table.setColumnWidth(0, 240)
        self._ingredients_table.setColumnWidth(1, 120)
        add_ingredient_btn = QPushButton("+ Ingrédient")
        add_ingredient_btn.setProperty("variant", "secondary")
        add_ingredient_btn.clicked.connect(lambda: self._add_ingredient_row())
        remove_ingredient_btn = QPushButton("Supprimer la ligne")
        remove_ingredient_btn.setProperty("variant", "ghost")
        remove_ingredient_btn.clicked.connect(self._remove_selected_ingredient_row)
        ingredients_buttons = QHBoxLayout()
        ingredients_buttons.addWidget(add_ingredient_btn)
        ingredients_buttons.addWidget(remove_ingredient_btn)
        ingredients_buttons.addStretch(1)

        self._steps_edit = _AutoGrowPlainTextEdit()
        self._steps_edit.setPlaceholderText("Une étape par ligne, dans l'ordre.")

        self._notes_edit = _AutoGrowPlainTextEdit()
        self._notes_edit.setPlaceholderText("Notes libres (facultatif)")

        self._raw_group = QGroupBox("Données brutes extraites (référence)")
        self._transcript_view = _AutoGrowPlainTextEdit()
        self._transcript_view.setReadOnly(True)
        self._caption_view = _AutoGrowPlainTextEdit()
        self._caption_view.setReadOnly(True)
        raw_layout = QVBoxLayout(self._raw_group)
        raw_layout.addWidget(QLabel("Transcription audio :"))
        raw_layout.addWidget(self._transcript_view)
        raw_layout.addWidget(QLabel("Légende du post :"))
        raw_layout.addWidget(self._caption_view)
        self._raw_group.hide()

        save_button = QPushButton("Enregistrer")
        save_button.setProperty("variant", "primary")
        save_button.clicked.connect(self._on_save_clicked)
        cancel_button = QPushButton("Annuler")
        cancel_button.setProperty("variant", "ghost")
        cancel_button.clicked.connect(self.cancel_requested.emit)
        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)
        buttons_row.addWidget(cancel_button)
        buttons_row.addWidget(save_button)

        top_row = QHBoxLayout()
        top_row.setSpacing(24)
        form_col = QVBoxLayout()
        form_col.setSpacing(8)
        form_col.addWidget(_field_label("Titre"))
        form_col.addWidget(self._title_edit)
        form_col.addWidget(_field_label("Catégorie"))
        form_col.addWidget(self._category_combo)
        form_col.addWidget(_field_label("Portions"))
        form_col.addWidget(self._servings_edit)
        top_row.addLayout(form_col, 3)
        top_row.addLayout(cover_col, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 28)
        content_layout.setSpacing(16)
        content_layout.addWidget(self._error_label)
        content_layout.addLayout(top_row)
        content_layout.addWidget(self._frame_section)
        content_layout.addWidget(_field_label("Ingrédients"))
        content_layout.addWidget(self._ingredients_table)
        content_layout.addLayout(ingredients_buttons)
        content_layout.addWidget(_field_label("Étapes"))
        content_layout.addWidget(self._steps_edit)
        content_layout.addWidget(_field_label("Notes"))
        content_layout.addWidget(self._notes_edit)
        content_layout.addWidget(self._raw_group)
        content_layout.addLayout(buttons_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # -- Catégories disponibles -----------------------------------------

    def set_available_categories(self, categories: list[str]) -> None:
        """Propose, en plus des suggestions de base, les catégories déjà
        utilisées dans la base — pour ne jamais avoir à les retaper."""
        current = self._category_combo.currentText()
        extra = sorted(c for c in categories if c not in SUGGESTED_CATEGORIES)
        self._category_combo.blockSignals(True)
        self._category_combo.clear()
        self._category_combo.addItem("")
        self._category_combo.addItems(list(SUGGESTED_CATEGORIES) + extra)
        self._category_combo.setCurrentText(current)
        self._category_combo.blockSignals(False)

    # -- Images clés extraites (choix de la couverture) ------------------

    def set_frame_candidates(self, frame_paths: list[str]) -> None:
        for button in list(self._frame_group.buttons()):
            self._frame_group.removeButton(button)
        while self._frame_row.count():
            item = self._frame_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        valid_paths = [p for p in frame_paths if Path(p).exists()]
        self._frame_section.setVisible(bool(valid_paths))

        for path in valid_paths:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                continue
            thumb = theme.rounded_pixmap(pixmap, QSize(_THUMB_SIZE, _THUMB_SIZE), radius=10)
            button = QToolButton()
            button.setProperty("variant", "thumb")
            button.setCheckable(True)
            button.setIcon(QIcon(thumb))
            button.setIconSize(QSize(_THUMB_SIZE, _THUMB_SIZE))
            button.setFixedSize(_THUMB_SIZE + 8, _THUMB_SIZE + 8)
            button.setChecked(path == self._cover_image_path)
            button.clicked.connect(lambda _checked=False, p=path: self._set_cover_image(p))
            button._frame_path = path  # pour resynchroniser l'état coché ailleurs
            self._frame_group.addButton(button)
            self._frame_row.addWidget(button)
        self._frame_row.addStretch(1)

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
        self.set_frame_candidates(result.frame_paths)

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
        self._category_combo.setCurrentText(recipe.category or "")
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
        self._category_combo.setCurrentText("")
        self._servings_edit.clear()
        self._ingredients_table.setRowCount(0)
        self._ingredients_table.autosize()
        self._steps_edit.clear()
        self._notes_edit.clear()
        self._error_label.hide()
        self._raw_group.hide()
        self.set_frame_candidates([])

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
            category=self._category_combo.currentText().strip() or None,
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
        self._ingredients_table.autosize()

    def _remove_selected_ingredient_row(self) -> None:
        rows = {index.row() for index in self._ingredients_table.selectedIndexes()}
        for row in sorted(rows, reverse=True):
            self._ingredients_table.removeRow(row)
        self._ingredients_table.autosize()

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
        for button in self._frame_group.buttons():
            button.setChecked(getattr(button, "_frame_path", None) == path)

        if path and Path(path).exists():
            pixmap = QPixmap(path).scaled(
                160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self._cover_label.setPixmap(pixmap)
            self._cover_label.setText("")
        else:
            self._cover_label.setPixmap(QPixmap())
            self._cover_label.setText("Pas d'image")

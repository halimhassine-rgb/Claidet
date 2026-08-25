"""Affichage en lecture seule d'une recette de la base locale."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from desktop import theme
from engine.models import Recipe

_HERO_SIZE = QSize(920, 280)
_STEP_BADGE = 34


class RecipeDetailView(QWidget):
    edit_requested = Signal(str)  # recipe id
    delete_requested = Signal(str)  # recipe id
    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipe_id: str | None = None

        back_button = QPushButton("←  Mes recettes")
        back_button.setProperty("variant", "ghost")
        back_button.clicked.connect(self.back_requested.emit)

        edit_button = QPushButton("Modifier")
        edit_button.setProperty("variant", "secondary")
        edit_button.clicked.connect(lambda: self.edit_requested.emit(self._recipe_id))
        delete_button = QPushButton("Supprimer")
        delete_button.setProperty("variant", "danger-ghost")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._recipe_id))

        header = QHBoxLayout()
        header.addWidget(back_button)
        header.addStretch(1)
        header.addWidget(edit_button)
        header.addWidget(delete_button)

        self._current_recipe: Recipe | None = None
        self._hero_label = QLabel()
        self._hero_label.setFixedHeight(_HERO_SIZE.height())
        self._hero_label.setAlignment(Qt.AlignCenter)

        self._title_label = QLabel()
        self._title_label.setProperty("role", "detail-title")
        self._title_label.setWordWrap(True)

        self._category_pill = QLabel()
        self._servings_label = QLabel()
        self._servings_label.setProperty("role", "muted")

        # Juste sous la photo : le lien le plus direct vers la source,
        # avant même le titre, sur sa propre ligne.
        self._source_link = QLabel()
        self._source_link.setStyleSheet("font-weight: 600; font-size: 13px;")
        self._source_link.setOpenExternalLinks(False)
        self._source_link.linkActivated.connect(self._open_source)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(12)
        meta_row.addWidget(self._category_pill)
        meta_row.addWidget(self._servings_label)
        meta_row.addStretch(1)

        title_block = QVBoxLayout()
        title_block.setSpacing(10)
        title_block.addWidget(self._source_link)
        title_block.addWidget(self._title_label)
        title_block.addLayout(meta_row)

        ingredients_label = QLabel("Ingrédients")
        ingredients_label.setProperty("role", "section-label")
        self._ingredients_col = QVBoxLayout()
        self._ingredients_col.setSpacing(11)
        ingredients_box = QVBoxLayout()
        ingredients_box.addWidget(ingredients_label)
        ingredients_box.addLayout(self._ingredients_col)
        ingredients_box.addStretch(1)
        ingredients_wrap = QWidget()
        ingredients_wrap.setLayout(ingredients_box)
        ingredients_wrap.setFixedWidth(260)

        steps_label = QLabel("Étapes")
        steps_label.setProperty("role", "section-label")
        self._steps_col = QVBoxLayout()
        self._steps_col.setSpacing(16)
        steps_box = QVBoxLayout()
        steps_box.addWidget(steps_label)
        steps_box.addLayout(self._steps_col)
        steps_wrap = QWidget()
        steps_wrap.setLayout(steps_box)

        body_row = QHBoxLayout()
        body_row.setSpacing(48)
        body_row.addWidget(ingredients_wrap)
        body_row.addWidget(steps_wrap, 1)

        self._notes_frame = QFrame()
        self._notes_frame.setProperty("role", "notes")
        self._notes_frame.setAttribute(Qt.WA_StyledBackground, True)
        notes_label = QLabel("Notes")
        notes_label.setProperty("role", "section-label")
        self._notes_text = QLabel()
        self._notes_text.setProperty("role", "notes-text")
        self._notes_text.setWordWrap(True)
        notes_layout = QVBoxLayout(self._notes_frame)
        notes_layout.setContentsMargins(22, 18, 22, 20)
        notes_layout.setSpacing(8)
        notes_layout.addWidget(notes_label)
        notes_layout.addWidget(self._notes_text)

        content = QVBoxLayout()
        content.setSpacing(28)
        content.addWidget(self._hero_label)
        content.addLayout(title_block)
        content.addLayout(body_row)
        content.addWidget(self._notes_frame)
        content_wrap = QWidget()
        content_wrap.setLayout(content)
        content_wrap.setMaximumWidth(_HERO_SIZE.width())

        content_row = QHBoxLayout()
        content_row.addStretch(1)
        content_row.addWidget(content_wrap, 1)
        content_row.addStretch(1)

        scroll_body = QWidget()
        scroll_layout = QVBoxLayout(scroll_body)
        scroll_layout.setContentsMargins(32, 24, 32, 32)
        scroll_layout.setSpacing(20)
        scroll_layout.addLayout(header)
        scroll_layout.addLayout(content_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(scroll_body)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def load_recipe(self, recipe: Recipe) -> None:
        self._recipe_id = recipe.id
        self._current_recipe = recipe
        self._title_label.setText(recipe.title)
        self._refresh_hero()

        if recipe.category:
            bg, fg = theme.category_colors(recipe.category)
            self._category_pill.setText(recipe.category)
            self._category_pill.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:10px; "
                "padding:5px 12px; font-size:12px; font-weight:700;"
            )
            self._category_pill.show()
        else:
            self._category_pill.hide()

        self._servings_label.setText(recipe.servings or "")
        self._servings_label.setVisible(bool(recipe.servings))

        if recipe.source_url:
            self._source_link.setText(
                f'<a href="{recipe.source_url}" style="color:{theme.ACCENT};'
                f'text-decoration:none;">Voir le reel original ↗</a>'
            )
            self._source_link.show()
        else:
            self._source_link.hide()

        _clear_layout(self._ingredients_col)
        for ingredient in recipe.ingredients:
            self._ingredients_col.addLayout(_ingredient_row(ingredient))
        if not recipe.ingredients:
            placeholder = QLabel("(aucun)")
            placeholder.setProperty("role", "muted")
            self._ingredients_col.addWidget(placeholder)

        _clear_layout(self._steps_col)
        for step in sorted(recipe.steps, key=lambda s: s.order):
            self._steps_col.addLayout(_step_row(step.order, step.text))
        if not recipe.steps:
            placeholder = QLabel("(aucune)")
            placeholder.setProperty("role", "muted")
            self._steps_col.addWidget(placeholder)

        if recipe.notes:
            self._notes_text.setText(recipe.notes)
            self._notes_frame.show()
        else:
            self._notes_frame.hide()

    def _open_source(self, url: str) -> None:
        QDesktopServices.openUrl(url)

    def resizeEvent(self, event) -> None:  # noqa: N802 (nom imposé par Qt)
        super().resizeEvent(event)
        self._refresh_hero()

    def _refresh_hero(self) -> None:
        if self._current_recipe is None:
            return
        # Régénérée à la largeur réelle du label (et non une largeur fixe
        # devinée à l'avance) : sur certains systèmes (résolutions
        # d'écran/mise à l'échelle variées), une taille figée pouvait ne
        # pas correspondre à l'espace réellement disponible.
        width = max(self._hero_label.width(), 320)
        size = QSize(width, _HERO_SIZE.height())
        self._hero_label.setPixmap(_hero_pixmap(self._current_recipe, size))


def _hero_pixmap(recipe: Recipe, size: QSize) -> QPixmap:
    if recipe.cover_image_path:
        path = Path(recipe.cover_image_path)
        if path.exists():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return theme.rounded_pixmap(pixmap, size, radius=20)
    return theme.placeholder_cover(size, radius=20)


def _ingredient_row(ingredient) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(11)

    dot = QLabel()
    dot.setFixedSize(15, 15)
    dot.setStyleSheet(
        f"border: 1.5px solid {theme.LINE}; border-radius: 7px; margin-top: 2px;"
    )

    text = ingredient.name
    if ingredient.quantity:
        text = f"<b>{ingredient.quantity}</b> {ingredient.name}"
    if ingredient.note:
        text += f' <span style="color:{theme.INK_FAINT};">— {ingredient.note}</span>'

    label = QLabel(text)
    label.setWordWrap(True)

    row.addWidget(dot, 0, Qt.AlignTop)
    row.addWidget(label, 1)
    return row


def _step_row(order: int, text: str) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(16)

    badge = QLabel(str(order))
    badge.setFixedSize(_STEP_BADGE, _STEP_BADGE)
    badge.setAlignment(Qt.AlignCenter)
    badge.setStyleSheet(
        f"background:{theme.SURFACE}; border:1px solid {theme.LINE}; "
        f"border-radius:{_STEP_BADGE // 2}px; color:{theme.ACCENT}; font-weight:700;"
    )

    label = QLabel(text)
    label.setWordWrap(True)

    row.addWidget(badge, 0, Qt.AlignTop)
    row.addWidget(label, 1)
    return row


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
            continue
        sub_layout = item.layout()
        if sub_layout is not None:
            _clear_layout(sub_layout)
            sub_layout.deleteLater()

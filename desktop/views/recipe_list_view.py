"""Écran d'accueil : la base locale des recettes déjà enregistrées."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from desktop import theme
from engine.models import Recipe

_ALL_CATEGORIES = "Toutes les catégories"
_NO_CATEGORY = "Sans catégorie"
_CARD_WIDTH = 240
_COVER_HEIGHT = 132
_GRID_SPACING = 20


class _RecipeCard(QFrame):
    clicked = Signal(str)  # recipe id

    def __init__(self, recipe: Recipe, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipe_id = recipe.id
        self.setProperty("role", "card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(_CARD_WIDTH)
        self.setCursor(Qt.PointingHandCursor)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(35, 44, 30, 45))
        self.setGraphicsEffect(shadow)

        cover_label = QLabel()
        cover_label.setFixedSize(_CARD_WIDTH, _COVER_HEIGHT)
        cover_label.setPixmap(_cover_pixmap(recipe, QSize(_CARD_WIDTH, _COVER_HEIGHT)))

        title_label = QLabel(recipe.title)
        title_label.setProperty("role", "title")
        title_label.setWordWrap(True)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        if recipe.category:
            bg, fg = theme.category_colors(recipe.category)
            pill = QLabel(recipe.category)
            pill.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:9px; "
                "padding:3px 9px; font-size:11px; font-weight:700;"
            )
            meta_row.addWidget(pill)
        if recipe.servings:
            servings_label = QLabel(recipe.servings)
            servings_label.setProperty("role", "faint")
            meta_row.addWidget(servings_label)
        meta_row.addStretch(1)

        body = QVBoxLayout()
        body.setContentsMargins(16, 14, 16, 16)
        body.setSpacing(9)
        body.addWidget(title_label)
        body.addLayout(meta_row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(cover_label)
        outer.addLayout(body)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._recipe_id)
        super().mousePressEvent(event)


class RecipeListView(QWidget):
    recipe_selected = Signal(str)  # recipe id
    new_recipe_requested = Signal()
    export_requested = Signal()
    import_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipes: list[Recipe] = []
        self._columns = 3

        mark = QLabel()
        mark.setFixedSize(34, 34)
        mark.setPixmap(_wordmark_pixmap(34))

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        wordmark = QLabel("Reelicious")
        wordmark.setProperty("role", "wordmark")
        tagline = QLabel("Vos reels, transformés en recettes")
        tagline.setProperty("role", "tagline")
        title_col.addWidget(wordmark)
        title_col.addWidget(tagline)

        header_left = QHBoxLayout()
        header_left.setSpacing(12)
        header_left.addWidget(mark)
        header_left.addLayout(title_col)

        more_button = QToolButton()
        more_button.setText("⋯")
        more_button.setProperty("variant", "secondary")
        more_button.setPopupMode(QToolButton.InstantPopup)
        more_menu = QMenu(more_button)
        more_menu.addAction("Exporter mes recettes…", self.export_requested.emit)
        more_menu.addAction("Importer des recettes…", self.import_requested.emit)
        more_button.setMenu(more_menu)

        new_button = QPushButton("+  Nouvelle recette")
        new_button.setProperty("variant", "primary")
        new_button.clicked.connect(self.new_recipe_requested.emit)

        header = QHBoxLayout()
        header.addLayout(header_left)
        header.addStretch(1)
        header.addWidget(more_button)
        header.addWidget(new_button)

        self._filter_group = QButtonGroup(self)
        self._filter_group.setExclusive(True)
        self._filter_row = QHBoxLayout()
        self._filter_row.setSpacing(8)

        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(_GRID_SPACING)
        self._grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self._empty_widget = self._build_empty_state()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self._grid_container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(22)
        layout.addLayout(header)
        layout.addLayout(self._filter_row)
        layout.addWidget(scroll, 1)

    def _build_empty_state(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 60, 0, 60)
        layout.setSpacing(10)

        icon = QLabel()
        icon.setPixmap(theme.placeholder_cover(QSize(88, 88), radius=44))
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("Aucune recette dans cette catégorie")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignCenter)

        sub = QLabel("Ajoutez-en une à partir d'un lien Instagram, ou changez de filtre.")
        sub.setProperty("role", "muted")
        sub.setAlignment(Qt.AlignCenter)

        button = QPushButton("+  Nouvelle recette")
        button.setProperty("variant", "primary")
        button.clicked.connect(self.new_recipe_requested.emit)

        layout.addWidget(icon, 0, Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addWidget(button, 0, Qt.AlignCenter)
        return container

    # -- Données -----------------------------------------------------

    def set_recipes(self, recipes: list[Recipe]) -> None:
        self._recipes = recipes
        self._refresh_category_filter()
        self._render()

    def _refresh_category_filter(self) -> None:
        previous = self._active_category() if self._filter_group.buttons() else _ALL_CATEGORIES

        for button in list(self._filter_group.buttons()):
            self._filter_group.removeButton(button)
        while self._filter_row.count():
            item = self._filter_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        categories = sorted({r.category for r in self._recipes if r.category})
        has_uncategorized = any(not r.category for r in self._recipes)
        labels = [_ALL_CATEGORIES, *categories]
        if has_uncategorized:
            labels.append(_NO_CATEGORY)

        for label in labels:
            button = QPushButton(label)
            button.setProperty("variant", "pill")
            button.setCheckable(True)
            button.setChecked(label == previous)
            button.clicked.connect(self._render)
            self._filter_group.addButton(button)
            self._filter_row.addWidget(button)
        self._filter_row.addStretch(1)

        if self._filter_group.checkedButton() is None and self._filter_group.buttons():
            self._filter_group.buttons()[0].setChecked(True)

    def _active_category(self) -> str:
        checked = self._filter_group.checkedButton()
        return checked.text() if checked else _ALL_CATEGORIES

    def _render(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        selected = self._active_category()
        if selected == _ALL_CATEGORIES:
            visible = self._recipes
        elif selected == _NO_CATEGORY:
            visible = [r for r in self._recipes if not r.category]
        else:
            visible = [r for r in self._recipes if r.category == selected]

        if not visible:
            self._grid.addWidget(self._empty_widget, 0, 0, 1, max(self._columns, 1))
            self._empty_widget.show()
            return

        self._empty_widget.hide()
        for index, recipe in enumerate(visible):
            card = _RecipeCard(recipe)
            card.clicked.connect(self.recipe_selected.emit)
            row, col = divmod(index, self._columns)
            self._grid.addWidget(card, row, col)

    # -- Mise en page responsive -----------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802 (nom imposé par Qt)
        super().resizeEvent(event)
        available = self.width() - 64
        columns = max(1, available // (_CARD_WIDTH + _GRID_SPACING))
        if columns != self._columns:
            self._columns = columns
            self._render()


def _cover_pixmap(recipe: Recipe, size: QSize) -> QPixmap:
    if recipe.cover_image_path:
        path = Path(recipe.cover_image_path)
        if path.exists():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return theme.rounded_pixmap(pixmap, size, radius=16, round_bottom=False)
    return theme.placeholder_cover(size, radius=16, round_bottom=False)


def _wordmark_pixmap(size: int) -> QPixmap:
    """Petite marque 'lecture sur assiette' — reel + recette."""

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(theme.ACCENT_TINT))
    painter.drawEllipse(0, 0, size, size)

    painter.setBrush(QColor(theme.ACCENT))
    margin = size * 0.32
    path = QPainterPath()
    path.moveTo(margin, size * 0.28)
    path.lineTo(size - margin * 0.7, size / 2)
    path.lineTo(margin, size * 0.72)
    path.closeSubpath()
    painter.drawPath(path)
    painter.end()
    return pixmap

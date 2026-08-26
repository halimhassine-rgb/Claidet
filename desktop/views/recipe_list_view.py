"""Écran d'accueil : la base locale des recettes déjà enregistrées."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
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
from desktop.widgets import HeartToggle, heart_icon
from engine.models import Recipe

_ALL_CATEGORIES = "Toutes les catégories"
_NO_CATEGORY = "Sans catégorie"
_CARD_WIDTH = 240
_COVER_HEIGHT = 132
_GRID_SPACING = 20
_RECIPE_MIME = "application/x-reelicious-recipe-id"
_CATEGORY_MIME = "application/x-reelicious-category"

_SORT_MODES = (
    ("manual", "Ordre personnalisé"),
    ("rating_desc", "Note décroissante"),
    ("rating_asc", "Note croissante"),
)


class _RecipeCard(QFrame):
    clicked = Signal(str)  # recipe id
    favorite_toggled = Signal(str, bool)  # recipe id, is_favorite
    reorder_requested = Signal(str, str)  # dragged recipe id, target recipe id

    def __init__(self, recipe: Recipe, draggable: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipe_id = recipe.id
        self._draggable = draggable
        self._drag_start: QPoint | None = None
        self._dragging = False
        self.setProperty("role", "card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(_CARD_WIDTH)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(True)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(35, 44, 30, 45))
        self.setGraphicsEffect(shadow)

        cover_label = QLabel(self)
        cover_label.setFixedSize(_CARD_WIDTH, _COVER_HEIGHT)
        cover_label.setPixmap(_cover_pixmap(recipe, QSize(_CARD_WIDTH, _COVER_HEIGHT)))

        self._heart = HeartToggle(overlay=True, parent=cover_label)
        self._heart.setChecked(recipe.is_favorite)
        self._heart.move(_CARD_WIDTH - self._heart.width() - 8, 8)
        self._heart.toggled.connect(
            lambda checked: self.favorite_toggled.emit(self._recipe_id, checked)
        )

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
        if recipe.rating:
            rating_label = QLabel(f"★ {recipe.rating}/10")
            rating_label.setStyleSheet(f"color: {theme.ACCENT}; font-size: 11px; font-weight: 700;")
            body.addWidget(rating_label)
        body.addLayout(meta_row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(cover_label)
        outer.addLayout(body)

    # -- Clic vs. glisser-déposer -----------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._draggable
            and self._drag_start is not None
            and event.buttons() & Qt.LeftButton
            and (event.position().toPoint() - self._drag_start).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._dragging = True
            self._start_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and not self._dragging and self._drag_start is not None:
            self.clicked.emit(self._recipe_id)
        self._drag_start = None
        self._dragging = False
        super().mouseReleaseEvent(event)

    def _start_drag(self) -> None:
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_RECIPE_MIME, self._recipe_id.encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab().scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.setHotSpot(QPoint(20, 20))
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event) -> None:
        if self._draggable and event.mimeData().hasFormat(_RECIPE_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        source_id = bytes(event.mimeData().data(_RECIPE_MIME)).decode("utf-8")
        if source_id and source_id != self._recipe_id:
            self.reorder_requested.emit(source_id, self._recipe_id)
        event.acceptProposedAction()


class _DraggableCategoryButton(QPushButton):
    """Pastille de catégorie, glissable pour changer l'ordre d'affichage."""

    reorder_requested = Signal(str, str)  # catégorie déplacée, catégorie cible

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self._drag_start: QPoint | None = None
        self.setAcceptDrops(True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._drag_start is not None
            and event.buttons() & Qt.LeftButton
            and (event.position().toPoint() - self._drag_start).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData(_CATEGORY_MIME, self.text().encode("utf-8"))
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.exec(Qt.MoveAction)
            self._drag_start = None
            return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(_CATEGORY_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        source = bytes(event.mimeData().data(_CATEGORY_MIME)).decode("utf-8")
        if source and source != self.text():
            self.reorder_requested.emit(source, self.text())
        event.acceptProposedAction()


class RecipeListView(QWidget):
    recipe_selected = Signal(str)  # recipe id
    new_recipe_requested = Signal()
    export_requested = Signal()
    import_requested = Signal()
    favorite_toggle_requested = Signal(str, bool)  # recipe id, is_favorite
    reorder_requested = Signal(list)  # ids de recette dans le nouvel ordre
    category_order_changed = Signal(list)
    sort_mode_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipes: list[Recipe] = []
        self._columns = 3
        self._category_order: list[str] = []
        self._sort_mode = "manual"
        self._favorites_only = False

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

        sort_label = QLabel("Trier par :")
        sort_label.setProperty("role", "muted")
        self._sort_combo = QComboBox()
        for _key, label in _SORT_MODES:
            self._sort_combo.addItem(label)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_mode_selected)

        self._favorites_button = QPushButton(" Favoris")
        self._favorites_button.setProperty("variant", "pill")
        self._favorites_button.setCheckable(True)
        self._favorites_button.setIconSize(QSize(13, 13))
        self._favorites_button.toggled.connect(self._on_favorites_filter_toggled)
        self._refresh_favorites_button_icon()

        self._filter_group = QButtonGroup(self)
        self._filter_group.setExclusive(True)
        self._filter_row = QHBoxLayout()
        self._filter_row.setSpacing(8)

        filters_row = QHBoxLayout()
        filters_row.setSpacing(16)
        filters_row.addLayout(self._filter_row, 1)
        filters_row.addWidget(self._favorites_button)
        filters_row.addWidget(sort_label)
        filters_row.addWidget(self._sort_combo)

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
        layout.addLayout(filters_row)
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

    # -- Préférences (appelées par MainWindow avant set_recipes) ---------

    def set_category_order(self, order: list[str]) -> None:
        self._category_order = list(order)

    def set_sort_mode(self, mode: str) -> None:
        self._sort_mode = mode if mode in dict(_SORT_MODES) else "manual"
        index = [key for key, _label in _SORT_MODES].index(self._sort_mode)
        self._sort_combo.blockSignals(True)
        self._sort_combo.setCurrentIndex(index)
        self._sort_combo.blockSignals(False)

    def _on_sort_mode_selected(self, index: int) -> None:
        self._sort_mode = _SORT_MODES[index][0]
        self.sort_mode_changed.emit(self._sort_mode)
        self._render()

    def _on_favorites_filter_toggled(self, checked: bool) -> None:
        self._favorites_only = checked
        self._refresh_favorites_button_icon()
        self._render()

    def _refresh_favorites_button_icon(self) -> None:
        color = theme.SURFACE if self._favorites_button.isChecked() else theme.INK_SOFT
        self._favorites_button.setIcon(heart_icon(color, size=13, filled=True))

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

        used = sorted({r.category for r in self._recipes if r.category})
        known = [c for c in self._category_order if c in used]
        new_ones = [c for c in used if c not in self._category_order]
        self._category_order = known + new_ones
        has_uncategorized = any(not r.category for r in self._recipes)

        all_button = QPushButton(_ALL_CATEGORIES)
        all_button.setProperty("variant", "pill")
        all_button.setCheckable(True)
        all_button.setChecked(previous == _ALL_CATEGORIES)
        all_button.clicked.connect(self._render)
        self._filter_group.addButton(all_button)
        self._filter_row.addWidget(all_button)

        for category in self._category_order:
            button = _DraggableCategoryButton(category)
            button.setProperty("variant", "pill")
            button.setCheckable(True)
            button.setChecked(category == previous)
            button.clicked.connect(self._render)
            button.reorder_requested.connect(self._on_category_reordered)
            self._filter_group.addButton(button)
            self._filter_row.addWidget(button)

        if has_uncategorized:
            none_button = QPushButton(_NO_CATEGORY)
            none_button.setProperty("variant", "pill")
            none_button.setCheckable(True)
            none_button.setChecked(previous == _NO_CATEGORY)
            none_button.clicked.connect(self._render)
            self._filter_group.addButton(none_button)
            self._filter_row.addWidget(none_button)

        self._filter_row.addStretch(1)

        if self._filter_group.checkedButton() is None and self._filter_group.buttons():
            self._filter_group.buttons()[0].setChecked(True)

    def _on_category_reordered(self, dragged: str, target: str) -> None:
        if dragged not in self._category_order or target not in self._category_order:
            return
        order = [c for c in self._category_order if c != dragged]
        order.insert(order.index(target), dragged)
        self._category_order = order
        self.category_order_changed.emit(list(order))
        self._refresh_category_filter()
        self._render()

    def _active_category(self) -> str:
        checked = self._filter_group.checkedButton()
        return checked.text() if checked else _ALL_CATEGORIES

    def _sorted_recipes(self) -> list[Recipe]:
        if self._sort_mode == "rating_desc":
            return sorted(self._recipes, key=lambda r: (r.rating is None, -(r.rating or 0)))
        if self._sort_mode == "rating_asc":
            return sorted(self._recipes, key=lambda r: (r.rating is None, r.rating or 0))
        return self._recipes  # "manual" : déjà dans l'ordre personnalisé (sort_order)

    def _render(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        ordered = self._sorted_recipes()
        selected = self._active_category()
        if selected == _ALL_CATEGORIES:
            visible = ordered
        elif selected == _NO_CATEGORY:
            visible = [r for r in ordered if not r.category]
        else:
            visible = [r for r in ordered if r.category == selected]

        if self._favorites_only:
            visible = [r for r in visible if r.is_favorite]

        if not visible:
            self._grid.addWidget(self._empty_widget, 0, 0, 1, max(self._columns, 1))
            self._empty_widget.show()
            return

        self._empty_widget.hide()
        draggable = self._sort_mode == "manual"
        for index, recipe in enumerate(visible):
            card = _RecipeCard(recipe, draggable=draggable)
            card.clicked.connect(self.recipe_selected.emit)
            card.favorite_toggled.connect(self._on_card_favorite_toggled)
            card.reorder_requested.connect(self._on_cards_reordered)
            row, col = divmod(index, self._columns)
            self._grid.addWidget(card, row, col)

    def _on_card_favorite_toggled(self, recipe_id: str, is_favorite: bool) -> None:
        self._recipes = [
            r.model_copy(update={"is_favorite": is_favorite}) if r.id == recipe_id else r
            for r in self._recipes
        ]
        self.favorite_toggle_requested.emit(recipe_id, is_favorite)

    def _on_cards_reordered(self, dragged_id: str, target_id: str) -> None:
        ids = [r.id for r in self._recipes]
        if dragged_id not in ids or target_id not in ids:
            return
        ids.remove(dragged_id)
        ids.insert(ids.index(target_id), dragged_id)
        by_id = {r.id: r for r in self._recipes}
        self._recipes = [by_id[i] for i in ids]
        self.reorder_requested.emit(ids)
        self._render()

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

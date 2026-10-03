"""Affichage en lecture seule d'une recette de la base locale."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from desktop import theme
from desktop.video_player import VideoPlayer
from desktop.widgets import HeartToggle, StarRating
from engine.models import Recipe

_BODY_MAX_WIDTH = 1200
_STEP_BADGE = 34
# Les reels sont filmés au format téléphone (portrait, 9:16) : la photo/
# vidéo de couverture suit ce ratio plutôt qu'un cadre large et bas, sans
# quoi une vidéo portrait ne remplit qu'une mince bande verticale au
# milieu d'un cadre très majoritairement vide. La largeur (donc la
# hauteur, qui en découle par ce ratio) grandit avec la fenêtre, jusqu'à
# ce maximum.
_HERO_ASPECT_RATIO = 16 / 9  # hauteur / largeur
_HERO_MAX_WIDTH = 480
_HERO_MIN_WIDTH = 320
_MAIN_SPACING = 40
# Largeur minimale garantie à la colonne ingrédients/étapes, pour qu'elle
# ne soit jamais écrasée par la vidéo quand la fenêtre est étroite :
# la vidéo rétrécit en premier (jusqu'à _HERO_MIN_WIDTH) plutôt que
# l'inverse, car on peut déjà l'agrandir via le bouton "Agrandir".
_RIGHT_MIN_WIDTH = 480


class RecipeDetailView(QWidget):
    edit_requested = Signal(str)  # recipe id
    delete_requested = Signal(str)  # recipe id
    favorite_toggled = Signal(str, bool)  # recipe id, is_favorite
    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipe_id: str | None = None

        self._heart_button = HeartToggle(overlay=False)
        self._heart_button.toggled.connect(self._on_favorite_toggled)

        # Volontairement seul à droite : le réflexe (comme pour fermer une
        # fenêtre) est d'aller cliquer en haut à droite. Modifier/
        # Supprimer sont en bas à gauche de la fenêtre (barre persistante,
        # voir plus bas), loin de ce réflexe de fermeture.
        close_button = QPushButton("✕")
        close_button.setProperty("variant", "ghost")
        close_button.setFixedSize(36, 36)
        close_button.setStyleSheet("font-size: 16px;")
        close_button.setToolTip("Retour à mes recettes")
        close_button.clicked.connect(self.back_requested.emit)

        header = QHBoxLayout()
        header.addWidget(self._heart_button)
        header.addStretch(1)
        header.addWidget(close_button)

        edit_button = QPushButton("Modifier")
        edit_button.setProperty("variant", "secondary")
        edit_button.clicked.connect(lambda: self.edit_requested.emit(self._recipe_id))
        delete_button = QPushButton("Supprimer")
        delete_button.setProperty("variant", "danger-ghost")
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._recipe_id))

        # Barre persistante en bas à gauche de la *fenêtre* (hors de la
        # zone de défilement) : reste accessible sans avoir à remonter en
        # haut de la fiche, quelle que soit la longueur de la recette.
        footer = QHBoxLayout()
        footer.setContentsMargins(32, 14, 32, 14)
        footer.setSpacing(12)
        footer.addWidget(edit_button)
        footer.addWidget(delete_button)
        footer.addStretch(1)
        self._footer_bar = QWidget()
        self._footer_bar.setProperty("role", "detail-footer")
        self._footer_bar.setAttribute(Qt.WA_StyledBackground, True)
        self._footer_bar.setStyleSheet(
            f"QWidget[role='detail-footer'] {{ background: {theme.SURFACE}; "
            f"border-top: 1px solid {theme.LINE}; }}"
        )
        self._footer_bar.setLayout(footer)

        self._current_recipe: Recipe | None = None
        self._hero_label = QLabel()
        self._hero_label.setAlignment(Qt.AlignCenter)

        self._video_player = VideoPlayer()

        # La photo statique et le lecteur vidéo occupent le même
        # emplacement : on n'affiche le second que si la vidéo source de
        # la recette a été conservée sur disque (recette extraite avant
        # cette fonctionnalité => photo seule).
        self._hero_stack = QStackedLayout()
        self._hero_stack.setContentsMargins(0, 0, 0, 0)
        self._hero_stack.addWidget(self._hero_label)
        self._hero_stack.addWidget(self._video_player)
        self._hero_container = QWidget()
        self._hero_container.setLayout(self._hero_stack)

        # Positionné à la main par-dessus la photo/vidéo (même procédé que
        # le cœur favori sur les cartes de l'accueil) plutôt que dans le
        # QStackedLayout, pour rester visible quel que soit le widget
        # affiché (photo ou vidéo).
        self._expand_button = QPushButton("Agrandir", parent=self._hero_container)
        self._expand_button.setStyleSheet(
            "background: rgba(0, 0, 0, 160); color: white; border: none; "
            "border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 600;"
        )
        self._expand_button.clicked.connect(self._open_fullscreen)
        self._expand_button.adjustSize()

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

        self._rating_widget = StarRating(editable=False)

        self._calories_badge = QLabel()
        self._calories_badge.setStyleSheet(
            f"background:{theme.ACCENT_TINT}; color:{theme.ACCENT_DEEP}; "
            "border-radius:10px; padding:6px 12px; font-size:13px; font-weight:700;"
        )
        self._calories_badge.hide()

        meta_row = QHBoxLayout()
        meta_row.setSpacing(12)
        meta_row.addWidget(self._category_pill)
        meta_row.addWidget(self._servings_label)
        meta_row.addStretch(1)

        rating_row = QHBoxLayout()
        rating_row.setSpacing(14)
        rating_row.addWidget(self._rating_widget)
        rating_row.addWidget(self._calories_badge)
        rating_row.addStretch(1)

        title_block = QVBoxLayout()
        title_block.setSpacing(10)
        title_block.addWidget(self._source_link)
        title_block.addWidget(self._title_label)
        title_block.addLayout(meta_row)
        title_block.addLayout(rating_row)

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

        # Format téléphone assumé jusqu'au bout : la vidéo/photo reste à
        # gauche, haute et étroite comme un téléphone, et ingrédients/
        # étapes viennent à côté, à droite. Le titre passe au-dessus des
        # deux colonnes plutôt que sous la photo : une photo haute aurait
        # sinon repoussé le titre sous le pli, hors champ sans défiler.
        hero_only = QVBoxLayout()
        hero_only.addWidget(self._hero_container)
        hero_only.addStretch(1)
        self._hero_wrap = QWidget()
        self._hero_wrap.setLayout(hero_only)

        right_content = QVBoxLayout()
        right_content.setSpacing(28)
        right_content.addLayout(body_row)
        right_content.addWidget(self._notes_frame)
        right_content.addStretch(1)
        right_wrap = QWidget()
        right_wrap.setLayout(right_content)

        main_row = QHBoxLayout()
        main_row.setSpacing(_MAIN_SPACING)
        main_row.addWidget(self._hero_wrap)
        main_row.addWidget(right_wrap, 1)

        content_col = QVBoxLayout()
        content_col.setSpacing(24)
        content_col.addLayout(title_block)
        content_col.addLayout(main_row)
        self._body_wrap = QWidget()
        self._body_wrap.setLayout(content_col)

        body_row_centered = QHBoxLayout()
        body_row_centered.addStretch(1)
        body_row_centered.addWidget(self._body_wrap)
        body_row_centered.addStretch(1)

        scroll_body = QWidget()
        scroll_layout = QVBoxLayout(scroll_body)
        scroll_layout.setContentsMargins(32, 24, 32, 32)
        scroll_layout.setSpacing(28)
        scroll_layout.addLayout(header)
        scroll_layout.addLayout(body_row_centered)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(scroll_body)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll, 1)
        outer.addWidget(self._footer_bar)

    def load_recipe(self, recipe: Recipe) -> None:
        self._video_player.stop()
        self._recipe_id = recipe.id
        self._current_recipe = recipe
        self._title_label.setText(recipe.title)
        self._update_widths()

        video_path = Path(recipe.video_path) if recipe.video_path else None
        if video_path and video_path.exists():
            self._video_player.load(str(video_path))
            self._hero_stack.setCurrentWidget(self._video_player)
        else:
            self._hero_stack.setCurrentWidget(self._hero_label)

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

        self._rating_widget.set_rating(recipe.rating)
        self._calories_badge.setText(_calories_html(recipe))
        self._calories_badge.setVisible(bool(recipe.calories))
        self._heart_button.blockSignals(True)
        self._heart_button.setChecked(recipe.is_favorite)
        self._heart_button.blockSignals(False)

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

    def stop_video(self) -> None:
        """Coupe la lecture en quittant la fiche détail (navigation ou
        passage en mode édition), pour ne pas laisser le son continuer en
        arrière-plan."""
        self._video_player.stop()

    def _open_fullscreen(self) -> None:
        recipe = self._current_recipe
        if recipe is None:
            return

        screen = self.screen()
        available = screen.availableGeometry() if screen else QSize(1280, 800)
        max_height = round(available.height() * 0.9)
        max_width = round(available.width() * 0.9)
        height = max_height
        width = round(height / _HERO_ASPECT_RATIO)
        if width > max_width:
            width = max_width
            height = round(width * _HERO_ASPECT_RATIO)

        dialog = QDialog(self)
        dialog.setWindowTitle(recipe.title)
        dialog.resize(width, height)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        video_path = Path(recipe.video_path) if recipe.video_path else None
        if video_path and video_path.exists():
            # Un second lecteur dédié à la fenêtre agrandie plutôt que de
            # déplacer le lecteur existant hors du QStackedLayout qui le
            # gère : plus simple et plus robuste. On met en pause le petit
            # lecteur pour ne pas entendre le son des deux à la fois.
            self._video_player.pause()
            big_player = VideoPlayer()
            layout.addWidget(big_player)
            big_player.load(str(video_path))
            dialog.exec()
            big_player.stop()
        else:
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setPixmap(_hero_pixmap(recipe, QSize(width, height)))
            layout.addWidget(label)
            dialog.exec()

    def _open_source(self, url: str) -> None:
        QDesktopServices.openUrl(url)

    def _on_favorite_toggled(self, checked: bool) -> None:
        if self._recipe_id is not None:
            self.favorite_toggled.emit(self._recipe_id, checked)

    def resizeEvent(self, event) -> None:  # noqa: N802 (nom imposé par Qt)
        super().resizeEvent(event)
        self._update_widths()

    def _update_widths(self) -> None:
        # Le mécanisme habituel de Qt (stretch de part et d'autre d'un
        # widget capé par une largeur maximale) ne se déclenche pas de
        # façon fiable à l'intérieur d'une QScrollArea ici : on calcule
        # donc explicitement la largeur de chaque bloc à chaque
        # redimensionnement plutôt que de compter sur les stretch factors.
        floor = _HERO_MIN_WIDTH + _MAIN_SPACING + _RIGHT_MIN_WIDTH
        available = max(self.width() - 80, floor)
        total_width = min(available, _BODY_MAX_WIDTH)
        hero_width = min(
            _HERO_MAX_WIDTH,
            max(_HERO_MIN_WIDTH, total_width - _MAIN_SPACING - _RIGHT_MIN_WIDTH),
        )
        hero_height = round(hero_width * _HERO_ASPECT_RATIO)
        self._hero_wrap.setFixedWidth(hero_width)
        self._hero_container.setFixedSize(hero_width, hero_height)
        self._expand_button.move(
            hero_width - self._expand_button.width() - 10, 10
        )
        self._body_wrap.setFixedWidth(total_width)
        self._refresh_hero(QSize(hero_width, hero_height))

    def _refresh_hero(self, size: QSize) -> None:
        if self._current_recipe is None:
            return
        self._hero_label.setPixmap(_hero_pixmap(self._current_recipe, size))


_CALORIES_BASIS_LABELS = {"per_serving": " / portion", "total": " au total"}
_CALORIES_SOURCE_LABELS = {
    "stated": "indiqué dans la vidéo",
    "estimated": "estimation",
    "manual": "saisie manuelle",
}


def _calories_html(recipe: Recipe) -> str:
    if not recipe.calories:
        return ""
    basis = _CALORIES_BASIS_LABELS.get(recipe.calories_basis, "")
    html = f"{recipe.calories} kcal{basis}"
    source = _CALORIES_SOURCE_LABELS.get(recipe.calories_source)
    if source:
        html += (
            f'<span style="color:{theme.ACCENT_DEEP}; font-weight:400; font-size:11px;">'
            f" · {source}</span>"
        )
    return html


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

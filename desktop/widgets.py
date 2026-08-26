"""Petits widgets réutilisés par plusieurs écrans."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from desktop import theme

_STAR_COUNT = 10
_HEART_FILLED = "#D1483D"
_HEART_EMPTY = "#FFFFFF"


class StarRating(QWidget):
    """Ligne de 10 étoiles cliquables (note sur 10).

    En lecture seule (`editable=False`), affiche simplement la note déjà
    enregistrée — utilisé sur la fiche détail, qui ne modifie rien.
    """

    rating_changed = Signal(int)  # 0 = pas de note

    def __init__(self, editable: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editable = editable
        self._rating = 0
        self._buttons: list[QPushButton] = []

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(1)
        for i in range(1, _STAR_COUNT + 1):
            button = QPushButton("☆")
            button.setFlat(True)
            button.setEnabled(editable)
            button.setFixedSize(20, 22)
            if editable:
                button.setCursor(Qt.PointingHandCursor)
                button.clicked.connect(lambda _checked=False, value=i: self._on_star_clicked(value))
            row.addWidget(button)
            self._buttons.append(button)

        self._label = QLabel()
        self._label.setProperty("role", "muted")
        row.addSpacing(6)
        row.addWidget(self._label)
        row.addStretch(1)

        self.set_rating(0)

    def _on_star_clicked(self, value: int) -> None:
        # Recliquer sur la dernière étoile pleine efface la note.
        self.set_rating(0 if value == self._rating else value)
        self.rating_changed.emit(self._rating)

    def set_rating(self, rating: int | None) -> None:
        self._rating = max(0, min(_STAR_COUNT, rating or 0))
        for index, button in enumerate(self._buttons, start=1):
            filled = index <= self._rating
            button.setText("★" if filled else "☆")
            color = theme.ACCENT if filled else theme.LINE
            button.setStyleSheet(
                f"border: none; background: transparent; font-size: 17px; color: {color};"
            )
        self._label.setText(f"{self._rating}/10" if self._rating else "Pas encore noté")

    def rating(self) -> int | None:
        return self._rating or None


class HeartToggle(QPushButton):
    """Bouton cœur (favori), dessiné en vectoriel plutôt qu'avec un
    caractère Unicode (♥/♡) : ce dernier ne s'affichait pas de façon
    fiable selon la police du système (constaté sous Windows, où le
    bouton apparaissait comme un simple rond vide, sans cœur visible).

    `overlay=True` (par défaut) : fond sombre semi-transparent, pensé
    pour être superposé sur une photo (cartes de l'accueil). `overlay=
    False` : fond neutre, pour un usage dans une barre d'outils normale
    (en-tête de la fiche détail).
    """

    def __init__(self, overlay: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._overlay = overlay
        self._color = _HEART_EMPTY
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(30, 30)
        self.toggled.connect(lambda _checked: self._refresh())
        self._refresh()

    def _refresh(self) -> None:
        filled = self.isChecked()
        if self._overlay:
            background = "rgba(35, 44, 30, 0.38)"
            self._color = _HEART_FILLED if filled else _HEART_EMPTY
        else:
            background = theme.SURFACE
            self._color = _HEART_FILLED if filled else theme.INK_FAINT
        self.setStyleSheet(
            f"border: 1px solid {theme.LINE}; border-radius: 15px; background: {background};"
        )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (nom imposé par Qt)
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        margin = self.width() * 0.27
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)
        _draw_heart(painter, rect, filled=self.isChecked(), color=QColor(self._color))


def _draw_heart(painter: QPainter, rect: QRectF, filled: bool, color: QColor) -> None:
    """Cœur composé de deux lobes (cercles) et d'une pointe (triangle),
    réunis en un seul chemin — plus fiable qu'un glyphe de police."""

    w, h = rect.width(), rect.height()
    lobe_radius = w * 0.28
    lobe_y = rect.top() + h * 0.32
    left_x = rect.left() + w * 0.30
    right_x = rect.left() + w * 0.70

    path = QPainterPath()
    path.addEllipse(QPointF(left_x, lobe_y), lobe_radius, lobe_radius)
    right_lobe = QPainterPath()
    right_lobe.addEllipse(QPointF(right_x, lobe_y), lobe_radius, lobe_radius)
    path = path.united(right_lobe)

    tip = QPainterPath()
    tip.addPolygon(
        QPolygonF(
            [
                QPointF(rect.left() + w * 0.04, lobe_y),
                QPointF(rect.left() + w * 0.5, rect.top() + h * 0.97),
                QPointF(rect.left() + w * 0.96, lobe_y),
            ]
        )
    )
    path = path.united(tip)

    if filled:
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
    else:
        painter.setPen(QPen(color, max(1.6, w * 0.12)))
        painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)

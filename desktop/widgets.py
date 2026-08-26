"""Petits widgets réutilisés par plusieurs écrans."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
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
        margin = self.width() * 0.20
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)
        _draw_heart(painter, rect, filled=self.isChecked(), color=QColor(self._color))


# Cœur dessiné sur une grille 24x24 (points de contrôle d'un tracé
# vectoriel classique), mis à l'échelle du rectangle cible à l'usage.
_HEART_START_24 = (12.0, 21.0)
_HEART_CURVES_24 = (
    ((12.0, 21.0), (5.3, 16.65), (2.7, 12.45)),
    ((1.1, 9.9), (1.9, 6.5), (4.8, 5.1)),
    ((7.0, 4.05), (9.3, 4.8), (12.0, 7.5)),
    ((14.7, 4.8), (17.0, 4.05), (19.2, 5.1)),
    ((22.1, 6.5), (22.9, 9.9), (21.3, 12.45)),
    ((18.7, 16.65), (12.0, 21.0), (12.0, 21.0)),
)
# Une bouchée croquée en haut à droite du creux — le cœur devient liké
# une fois « croqué », comme on croquerait dans la recette elle-même.
_BITE_CENTER_24 = (15.5, 4.6)
_BITE_RADIUS_24 = 2.7


def _heart_path(rect: QRectF) -> QPainterPath:
    scale_x, scale_y = rect.width() / 24.0, rect.height() / 24.0

    def point(x: float, y: float) -> QPointF:
        return QPointF(rect.left() + x * scale_x, rect.top() + y * scale_y)

    path = QPainterPath()
    path.moveTo(point(*_HEART_START_24))
    for control1, control2, end in _HEART_CURVES_24:
        path.cubicTo(point(*control1), point(*control2), point(*end))
    path.closeSubpath()
    return path


def _draw_heart(painter: QPainter, rect: QRectF, filled: bool, color: QColor) -> None:
    """Cœur plein avec une bouchée croquée en haut quand il est liké ;
    simple contour, intact, sinon."""

    heart = _heart_path(rect)

    if filled:
        scale_x, scale_y = rect.width() / 24.0, rect.height() / 24.0
        bite_center = QPointF(
            rect.left() + _BITE_CENTER_24[0] * scale_x,
            rect.top() + _BITE_CENTER_24[1] * scale_y,
        )
        bite = QPainterPath()
        bite.addEllipse(bite_center, _BITE_RADIUS_24 * scale_x, _BITE_RADIUS_24 * scale_y)
        heart = heart.subtracted(bite)

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
    else:
        painter.setPen(QPen(color, max(1.6, rect.width() * 0.1)))
        painter.setBrush(Qt.NoBrush)
    painter.drawPath(heart)


def heart_icon(color: str, size: int = 14, filled: bool = False) -> QIcon:
    """Petite icône cœur (même tracé vectoriel que `HeartToggle`), pour un
    usage ailleurs qu'un bouton dédié — ex. le filtre « Favoris » de
    l'accueil — sans dépendre d'un glyphe Unicode."""

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    margin = size * 0.06
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    _draw_heart(painter, rect, filled=filled, color=QColor(color))
    painter.end()
    return QIcon(pixmap)

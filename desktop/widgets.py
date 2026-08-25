"""Petits widgets réutilisés par plusieurs écrans."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
    """Bouton cœur (favori).

    `overlay=True` (par défaut) : fond sombre semi-transparent, pensé
    pour être superposé sur une photo (cartes de l'accueil). `overlay=
    False` : fond neutre, pour un usage dans une barre d'outils normale
    (en-tête de la fiche détail).
    """

    def __init__(self, overlay: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._overlay = overlay
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(30, 30)
        self.toggled.connect(lambda _checked: self._refresh())
        self._refresh()

    def _refresh(self) -> None:
        filled = self.isChecked()
        self.setText("♥" if filled else "♡")
        if self._overlay:
            background = "rgba(35, 44, 30, 0.38)"
            color = _HEART_FILLED if filled else _HEART_EMPTY
        else:
            background = theme.SURFACE
            color = _HEART_FILLED if filled else theme.INK_FAINT
        self.setStyleSheet(
            f"border: 1px solid {theme.LINE}; border-radius: 15px; "
            f"font-size: 15px; background: {background}; color: {color};"
        )

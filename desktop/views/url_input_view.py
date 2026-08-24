"""Écran d'accueil pour une nouvelle recette : coller un lien Instagram,
ou basculer directement en saisie manuelle."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class UrlInputView(QWidget):
    extract_requested = Signal(str)
    manual_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://www.instagram.com/reel/...")
        self._extract_button = QPushButton("Extraire la recette")
        self._manual_button = QPushButton("Saisir une recette manuellement")
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indéterminé
        self._progress_bar.hide()

        self._extract_button.clicked.connect(self._on_extract_clicked)
        self._manual_button.clicked.connect(self.manual_requested.emit)
        self._url_edit.returnPressed.connect(self._on_extract_clicked)

        title = QLabel("Nouvelle recette")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")

        url_row = QHBoxLayout()
        url_row.addWidget(self._url_edit)
        url_row.addWidget(self._extract_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(url_row)
        layout.addWidget(self._progress_bar)
        layout.addWidget(self._status_label)
        layout.addStretch(1)
        layout.addWidget(self._manual_button)

    def _on_extract_clicked(self) -> None:
        url = self._url_edit.text().strip()
        if url:
            self.extract_requested.emit(url)

    def set_busy(self, busy: bool, status_text: str = "") -> None:
        self._extract_button.setEnabled(not busy)
        self._manual_button.setEnabled(not busy)
        self._url_edit.setEnabled(not busy)
        self._progress_bar.setVisible(busy)
        self._status_label.setText(status_text)

    def reset(self) -> None:
        self._url_edit.clear()
        self.set_busy(False)

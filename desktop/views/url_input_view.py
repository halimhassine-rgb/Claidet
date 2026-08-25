"""Écran d'accueil pour une nouvelle recette : coller un lien Instagram,
ou basculer directement en saisie manuelle."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
        self._url_edit.setMinimumHeight(38)

        self._extract_button = QPushButton("Extraire la recette")
        self._extract_button.setProperty("variant", "primary")
        self._manual_button = QPushButton("Saisir une recette manuellement")
        self._manual_button.setProperty("variant", "secondary")

        self._status_label = QLabel("")
        self._status_label.setProperty("role", "muted")
        self._status_label.setWordWrap(True)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indéterminé
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.hide()

        self._extract_button.clicked.connect(self._on_extract_clicked)
        self._manual_button.clicked.connect(self.manual_requested.emit)
        self._url_edit.returnPressed.connect(self._on_extract_clicked)

        title = QLabel("Nouvelle recette")
        title.setProperty("role", "detail-title")
        subtitle = QLabel("Collez le lien d'un reel de cuisine Instagram.")
        subtitle.setProperty("role", "muted")

        url_row = QHBoxLayout()
        url_row.setSpacing(10)
        url_row.addWidget(self._url_edit, 1)
        url_row.addWidget(self._extract_button)

        form = QVBoxLayout()
        form.setSpacing(18)
        form.addWidget(title)
        form.addWidget(subtitle)
        form.addLayout(url_row)
        form.addWidget(self._progress_bar)
        form.addWidget(self._status_label)
        form.addWidget(self._manual_button, 0, Qt.AlignLeft)

        form_wrap = QWidget()
        form_wrap.setLayout(form)
        form_wrap.setMaximumWidth(560)

        centered = QHBoxLayout()
        centered.addStretch(1)
        centered.addWidget(form_wrap, 1)
        centered.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.addLayout(centered)
        layout.addStretch(1)

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

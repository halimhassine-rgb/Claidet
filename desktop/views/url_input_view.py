"""Écran d'accueil pour une nouvelle recette : coller un lien Instagram,
ou basculer directement en saisie manuelle."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class UrlInputView(QWidget):
    extract_requested = Signal(str, bool)  # url, use_ai
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

        self._use_ai_checkbox = QCheckBox("Utiliser Claude (IA) pour cette extraction")
        ai_hint = QLabel(
            "Décochée : extraction gratuite par règles simples, à vérifier — "
            "vous pourrez relancer avec Claude ensuite si besoin."
        )
        ai_hint.setProperty("role", "faint")
        ai_hint.setWordWrap(True)

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

        ai_option = QVBoxLayout()
        ai_option.setSpacing(2)
        ai_option.addWidget(self._use_ai_checkbox)
        ai_option.addWidget(ai_hint)

        form = QVBoxLayout()
        form.setSpacing(18)
        form.addWidget(title)
        form.addWidget(subtitle)
        form.addLayout(url_row)
        form.addLayout(ai_option)
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
            self.extract_requested.emit(url, self._use_ai_checkbox.isChecked())

    def set_busy(self, busy: bool, status_text: str = "") -> None:
        self._extract_button.setEnabled(not busy)
        self._manual_button.setEnabled(not busy)
        self._url_edit.setEnabled(not busy)
        self._use_ai_checkbox.setEnabled(not busy)
        self._progress_bar.setVisible(busy)
        self._status_label.setText(status_text)

    def start_for_retry(self, url: str) -> None:
        """Pré-remplit le lien et relance directement avec Claude — utilisé
        quand on revient depuis l'écran de relecture après une extraction
        sans IA jugée insuffisante."""
        self._url_edit.setText(url)
        self._use_ai_checkbox.setChecked(True)
        self.extract_requested.emit(url, True)

    def reset(self) -> None:
        self._url_edit.clear()
        self._use_ai_checkbox.setChecked(False)
        self.set_busy(False)

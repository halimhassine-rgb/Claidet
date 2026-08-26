"""Lecteur vidéo simple (lecture/pause + défilement) pour la vidéo source
d'une recette, affiché à la place de la photo de couverture statique sur
la fiche détail."""

from __future__ import annotations

from PySide6.QtCore import QUrl, Qt
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from desktop import theme


class VideoPlayer(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet(f"background: {theme.INK};")
        # Sans ça, QVideoWidget impose sa taille par défaut (640x480) et
        # refuse de se réduire à l'espace réellement disponible dans la
        # fiche détail (280 px de haut).
        self._video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._video_widget.setMinimumSize(1, 1)

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_widget)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)

        self._play_button = QPushButton("▶")
        self._play_button.setProperty("variant", "secondary")
        self._play_button.setFixedWidth(44)
        self._play_button.clicked.connect(self._toggle_play)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{ background: {theme.LINE}; height: 4px; border-radius: 2px; }}
            QSlider::handle:horizontal {{
                background: {theme.ACCENT}; width: 14px; height: 14px;
                margin: -5px 0; border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{ background: {theme.ACCENT}; border-radius: 2px; }}
            """
        )
        self._slider.sliderMoved.connect(self._player.setPosition)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(self._play_button)
        controls.addWidget(self._slider, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._video_widget, 1)
        layout.addLayout(controls)

    def load(self, path: str) -> None:
        self._player.setSource(QUrl.fromLocalFile(path))

    def stop(self) -> None:
        self._player.stop()

    def _toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self._play_button.setText("⏸" if state == QMediaPlayer.PlayingState else "▶")

    def _on_duration_changed(self, duration: int) -> None:
        self._slider.setRange(0, duration)

    def _on_position_changed(self, position: int) -> None:
        if not self._slider.isSliderDown():
            self._slider.setValue(position)

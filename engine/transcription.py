"""Transcription de la piste audio en texte.

Interface `Transcriber` + implémentation par défaut sur faster-whisper
(local, pas d'appel réseau, tourne sur CPU). Le modèle de langue est
chargé une seule fois par instance et réutilisé entre extractions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from engine.exceptions import TranscriptionError


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> str: ...


class FasterWhisperTranscriber:
    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None  # chargement paresseux : coûteux, pas nécessaire aux tests

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:  # pragma: no cover
                raise TranscriptionError(
                    "faster-whisper n'est pas installé (extra 'engine' requis)."
                ) from exc
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        if not audio_path.exists():
            raise TranscriptionError(f"Fichier audio introuvable : {audio_path}")

        model = self._load_model()
        try:
            segments, _info = model.transcribe(str(audio_path))
            text = " ".join(segment.text.strip() for segment in segments)
        except Exception as exc:
            raise TranscriptionError(f"Échec de la transcription : {exc}") from exc

        return text.strip()

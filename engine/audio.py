"""Extraction de la piste audio d'une vidéo, via ffmpeg en sous-processus.

Pas de binding Python à ffmpeg (type ffmpeg-python) : un simple appel
`subprocess` est plus facile à auditer, à tester (on peut mocker
`subprocess.run`) et ne rajoute pas de dépendance native supplémentaire
en plus du binaire ffmpeg lui-même, qui est de toute façon requis sur la
machine de l'utilisateur.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from engine.exceptions import AudioExtractionError


def extract_audio(video_path: Path, dest_dir: Path) -> Path:
    """Extrait la piste audio en WAV mono 16 kHz (format attendu par
    faster-whisper) à côté du fichier vidéo."""

    dest_dir.mkdir(parents=True, exist_ok=True)
    audio_path = dest_dir / f"{video_path.stem}.wav"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise AudioExtractionError(
            "ffmpeg est introuvable sur le PATH. Installez-le pour utiliser "
            "l'extraction automatique."
        ) from exc

    if result.returncode != 0:
        raise AudioExtractionError(
            f"ffmpeg a échoué à extraire l'audio de {video_path.name} : "
            f"{result.stderr.strip()[-500:]}"
        )

    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise AudioExtractionError(
            f"Aucun fichier audio produit pour {video_path.name}."
        )

    return audio_path

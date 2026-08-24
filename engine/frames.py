"""Extraction d'images clés de la vidéo et choix de l'image de couverture.

Les recettes en reels affichent souvent le texte (ingrédients, quantités)
incrusté à l'écran plutôt que dit à voix haute : ces images clés sont
envoyées au modèle de reconstruction (`engine.recipe_builder`) en
complément de la transcription audio.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from engine.exceptions import FrameExtractionError


def _ffprobe_duration_seconds(video_path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise FrameExtractionError("ffprobe est introuvable sur le PATH.") from exc

    if result.returncode != 0 or not result.stdout.strip():
        raise FrameExtractionError(
            f"Impossible de déterminer la durée de {video_path.name} : "
            f"{result.stderr.strip()[-300:]}"
        )

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise FrameExtractionError(
            f"Durée ffprobe invalide pour {video_path.name}."
        ) from exc


def _grab_frame(video_path: Path, ts: float, out_path: Path) -> bool:
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{ts:.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(out_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise FrameExtractionError("ffmpeg est introuvable sur le PATH.") from exc

    return result.returncode == 0 and out_path.exists()


def extract_key_frames(video_path: Path, dest_dir: Path, max_frames: int = 6) -> list[Path]:
    """Extrait `max_frames` images réparties uniformément sur la vidéo.

    Un échantillonnage uniforme est préféré à une détection de scène :
    les reels de recette sont courts (souvent < 60 s) et changent de plan
    fréquemment sans forcément de "coupure" nette, donc la détection de
    scène rate souvent les images où le texte incrusté est affiché. Un
    échantillonnage régulier est plus prévisible et suffisant vu que le
    nombre d'images reste faible.
    """

    dest_dir.mkdir(parents=True, exist_ok=True)
    duration = _ffprobe_duration_seconds(video_path)
    if duration <= 0:
        raise FrameExtractionError(f"Durée nulle pour {video_path.name}.")

    count = max(1, max_frames)
    # On évite le tout premier et le tout dernier instant (souvent un
    # écran de transition noir) en resserrant légèrement la fenêtre.
    margin = duration * 0.05
    span = max(duration - 2 * margin, 0.1)
    timestamps = [margin + span * i / max(count - 1, 1) for i in range(count)] if count > 1 else [duration / 2]

    frame_paths: list[Path] = []
    for index, ts in enumerate(timestamps):
        out_path = dest_dir / f"{video_path.stem}_frame_{index:02d}.jpg"
        # Un timestamp calculé peut tomber après la dernière frame
        # décodable (arrondis de durée/fps) : on retente un peu plus tôt
        # avant d'abandonner cette image.
        for attempt_ts in (ts, max(ts - 0.5, 0.0)):
            if _grab_frame(video_path, attempt_ts, out_path):
                frame_paths.append(out_path)
                break

    if not frame_paths:
        raise FrameExtractionError(
            f"Aucune image clé n'a pu être extraite de {video_path.name}."
        )

    return frame_paths


def pick_cover_image(frame_paths: list[Path], thumbnail_path: Path | None) -> Path | None:
    """Choisit l'image de couverture : la miniature Instagram si présente
    (généralement la plus représentative, choisie par l'auteur du post),
    sinon la première image clé extraite."""

    if thumbnail_path is not None and thumbnail_path.exists():
        return thumbnail_path
    if frame_paths:
        return frame_paths[0]
    return None

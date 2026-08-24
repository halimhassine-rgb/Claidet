"""Téléchargement de la vidéo Instagram source.

Passe par une interface (`VideoDownloader`) plutôt que d'appeler yt-dlp
en dur dans le pipeline : ça permet de tester l'orchestration sans réseau
et de remplacer le téléchargeur si Instagram change de mécanisme
d'accès, sans toucher au reste du moteur.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from engine.exceptions import DownloadError


@dataclass
class DownloadedVideo:
    video_path: Path
    title: str | None
    # La légende du post Instagram contient très souvent la recette en
    # texte (ingrédients, étapes) : c'est un signal fort pour la
    # reconstruction, en plus de la transcription audio.
    caption: str | None
    thumbnail_path: Path | None


class VideoDownloader(Protocol):
    def download(self, url: str, dest_dir: Path) -> DownloadedVideo: ...


class YtDlpDownloader:
    """Implémentation par défaut, basée sur yt-dlp."""

    def download(self, url: str, dest_dir: Path) -> DownloadedVideo:
        try:
            import yt_dlp
        except ImportError as exc:  # pragma: no cover
            raise DownloadError(
                "yt-dlp n'est pas installé (extra 'engine' requis)."
            ) from exc

        dest_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(dest_dir / "%(id)s.%(ext)s")
        options = {
            "outtmpl": outtmpl,
            "format": "mp4/bestvideo+bestaudio/best",
            "writethumbnail": True,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = Path(ydl.prepare_filename(info))
        except Exception as exc:
            raise DownloadError(f"Échec du téléchargement de la vidéo : {exc}") from exc

        if not video_path.exists():
            raise DownloadError(
                f"yt-dlp n'a produit aucun fichier vidéo pour {url!r}."
            )

        thumbnail_path = _find_thumbnail(dest_dir, video_path.stem)

        return DownloadedVideo(
            video_path=video_path,
            title=info.get("title"),
            caption=info.get("description"),
            thumbnail_path=thumbnail_path,
        )


def _find_thumbnail(dest_dir: Path, stem: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = dest_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None

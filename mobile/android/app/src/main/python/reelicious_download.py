"""Téléchargement de la vidéo Instagram source, exécuté sur le téléphone via
Chaquopy (Python embarqué dans l'appli Android).

Reprend volontairement la même logique que engine/downloader.py (version
bureau) : même bibliothèque (yt-dlp), mêmes options, même façon de
retrouver la miniature. Le format de retour est un simple dict (types
JSON-compatibles) plutôt qu'un objet, pour traverser proprement le pont
Java/Python de Chaquopy.
"""

import json
from pathlib import Path


def download(url: str, dest_dir: str) -> str:
    """Retourne un JSON (str) plutôt qu'un dict Python : évite toute
    ambiguïté de conversion de type au passage du pont Java/Python de
    Chaquopy, le code Kotlin se contente de parser une chaîne JSON comme
    n'importe quelle réponse réseau."""
    return json.dumps(_download(url, dest_dir))


def _download(url: str, dest_dir: str) -> dict:
    import yt_dlp

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    outtmpl = str(dest / "%(id)s.%(ext)s")
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
        raise RuntimeError(f"Échec du téléchargement de la vidéo : {exc}") from exc

    if not video_path.exists():
        raise RuntimeError(f"yt-dlp n'a produit aucun fichier vidéo pour {url!r}.")

    thumbnail_path = None
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = dest / f"{video_path.stem}{ext}"
        if candidate.exists():
            thumbnail_path = str(candidate)
            break

    return {
        "video_path": str(video_path),
        "title": info.get("title"),
        "caption": info.get("description"),
        "thumbnail_path": thumbnail_path,
    }

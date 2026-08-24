"""Configuration du moteur, chargée depuis l'environnement (`.env` inclus).

Un seul objet `EngineConfig`, sans aucun état global mutable : chaque
appelant (app de bureau, futur serveur, tests) construit le sien.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _default_data_dir() -> Path:
    return Path.home() / ".claidet"


@dataclass(frozen=True)
class EngineConfig:
    anthropic_api_key: str | None = None
    # Modèle Claude utilisé pour reconstruire la recette (texte + images).
    claude_model: str = "claude-sonnet-5"
    # Taille du modèle faster-whisper : tiny/base/small/medium/large-v3.
    # "small" est un bon compromis vitesse/qualité pour du français sur CPU.
    whisper_model_size: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    # Répertoire de travail : vidéos/audio/frames téléchargés, DB locale,
    # images de couverture persistées.
    data_dir: Path = _default_data_dir()
    # Nombre d'images clés candidates extraites de la vidéo pour capter le
    # texte incrusté (ingrédients affichés à l'écran, etc.).
    max_key_frames: int = 6

    @classmethod
    def from_env(cls) -> "EngineConfig":
        data_dir = Path(os.environ.get("CLAIDET_DATA_DIR", str(_default_data_dir())))
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            claude_model=os.environ.get("CLAIDET_CLAUDE_MODEL", "claude-sonnet-5"),
            whisper_model_size=os.environ.get("CLAIDET_WHISPER_SIZE", "small"),
            whisper_device=os.environ.get("CLAIDET_WHISPER_DEVICE", "cpu"),
            whisper_compute_type=os.environ.get("CLAIDET_WHISPER_COMPUTE", "int8"),
            data_dir=data_dir,
            max_key_frames=int(os.environ.get("CLAIDET_MAX_KEY_FRAMES", "6")),
        )

    @property
    def downloads_dir(self) -> Path:
        return self.data_dir / "downloads"

    @property
    def frames_dir(self) -> Path:
        return self.data_dir / "frames"

    @property
    def covers_dir(self) -> Path:
        return self.data_dir / "covers"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "claidet.db"

    def ensure_dirs(self) -> None:
        for d in (self.downloads_dir, self.frames_dir, self.covers_dir):
            d.mkdir(parents=True, exist_ok=True)

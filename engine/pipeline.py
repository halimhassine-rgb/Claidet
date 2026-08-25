"""Orchestration du pipeline d'extraction.

Principe directeur : une étape qui échoue ne doit pas nécessairement
faire échouer toute l'extraction. Le pipeline dégrade gracieusement et
renvoie toujours un `ExtractionResult` exploitable :

- SUCCESS   : recette complète reconstruite automatiquement.
- PARTIAL   : la reconstruction automatique a échoué (ou n'a pas pu être
              tentée), mais on a récupéré transcript/légende/images —
              l'UI pré-remplit l'écran de saisie manuelle avec ça.
- FAILED    : rien d'exploitable (typiquement le téléchargement a échoué).

C'est le seul point d'entrée que l'UI de bureau (et, demain, un serveur)
a besoin de connaître : `ExtractionPipeline(config).extract(url)`.
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from collections.abc import Callable
from pathlib import Path

from engine.audio import extract_audio
from engine.config import EngineConfig
from engine.downloader import DownloadedVideo, VideoDownloader, YtDlpDownloader
from engine.exceptions import (
    AudioExtractionError,
    DownloadError,
    FrameExtractionError,
    RecipeReconstructionError,
    TranscriptionError,
)
from engine.frames import extract_key_frames, pick_cover_image
from engine.models import ExtractionResult, ExtractionStatus, PipelineStage, Recipe
from engine.recipe_builder import ClaudeRecipeReconstructor, RecipeReconstructor
from engine.transcription import FasterWhisperTranscriber, Transcriber

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[PipelineStage], None]


class ExtractionPipeline:
    def __init__(
        self,
        config: EngineConfig,
        downloader: VideoDownloader | None = None,
        transcriber: Transcriber | None = None,
        reconstructor: RecipeReconstructor | None = None,
    ) -> None:
        self._config = config
        self._downloader = downloader or YtDlpDownloader()
        self._transcriber = transcriber or FasterWhisperTranscriber(
            model_size=config.whisper_model_size,
            device=config.whisper_device,
            compute_type=config.whisper_compute_type,
        )
        self._reconstructor = reconstructor or ClaudeRecipeReconstructor(
            api_key=config.anthropic_api_key, model=config.claude_model
        )

    def extract(
        self, url: str, on_progress: ProgressCallback | None = None
    ) -> ExtractionResult:
        def report(stage: PipelineStage) -> None:
            if on_progress is not None:
                on_progress(stage)

        self._config.ensure_dirs()
        # Un identifiant par extraction pour isoler les fichiers de cette
        # tentative dans downloads_dir/frames_dir (contrairement à l'audio,
        # ces fichiers doivent survivre à la fonction : l'appelant a besoin
        # des images clés et de la miniature après le `return`).
        extraction_id = uuid.uuid4().hex[:12]

        report(PipelineStage.DOWNLOAD)
        try:
            downloaded = self._downloader.download(
                url, self._config.downloads_dir / extraction_id
            )
        except DownloadError as exc:
            logger.warning("Téléchargement échoué pour %s : %s", url, exc)
            return _failed_result(url, PipelineStage.DOWNLOAD, str(exc))

        try:
            transcript = self._try_transcribe(downloaded, report)
            frame_paths = self._try_extract_frames(downloaded, extraction_id, report)
        finally:
            # La vidéo brute ne sert plus à rien une fois l'audio et les
            # images clés extraits ; elle est volumineuse, on la supprime.
            downloaded.video_path.unlink(missing_ok=True)

        cover_image_path = pick_cover_image(frame_paths, downloaded.thumbnail_path)

        return self._reconstruct(
            url=url,
            downloaded=downloaded,
            transcript=transcript,
            frame_paths=frame_paths,
            cover_image_path=cover_image_path,
            report=report,
        )

    def _try_transcribe(
        self, downloaded: DownloadedVideo, report: ProgressCallback
    ) -> str | None:
        report(PipelineStage.AUDIO_EXTRACTION)
        # L'audio n'est utile que le temps de la transcription : un
        # répertoire temporaire, nettoyé automatiquement, suffit.
        with tempfile.TemporaryDirectory(prefix="reelicious_audio_") as tmp:
            try:
                audio_path = extract_audio(downloaded.video_path, Path(tmp))
            except AudioExtractionError as exc:
                logger.warning("Extraction audio échouée : %s", exc)
                return None

            report(PipelineStage.TRANSCRIPTION)
            try:
                return self._transcriber.transcribe(audio_path) or None
            except TranscriptionError as exc:
                logger.warning("Transcription échouée : %s", exc)
                return None

    def _try_extract_frames(
        self, downloaded: DownloadedVideo, extraction_id: str, report: ProgressCallback
    ) -> list[Path]:
        report(PipelineStage.FRAME_EXTRACTION)
        try:
            return extract_key_frames(
                downloaded.video_path,
                self._config.frames_dir / extraction_id,
                max_frames=self._config.max_key_frames,
            )
        except FrameExtractionError as exc:
            logger.warning("Extraction d'images clés échouée : %s", exc)
            return []

    def _reconstruct(
        self,
        *,
        url: str,
        downloaded: DownloadedVideo,
        transcript: str | None,
        frame_paths: list[Path],
        cover_image_path: Path | None,
        report: ProgressCallback,
    ) -> ExtractionResult:
        has_raw_material = bool(transcript or downloaded.caption or frame_paths)

        report(PipelineStage.RECIPE_RECONSTRUCTION)
        if has_raw_material:
            try:
                recipe = self._reconstructor.reconstruct(
                    transcript=transcript,
                    caption=downloaded.caption,
                    frame_paths=frame_paths,
                    source_url=url,
                )
                recipe.cover_image_path = str(cover_image_path) if cover_image_path else None
                return ExtractionResult(
                    status=ExtractionStatus.SUCCESS,
                    recipe=recipe,
                    transcript=transcript,
                    caption=downloaded.caption,
                    frame_paths=[str(p) for p in frame_paths],
                )
            except RecipeReconstructionError as exc:
                logger.warning("Reconstruction de la recette échouée : %s", exc)
                error_message = str(exc)
        else:
            error_message = "Aucune donnée exploitable extraite de la vidéo."

        draft = _draft_recipe(url, downloaded, cover_image_path)
        status = ExtractionStatus.PARTIAL if has_raw_material else ExtractionStatus.FAILED
        return ExtractionResult(
            status=status,
            recipe=draft,
            transcript=transcript,
            caption=downloaded.caption,
            frame_paths=[str(p) for p in frame_paths],
            failed_stage=PipelineStage.RECIPE_RECONSTRUCTION,
            error_message=error_message,
        )


def _draft_recipe(
    url: str, downloaded: DownloadedVideo, cover_image_path: Path | None
) -> Recipe:
    return Recipe(
        source_url=url,
        title=downloaded.title or "Recette sans titre",
        notes=downloaded.caption,
        cover_image_path=str(cover_image_path) if cover_image_path else None,
        extraction_method="manual",
    )


def _failed_result(url: str, stage: PipelineStage, error_message: str) -> ExtractionResult:
    return ExtractionResult(
        status=ExtractionStatus.FAILED,
        recipe=Recipe(source_url=url, title="Recette sans titre", extraction_method="manual"),
        failed_stage=stage,
        error_message=error_message,
    )

"""Exceptions du moteur d'extraction.

Chaque étape du pipeline lève une sous-classe distincte pour que
`ExtractionPipeline` puisse rapporter précisément `failed_stage` sans
inspecter des messages d'erreur.
"""

from engine.models import PipelineStage


class EngineError(Exception):
    """Base de toutes les erreurs du moteur."""

    stage: PipelineStage

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DownloadError(EngineError):
    stage = PipelineStage.DOWNLOAD


class AudioExtractionError(EngineError):
    stage = PipelineStage.AUDIO_EXTRACTION


class FrameExtractionError(EngineError):
    stage = PipelineStage.FRAME_EXTRACTION


class TranscriptionError(EngineError):
    stage = PipelineStage.TRANSCRIPTION


class RecipeReconstructionError(EngineError):
    stage = PipelineStage.RECIPE_RECONSTRUCTION

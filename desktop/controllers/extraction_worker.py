"""Exécution de l'extraction dans un thread séparé.

Le pipeline fait des appels réseau et CPU potentiellement longs
(téléchargement, transcription, appel LLM) : il ne doit jamais tourner
sur le thread d'interface, sous peine de geler l'UI.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from engine.models import ExtractionResult, PipelineStage
from engine.pipeline import ExtractionPipeline

STAGE_LABELS: dict[PipelineStage, str] = {
    PipelineStage.DOWNLOAD: "Téléchargement de la vidéo…",
    PipelineStage.AUDIO_EXTRACTION: "Extraction de l'audio…",
    PipelineStage.FRAME_EXTRACTION: "Capture des images clés…",
    PipelineStage.TRANSCRIPTION: "Transcription de l'audio…",
    PipelineStage.RECIPE_RECONSTRUCTION: "Reconstruction de la recette…",
}


class ExtractionWorker(QThread):
    stage_changed = Signal(str)
    succeeded = Signal(ExtractionResult)
    crashed = Signal(str)

    def __init__(self, pipeline: ExtractionPipeline, url: str) -> None:
        super().__init__()
        self._pipeline = pipeline
        self._url = url

    def run(self) -> None:
        try:
            result = self._pipeline.extract(self._url, on_progress=self._on_progress)
        except Exception as exc:  # sécurité : le pipeline ne devrait normalement
            # jamais laisser fuir d'exception (voir engine.pipeline), mais on
            # ne veut surtout pas planter le thread UI si un cas nous échappe.
            self.crashed.emit(str(exc))
            return
        self.succeeded.emit(result)

    def _on_progress(self, stage: PipelineStage) -> None:
        self.stage_changed.emit(STAGE_LABELS.get(stage, stage.value))

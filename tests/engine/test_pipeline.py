import shutil
from pathlib import Path

from engine.config import EngineConfig
from engine.downloader import DownloadedVideo
from engine.exceptions import DownloadError, RecipeReconstructionError
from engine.models import ExtractionStatus, Ingredient, PipelineStage, Recipe, Step
from engine.pipeline import ExtractionPipeline


class _FakeDownloader:
    def __init__(self, source_video: Path, caption: str | None = "Une superbe recette", title: str | None = "Mon reel") -> None:
        self._source_video = source_video
        self.caption = caption
        self.title = title

    def download(self, url: str, dest_dir: Path) -> DownloadedVideo:
        dest_dir.mkdir(parents=True, exist_ok=True)
        video_path = dest_dir / "video.mp4"
        # On copie la fixture plutôt que la référencer directement : chaque
        # test doit avoir son propre fichier, indépendant de la fixture
        # partagée.
        shutil.copyfile(self._source_video, video_path)
        return DownloadedVideo(
            video_path=video_path, title=self.title, caption=self.caption, thumbnail_path=None
        )


class _FailingDownloader:
    def download(self, url: str, dest_dir: Path) -> DownloadedVideo:
        raise DownloadError("réseau indisponible")


class _FakeTranscriber:
    def transcribe(self, audio_path: Path) -> str:
        return "on fait cuire des pâtes pendant dix minutes"


class _FakeReconstructor:
    def __init__(self, recipe: Recipe | None = None, error: Exception | None = None) -> None:
        self._recipe = recipe
        self._error = error

    def reconstruct(self, **kwargs) -> Recipe:
        if self._error is not None:
            raise self._error
        return self._recipe


def test_pipeline_success_end_to_end(tiny_video, tmp_path):
    config = EngineConfig(data_dir=tmp_path)
    expected_recipe = Recipe(
        title="Pâtes",
        ingredients=[Ingredient(name="Pâtes", quantity="200 g")],
        steps=[Step(order=1, text="Cuire")],
    )
    pipeline = ExtractionPipeline(
        config,
        downloader=_FakeDownloader(tiny_video),
        transcriber=_FakeTranscriber(),
        reconstructor=_FakeReconstructor(recipe=expected_recipe),
    )

    stages: list[PipelineStage] = []
    result = pipeline.extract("https://instagram.com/reel/abc", on_progress=stages.append)

    assert result.status is ExtractionStatus.SUCCESS
    assert result.recipe.title == "Pâtes"
    assert result.transcript
    assert result.frame_paths
    assert stages == [
        PipelineStage.DOWNLOAD,
        PipelineStage.AUDIO_EXTRACTION,
        PipelineStage.TRANSCRIPTION,
        PipelineStage.FRAME_EXTRACTION,
        PipelineStage.RECIPE_RECONSTRUCTION,
    ]
    # La vidéo brute est conservée (pour pouvoir la rejouer depuis la fiche
    # détail) et référencée sur la recette.
    assert list(config.downloads_dir.rglob("*.mp4"))
    assert result.recipe.video_path is not None
    assert Path(result.recipe.video_path).exists()
    # ...et les images clés doivent aussi survivre pour l'appelant.
    assert list(config.frames_dir.rglob("*.jpg"))


def test_pipeline_uses_heuristic_reconstructor_when_use_ai_is_false(tiny_video, tmp_path):
    config = EngineConfig(data_dir=tmp_path)

    class _FakeHeuristic:
        def reconstruct(self, **kwargs):
            return Recipe(title="Recette sans IA", extraction_method="auto")

    ai_reconstructor = _FakeReconstructor(error=RecipeReconstructionError("ne devrait pas être appelé"))
    pipeline = ExtractionPipeline(
        config,
        downloader=_FakeDownloader(tiny_video),
        transcriber=_FakeTranscriber(),
        reconstructor=ai_reconstructor,
        heuristic_reconstructor=_FakeHeuristic(),
    )

    result = pipeline.extract("https://instagram.com/reel/free", use_ai=False)

    assert result.status is ExtractionStatus.SUCCESS
    assert result.recipe.title == "Recette sans IA"
    assert result.used_ai is False


def test_pipeline_marks_used_ai_true_by_default(tiny_video, tmp_path):
    config = EngineConfig(data_dir=tmp_path)
    pipeline = ExtractionPipeline(
        config,
        downloader=_FakeDownloader(tiny_video),
        transcriber=_FakeTranscriber(),
        reconstructor=_FakeReconstructor(recipe=Recipe(title="Pâtes")),
    )

    result = pipeline.extract("https://instagram.com/reel/ai")

    assert result.used_ai is True


def test_pipeline_failed_when_download_fails(tmp_path):
    config = EngineConfig(data_dir=tmp_path)
    pipeline = ExtractionPipeline(
        config,
        downloader=_FailingDownloader(),
        transcriber=_FakeTranscriber(),
        reconstructor=_FakeReconstructor(),
    )

    result = pipeline.extract("https://instagram.com/reel/broken")

    assert result.status is ExtractionStatus.FAILED
    assert result.failed_stage is PipelineStage.DOWNLOAD
    assert result.recipe.extraction_method == "manual"


def test_pipeline_partial_when_reconstruction_fails(tiny_video, tmp_path):
    config = EngineConfig(data_dir=tmp_path)
    pipeline = ExtractionPipeline(
        config,
        downloader=_FakeDownloader(tiny_video, caption="Recette secrète"),
        transcriber=_FakeTranscriber(),
        reconstructor=_FakeReconstructor(error=RecipeReconstructionError("panne LLM")),
    )

    result = pipeline.extract("https://instagram.com/reel/def")

    assert result.status is ExtractionStatus.PARTIAL
    assert result.failed_stage is PipelineStage.RECIPE_RECONSTRUCTION
    assert result.caption == "Recette secrète"
    assert result.transcript
    # Le brouillon manuel est pré-rempli avec la légende, pour ne pas
    # repartir de zéro dans l'écran de saisie manuelle.
    assert result.recipe.notes == "Recette secrète"
    assert result.recipe.extraction_method == "manual"

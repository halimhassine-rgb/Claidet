import zipfile

import pytest

from engine.models import Ingredient, Recipe, Step
from storage.backup import BackupError, export_to_zip, import_from_zip
from storage.repository import RecipeRepository


def _make_recipe(**overrides) -> Recipe:
    defaults = dict(
        title="Salade de pâtes",
        category="Entrée",
        servings="4 personnes",
        ingredients=[Ingredient(name="Pâtes", quantity="300 g")],
        steps=[Step(order=1, text="Cuire les pâtes")],
        notes="Meilleure le lendemain.",
        extraction_method="manual",
    )
    defaults.update(overrides)
    return Recipe(**defaults)


def test_export_then_import_roundtrip(tmp_path):
    source_repo = RecipeRepository(tmp_path / "source.sqlite", covers_dir=tmp_path / "source_covers")

    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"\xff\xd8\xff")
    saved = source_repo.save(_make_recipe(cover_image_path=str(cover)))
    source_repo.save(_make_recipe(title="Tarte", category="Dessert"))

    archive_path = tmp_path / "export.zip"
    count = export_to_zip(source_repo, archive_path)
    assert count == 2
    assert archive_path.exists()

    dest_repo = RecipeRepository(tmp_path / "dest.sqlite", covers_dir=tmp_path / "dest_covers")
    imported = import_from_zip(dest_repo, archive_path)
    assert imported == 2

    recipes = {r.title: r for r in dest_repo.list_all()}
    assert set(recipes) == {"Salade de pâtes", "Tarte"}

    migrated = dest_repo.get(saved.id)
    assert migrated is not None
    assert migrated.category == "Entrée"
    assert migrated.ingredients[0].name == "Pâtes"
    assert migrated.cover_image_path is not None
    assert (tmp_path / "dest_covers").exists()
    from pathlib import Path

    assert Path(migrated.cover_image_path).read_bytes() == b"\xff\xd8\xff"


def test_export_then_import_carries_video_file(tmp_path):
    source_repo = RecipeRepository(
        tmp_path / "source.sqlite",
        covers_dir=tmp_path / "source_covers",
        videos_dir=tmp_path / "source_videos",
    )

    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake video bytes")
    saved = source_repo.save(_make_recipe(video_path=str(video)))

    archive_path = tmp_path / "export.zip"
    export_to_zip(source_repo, archive_path)

    dest_repo = RecipeRepository(
        tmp_path / "dest.sqlite",
        covers_dir=tmp_path / "dest_covers",
        videos_dir=tmp_path / "dest_videos",
    )
    import_from_zip(dest_repo, archive_path)

    migrated = dest_repo.get(saved.id)
    assert migrated is not None
    assert migrated.video_path is not None
    from pathlib import Path

    assert Path(migrated.video_path).read_bytes() == b"fake video bytes"


def test_export_skips_missing_cover_file(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    repo.save(_make_recipe(cover_image_path=str(tmp_path / "does_not_exist.jpg")))

    archive_path = tmp_path / "export.zip"
    export_to_zip(repo, archive_path)

    dest_repo = RecipeRepository(tmp_path / "dest.sqlite", covers_dir=tmp_path / "dest_covers")
    import_from_zip(dest_repo, archive_path)

    recipe = dest_repo.list_all()[0]
    assert recipe.cover_image_path is None


def test_import_rejects_non_zip_file(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    bogus = tmp_path / "not_a_zip.zip"
    bogus.write_text("ceci n'est pas une archive")

    with pytest.raises(BackupError):
        import_from_zip(repo, bogus)


def test_import_rejects_zip_without_manifest(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    empty_zip = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty_zip, "w") as archive:
        archive.writestr("hello.txt", "pas de manifeste ici")

    with pytest.raises(BackupError):
        import_from_zip(repo, empty_zip)


def test_import_is_idempotent_for_same_recipe(tmp_path):
    source_repo = RecipeRepository(tmp_path / "source.sqlite", covers_dir=tmp_path / "source_covers")
    source_repo.save(_make_recipe())

    archive_path = tmp_path / "export.zip"
    export_to_zip(source_repo, archive_path)

    dest_repo = RecipeRepository(tmp_path / "dest.sqlite", covers_dir=tmp_path / "dest_covers")
    import_from_zip(dest_repo, archive_path)
    import_from_zip(dest_repo, archive_path)  # ré-importer ne duplique pas

    assert len(dest_repo.list_all()) == 1

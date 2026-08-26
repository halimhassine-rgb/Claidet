from pathlib import Path

from engine.models import Ingredient, Recipe, Step
from storage.repository import RecipeRepository


def _make_recipe(**overrides) -> Recipe:
    defaults = dict(
        title="Salade de pâtes",
        category="Entrée",
        servings="4 personnes",
        ingredients=[Ingredient(name="Pâtes", quantity="300 g")],
        steps=[Step(order=1, text="Cuire les pâtes")],
        extraction_method="manual",
    )
    defaults.update(overrides)
    return Recipe(**defaults)


def test_save_and_get_roundtrip(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    recipe = _make_recipe()

    saved = repo.save(recipe)
    fetched = repo.get(saved.id)

    assert fetched is not None
    assert fetched.title == "Salade de pâtes"
    assert fetched.category == "Entrée"
    assert fetched.ingredients[0].name == "Pâtes"
    assert fetched.steps[0].text == "Cuire les pâtes"


def test_get_missing_recipe_returns_none(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    assert repo.get("does-not-exist") is None


def test_save_copies_cover_image_into_covers_dir(tmp_path):
    source_image = tmp_path / "work" / "cover.jpg"
    source_image.parent.mkdir()
    source_image.write_bytes(b"\xff\xd8\xff")

    covers_dir = tmp_path / "covers"
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=covers_dir)
    recipe = _make_recipe(cover_image_path=str(source_image))

    saved = repo.save(recipe)

    assert saved.cover_image_path is not None
    assert Path(saved.cover_image_path).parent == covers_dir
    assert Path(saved.cover_image_path).read_bytes() == b"\xff\xd8\xff"
    # Le fichier source, hors covers_dir, n'est pas touché.
    assert source_image.exists()


def test_save_preserves_created_at_on_update(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    first = repo.save(_make_recipe())

    updated = first.model_copy(update={"title": "Salade de pâtes revisitée"})
    second = repo.save(updated)

    assert second.created_at == first.created_at
    assert second.title == "Salade de pâtes revisitée"
    assert second.updated_at >= first.updated_at


def test_list_all_orders_by_manual_sort_order_by_default(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    repo.save(_make_recipe(title="Première"))
    repo.save(_make_recipe(title="Seconde"))

    recipes = repo.list_all()

    # Nouvelles recettes ajoutées à la fin de l'ordre personnalisé.
    assert [r.title for r in recipes] == ["Première", "Seconde"]


def test_reorder_recipes_updates_sort_order(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    first = repo.save(_make_recipe(title="Première"))
    second = repo.save(_make_recipe(title="Seconde"))
    third = repo.save(_make_recipe(title="Troisième"))

    repo.reorder_recipes([third.id, first.id, second.id])

    assert [r.title for r in repo.list_all()] == ["Troisième", "Première", "Seconde"]


def test_set_favorite_toggles_flag(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    saved = repo.save(_make_recipe())
    assert saved.is_favorite is False

    repo.set_favorite(saved.id, True)
    assert repo.get(saved.id).is_favorite is True

    repo.set_favorite(saved.id, False)
    assert repo.get(saved.id).is_favorite is False


def test_rating_roundtrip(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    saved = repo.save(_make_recipe(rating=8))

    assert repo.get(saved.id).rating == 8


def test_category_order_roundtrip(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    assert repo.get_category_order() == []

    repo.set_category_order(["Dessert", "Entrée", "Plat"])

    assert repo.get_category_order() == ["Dessert", "Entrée", "Plat"]


def test_sort_mode_defaults_to_manual_and_roundtrips(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    assert repo.get_sort_mode() == "manual"

    repo.set_sort_mode("rating_desc")

    assert repo.get_sort_mode() == "rating_desc"


def test_list_categories_returns_distinct_used_categories(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    repo.save(_make_recipe(title="Salade", category="Entrée"))
    repo.save(_make_recipe(title="Tiramisu", category="Dessert"))
    repo.save(_make_recipe(title="Autre salade", category="Entrée"))
    repo.save(_make_recipe(title="Sans catégorie", category=None))

    assert repo.list_categories() == ["Dessert", "Entrée"]


def test_save_moves_video_into_videos_dir(tmp_path):
    source_video = tmp_path / "work" / "video.mp4"
    source_video.parent.mkdir()
    source_video.write_bytes(b"fake video bytes")

    videos_dir = tmp_path / "videos"
    repo = RecipeRepository(
        tmp_path / "db.sqlite", covers_dir=tmp_path / "covers", videos_dir=videos_dir
    )
    recipe = _make_recipe(video_path=str(source_video))

    saved = repo.save(recipe)

    assert saved.video_path is not None
    assert Path(saved.video_path).parent == videos_dir
    assert Path(saved.video_path).read_bytes() == b"fake video bytes"
    assert repo.get(saved.id).video_path == saved.video_path


def test_find_by_source_url_returns_matching_recipe(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    saved = repo.save(_make_recipe(source_url="https://instagram.com/reel/abc"))
    repo.save(_make_recipe(title="Autre", source_url="https://instagram.com/reel/def"))

    found = repo.find_by_source_url("https://instagram.com/reel/abc")

    assert found is not None
    assert found.id == saved.id
    assert repo.find_by_source_url("https://instagram.com/reel/inconnu") is None


def test_delete_removes_recipe_and_cover_file(tmp_path):
    source_image = tmp_path / "cover_src.jpg"
    source_image.write_bytes(b"data")
    covers_dir = tmp_path / "covers"
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=covers_dir)
    saved = repo.save(_make_recipe(cover_image_path=str(source_image)))
    cover_path = Path(saved.cover_image_path)
    assert cover_path.exists()

    repo.delete(saved.id)

    assert repo.get(saved.id) is None
    assert not cover_path.exists()


def test_delete_removes_video_file(tmp_path):
    source_video = tmp_path / "video_src.mp4"
    source_video.write_bytes(b"data")
    videos_dir = tmp_path / "videos"
    repo = RecipeRepository(
        tmp_path / "db.sqlite", covers_dir=tmp_path / "covers", videos_dir=videos_dir
    )
    saved = repo.save(_make_recipe(video_path=str(source_video)))
    video_path = Path(saved.video_path)
    assert video_path.exists()

    repo.delete(saved.id)

    assert not video_path.exists()

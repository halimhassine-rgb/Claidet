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


def test_list_all_orders_by_updated_at_desc(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    repo.save(_make_recipe(title="Ancienne"))
    repo.save(_make_recipe(title="Récente"))

    recipes = repo.list_all()

    assert [r.title for r in recipes] == ["Récente", "Ancienne"]


def test_list_categories_returns_distinct_used_categories(tmp_path):
    repo = RecipeRepository(tmp_path / "db.sqlite", covers_dir=tmp_path / "covers")
    repo.save(_make_recipe(title="Salade", category="Entrée"))
    repo.save(_make_recipe(title="Tiramisu", category="Dessert"))
    repo.save(_make_recipe(title="Autre salade", category="Entrée"))
    repo.save(_make_recipe(title="Sans catégorie", category=None))

    assert repo.list_categories() == ["Dessert", "Entrée"]


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

import json

import pytest

from engine.exceptions import RecipeReconstructionError
from engine.recipe_builder import (
    ClaudeRecipeReconstructor,
    HeuristicRecipeReconstructor,
    _extract_json,
)


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self._response_text)


class _FakeClient:
    def __init__(self, response_text: str) -> None:
        self.messages = _FakeMessages(response_text)


def _valid_payload_text() -> str:
    return json.dumps(
        {
            "title": "Pâtes au pesto",
            "category": "Plat",
            "servings": "2 personnes",
            "ingredients": [{"name": "Pâtes", "quantity": "200 g", "note": None}],
            "steps": ["Cuire les pâtes", "Ajouter le pesto"],
            "notes": None,
        }
    )


def test_reconstruct_parses_valid_json():
    reconstructor = ClaudeRecipeReconstructor(api_key="fake", model="claude-sonnet-5")
    reconstructor._client = _FakeClient(_valid_payload_text())

    recipe = reconstructor.reconstruct(
        transcript="on cuit des pâtes",
        caption="recette de pâtes",
        frame_paths=[],
        source_url="https://instagram.com/reel/xyz",
    )

    assert recipe.title == "Pâtes au pesto"
    assert recipe.category == "Plat"
    assert recipe.servings == "2 personnes"
    assert [i.name for i in recipe.ingredients] == ["Pâtes"]
    assert [s.text for s in recipe.steps] == ["Cuire les pâtes", "Ajouter le pesto"]
    assert recipe.extraction_method == "auto"
    assert recipe.source_url == "https://instagram.com/reel/xyz"


def test_reconstruct_raises_on_garbage_response():
    reconstructor = ClaudeRecipeReconstructor(api_key="fake", model="claude-sonnet-5")
    reconstructor._client = _FakeClient("désolé je ne peux pas aider")

    with pytest.raises(RecipeReconstructionError):
        reconstructor.reconstruct(transcript="x", caption=None, frame_paths=[], source_url=None)


def test_reconstruct_without_api_key_raises():
    reconstructor = ClaudeRecipeReconstructor(api_key=None, model="claude-sonnet-5")

    with pytest.raises(RecipeReconstructionError):
        reconstructor.reconstruct(transcript="x", caption=None, frame_paths=[], source_url=None)


def test_reconstruct_sends_one_image_block_per_frame(tmp_path):
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"\xff\xd8\xff")

    reconstructor = ClaudeRecipeReconstructor(api_key="fake", model="claude-sonnet-5")
    fake_client = _FakeClient(_valid_payload_text())
    reconstructor._client = fake_client

    reconstructor.reconstruct(transcript=None, caption=None, frame_paths=[frame], source_url=None)

    content = fake_client.messages.last_kwargs["messages"][0]["content"]
    image_blocks = [block for block in content if block["type"] == "image"]
    assert len(image_blocks) == 1
    assert image_blocks[0]["source"]["media_type"] == "image/jpeg"


def test_extract_json_strips_surrounding_text():
    text = "Voici la recette :\n{\"title\": \"Test\"}\nBon appétit !"
    assert _extract_json(text) == {"title": "Test"}


def test_extract_json_raises_without_braces():
    with pytest.raises(RecipeReconstructionError):
        _extract_json("pas de json ici")


def test_heuristic_reconstruct_parses_structured_caption():
    caption = (
        "Pâtes au pesto maison\n"
        "Ingrédients :\n"
        "- 200 g de pâtes\n"
        "- 2 cuillères à soupe de pesto\n"
        "- 1 gousse d'ail\n"
        "#recette #pates"
    )
    transcript = "On fait cuire les pâtes. Ensuite on ajoute le pesto. On mélange bien."

    reconstructor = HeuristicRecipeReconstructor()
    recipe = reconstructor.reconstruct(
        transcript=transcript,
        caption=caption,
        frame_paths=[],
        source_url="https://instagram.com/reel/abc",
    )

    assert recipe.title == "Pâtes au pesto maison"
    assert recipe.source_url == "https://instagram.com/reel/abc"
    assert recipe.extraction_method == "auto"
    names = [i.name for i in recipe.ingredients]
    assert "pâtes" in names
    assert any(i.quantity and "200" in i.quantity for i in recipe.ingredients)
    assert [s.text for s in recipe.steps] == [
        "On fait cuire les pâtes.",
        "Ensuite on ajoute le pesto.",
        "On mélange bien.",
    ]


def test_heuristic_reconstruct_never_raises_on_empty_input():
    reconstructor = HeuristicRecipeReconstructor()
    recipe = reconstructor.reconstruct(
        transcript=None, caption=None, frame_paths=[], source_url=None
    )

    assert recipe.title == "Recette sans titre"
    assert recipe.ingredients == []
    assert recipe.steps == []

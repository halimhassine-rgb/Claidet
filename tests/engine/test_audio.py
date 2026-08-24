import pytest

from engine.audio import extract_audio
from engine.exceptions import AudioExtractionError


def test_extract_audio_produces_wav(tiny_video, tmp_path):
    audio_path = extract_audio(tiny_video, tmp_path)

    assert audio_path.exists()
    assert audio_path.suffix == ".wav"
    assert audio_path.stat().st_size > 0


def test_extract_audio_raises_on_missing_video(tmp_path):
    with pytest.raises(AudioExtractionError):
        extract_audio(tmp_path / "does_not_exist.mp4", tmp_path / "out")

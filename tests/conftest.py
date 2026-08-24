import shutil
import subprocess

import pytest


@pytest.fixture(scope="session")
def tiny_video(tmp_path_factory):
    """Une vidéo mp4 minuscule (image de test + son) générée avec ffmpeg,
    pour tester audio.py/frames.py contre un vrai binaire ffmpeg sans
    dépendre d'un fichier vidéo versionné ni du réseau."""

    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg n'est pas installé")

    video_dir = tmp_path_factory.mktemp("fixtures")
    video_path = video_dir / "tiny.mp4"
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=64x64:rate=5:duration=2",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(video_path),
    ]
    subprocess.run(command, capture_output=True, check=True)
    return video_path

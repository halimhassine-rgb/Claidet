from engine.frames import extract_key_frames, pick_cover_image


def test_extract_key_frames_returns_requested_count(tiny_video, tmp_path):
    frames = extract_key_frames(tiny_video, tmp_path, max_frames=3)

    assert len(frames) == 3
    for frame in frames:
        assert frame.exists()
        assert frame.stat().st_size > 0


def test_pick_cover_image_prefers_thumbnail(tmp_path):
    thumbnail = tmp_path / "thumb.jpg"
    thumbnail.write_bytes(b"x")
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"y")

    assert pick_cover_image([frame], thumbnail) == thumbnail


def test_pick_cover_image_falls_back_to_first_frame(tmp_path):
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"y")

    assert pick_cover_image([frame], None) == frame


def test_pick_cover_image_none_when_nothing_available():
    assert pick_cover_image([], None) is None

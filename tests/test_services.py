import pytest
from app.services import safe_filename, validate_video


def test_safe_filename_blocks_path_traversal():
    assert safe_filename("../../secret.mp4") == "secret.mp4"


def test_video_validation():
    validate_video("clip.mp4", 10)
    with pytest.raises(ValueError):
        validate_video("clip.txt", 10)

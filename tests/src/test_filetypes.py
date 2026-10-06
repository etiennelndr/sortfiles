"""Tests of the detection of file types."""

from collections.abc import Callable
from pathlib import Path

import pytest

from sortfiles.filetypes import FileType, ImageType, SidecarType, VideoType, get_file_type


@pytest.mark.parametrize(
    ("file_name", "expected_type"),
    [
        ("picture.jpg", ImageType.JPEG),
        ("picture.JPG", ImageType.JPEG),
        ("picture.jpeg", ImageType.JPEG),
        ("picture.png", ImageType.PNG),
        ("picture.heic", ImageType.HEIC),
        ("picture.raw", ImageType.RAW),
        ("picture.arw", ImageType.ARW),
        ("picture.cr2", ImageType.CR2),
        ("picture.CR2", ImageType.CR2),
        ("picture.dng", ImageType.DNG),
        ("picture.nef", ImageType.NEF),
        ("video.mov", VideoType.MOV),
        ("video.mp4", VideoType.MP4),
        ("picture.aae", SidecarType.AAE),
        ("picture.AAE", SidecarType.AAE),
        ("picture.xmp", SidecarType.XMP),
        ("picture.jpg.xmp", SidecarType.XMP),
    ],
)
def test_get_file_type(
    make_file: Callable[..., Path], file_name: str, expected_type: FileType
) -> None:
    assert get_file_type(make_file(file_name)) is expected_type


@pytest.mark.parametrize(
    "file_name", ["notes.txt", "picture.cr3", "picture.gif", "music.mp3", "no_extension"]
)
def test_get_file_type_unsupported(make_file: Callable[..., Path], file_name: str) -> None:
    assert get_file_type(make_file(file_name)) is None


def test_get_file_type_folder(tmp_path: Path) -> None:
    folder = tmp_path / "folder.jpg"
    folder.mkdir()

    assert get_file_type(folder) is None


def test_get_file_type_missing_file(tmp_path: Path) -> None:
    assert get_file_type(tmp_path / "missing.jpg") is None

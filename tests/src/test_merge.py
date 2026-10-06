"""Tests of the merge of duplicate pictures."""

from collections.abc import Callable
from pathlib import Path

import pytest

from sortfiles.merge import merge


def _read_files(folder: Path) -> dict[str, bytes]:
    """Reads the files of a folder, identified by their POSIX path relative to it."""
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()
    }


def test_merge_replaces_original_with_edited(
    tmp_path: Path, make_file: Callable[..., Path]
) -> None:
    make_file("IMG_0001.jpg", b"original")
    make_file("IMG_E0001.jpg", b"edited")

    merge(tmp_path)

    assert _read_files(tmp_path) == {"IMG_0001.jpg": b"edited"}


def test_merge_keeps_extension_of_edited(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("IMG_0001.heic", b"original")
    make_file("IMG_E0001.jpg", b"edited")

    merge(tmp_path)

    assert _read_files(tmp_path) == {"IMG_0001.jpg": b"edited"}


def test_merge_prefers_edited_with_same_extension(
    tmp_path: Path, make_file: Callable[..., Path]
) -> None:
    make_file("IMG_0001.jpg", b"original")
    make_file("IMG_E0001.heic", b"edited heic")
    make_file("IMG_E0001.jpg", b"edited jpg")

    merge(tmp_path)

    assert _read_files(tmp_path) == {
        "IMG_0001.jpg": b"edited jpg",
        "IMG_E0001.heic": b"edited heic",
    }


def test_merge_is_recursive(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("IMG_0001.jpg", b"original 1")
    make_file("IMG_E0001.jpg", b"edited 1")
    make_file("holidays/IMG_0002.jpg", b"original 2")
    make_file("holidays/IMG_E0002.jpg", b"edited 2")

    merge(tmp_path)

    assert _read_files(tmp_path) == {
        "IMG_0001.jpg": b"edited 1",
        "holidays/IMG_0002.jpg": b"edited 2",
    }


@pytest.mark.parametrize(
    "file_names",
    [
        pytest.param(["IMG_0001.jpg"], id="original only"),
        pytest.param(["IMG_E0001.jpg"], id="edited only"),
        pytest.param(["photo.jpg", "IMG_Ephoto.jpg"], id="no original prefix"),
        pytest.param(["IMG_0001.png", "IMG_E0001.png"], id="unmergeable original"),
        pytest.param(["IMG_0001.jpg", "IMG_E0001.png"], id="unmergeable edited"),
        pytest.param(["IMG_0001.jpg", "IMG_E0001.txt"], id="unsupported edited"),
    ],
)
def test_merge_leaves_files_untouched(
    tmp_path: Path, make_file: Callable[..., Path], file_names: list[str]
) -> None:
    for file_name in file_names:
        make_file(file_name, file_name.encode())

    merge(tmp_path)

    assert _read_files(tmp_path) == {file_name: file_name.encode() for file_name in file_names}


def test_merge_dry_run(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("IMG_0001.jpg", b"original")
    make_file("IMG_E0001.jpg", b"edited")

    merge(tmp_path, dry_run=True)

    assert _read_files(tmp_path) == {"IMG_0001.jpg": b"original", "IMG_E0001.jpg": b"edited"}

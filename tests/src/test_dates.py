"""Tests of the retrieval of creation dates."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from sortfiles.dates import retrieve_file_creation_date

MODIFIED: date = date(2015, 6, 15)
"""Modification date of the files, to tell a date read from EXIF from a file system one."""


def test_exif_original_date_is_preferred(
    make_file: Callable[..., Path], make_exif: Callable[..., bytes]
) -> None:
    content = make_exif(image_date="2024:05:05 10:00:00", original_date="2019:03:02 10:00:00")
    file_path = make_file("picture.jpg", content, modified=MODIFIED)

    assert retrieve_file_creation_date(file_path) == date(2019, 3, 2)


def test_exif_image_date_is_used_without_original_date(
    make_file: Callable[..., Path], make_exif: Callable[..., bytes]
) -> None:
    content = make_exif(image_date="2021:07:01 10:00:00")
    file_path = make_file("picture.jpg", content, modified=MODIFIED)

    assert retrieve_file_creation_date(file_path) == date(2021, 7, 1)


def test_exif_image_date_is_used_with_unreadable_original_date(
    make_file: Callable[..., Path], make_exif: Callable[..., bytes]
) -> None:
    content = make_exif(image_date="2021:07:01 10:00:00", original_date="0000:00:00 00:00:00")
    file_path = make_file("picture.jpg", content, modified=MODIFIED)

    assert retrieve_file_creation_date(file_path) == date(2021, 7, 1)


def test_exif_alternative_date_format(
    make_file: Callable[..., Path], make_exif: Callable[..., bytes]
) -> None:
    content = make_exif(original_date="2021/07/01 10:00")
    file_path = make_file("picture.jpg", content, modified=MODIFIED)

    assert retrieve_file_creation_date(file_path) == date(2021, 7, 1)


def test_exif_of_raw_picture(
    make_file: Callable[..., Path], make_exif: Callable[..., bytes]
) -> None:
    content = make_exif(original_date="2017:08:09 10:00:00", jpeg=False)
    file_path = make_file("picture.cr2", content, modified=MODIFIED)

    assert retrieve_file_creation_date(file_path) == date(2017, 8, 9)


def test_picture_without_exif_uses_file_system(make_file: Callable[..., Path]) -> None:
    file_path = make_file("picture.jpg", modified=MODIFIED)

    assert retrieve_file_creation_date(file_path) == MODIFIED


def test_picture_with_unreadable_exif_date_uses_file_system(
    make_file: Callable[..., Path], make_exif: Callable[..., bytes]
) -> None:
    content = make_exif(original_date="0000:00:00 00:00:00")
    file_path = make_file("picture.jpg", content, modified=MODIFIED)

    assert retrieve_file_creation_date(file_path) == MODIFIED


def test_video_uses_file_system(make_file: Callable[..., Path]) -> None:
    file_path = make_file("video.mp4", modified=MODIFIED)

    assert retrieve_file_creation_date(file_path) == MODIFIED


def test_file_system_uses_birth_time_if_older(make_file: Callable[..., Path]) -> None:
    file_path = make_file("video.mp4", modified=date(date.today().year + 1, 1, 1))
    file_birthtime = getattr(file_path.stat(), "st_birthtime", None)
    if file_birthtime is None:
        pytest.skip("Birth time is unavailable on this platform")

    assert retrieve_file_creation_date(file_path) == date.fromtimestamp(file_birthtime)


@pytest.mark.parametrize("sidecar_name", ["IMG_0001.aae", "IMG_0001.xmp", "IMG_0001.jpg.xmp"])
def test_sidecar_uses_date_of_its_owner(
    make_file: Callable[..., Path], make_exif: Callable[..., bytes], sidecar_name: str
) -> None:
    make_file("IMG_0001.jpg", make_exif(original_date="2019:03:02 10:00:00"), modified=MODIFIED)
    sidecar_path = make_file(sidecar_name)

    assert retrieve_file_creation_date(sidecar_path) == date(2019, 3, 2)


def test_orphan_sidecar_has_no_date(make_file: Callable[..., Path]) -> None:
    make_file("IMG_0002.jpg")
    sidecar_path = make_file("IMG_0001.aae")

    assert retrieve_file_creation_date(sidecar_path) is None


def test_sidecar_is_not_owned_by_another_sidecar(make_file: Callable[..., Path]) -> None:
    make_file("IMG_0001.xmp")
    sidecar_path = make_file("IMG_0001.aae")

    assert retrieve_file_creation_date(sidecar_path) is None


def test_unsupported_file_has_no_date(make_file: Callable[..., Path]) -> None:
    file_path = make_file("notes.txt")

    assert retrieve_file_creation_date(file_path) is None

"""Retrieval of the creation date of a file."""

import glob
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Final

from exifread import process_file

from .filetypes import ImageType, SidecarType, VideoType, get_file_type

# Files without any EXIF are expected: do not let `exifread` warn about each of them
logging.getLogger("exifread").setLevel(logging.ERROR)


def retrieve_file_creation_date(file_path: Path) -> date | None:
    """Retrieves the creation date of a file.

    The source of the date depends on the file type:

    - picture: EXIF metadata, or the file system if they hold no date;
    - video: file system;
    - sidecar: date of the picture or the video it is attached to.

    :return: creation date, or `None` if the file is unsupported or is a sidecar without owner.
    """
    match get_file_type(file_path):
        case ImageType():
            try:
                return _retrieve_creation_date_exif(file_path)
            except ValueError:
                return _retrieve_creation_date_dummy(file_path)
        case VideoType():
            return _retrieve_creation_date_dummy(file_path)
        case SidecarType():
            owner_path = _find_sidecar_owner(file_path)
            if owner_path is None:
                return None

            return retrieve_file_creation_date(owner_path)
        case _:
            # File type is unsupported: skip it
            return None


def _find_sidecar_owner(sidecar_path: Path) -> Path | None:
    """Finds the picture or the video a sidecar is attached to.

    It is the file of the same folder sharing the name of the sidecar: `IMG_1234.jpg` for
    `IMG_1234.aae` as well as for `IMG_1234.jpg.xmp`.
    """
    owner_paths = [
        sidecar_path.with_suffix(""),
        *sorted(sidecar_path.parent.glob(f"{glob.escape(sidecar_path.stem)}.*")),
    ]
    for owner_path in owner_paths:
        owner_type = get_file_type(owner_path)
        if owner_type is not None and not isinstance(owner_type, SidecarType):
            return owner_path

    return None


_EXIF_DATE_TAGS: Final = ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime")
"""EXIF tags holding a date, from the most to the least reliable.

`Image DateTime` is the last modification date: it is only used when the shooting date is missing.
"""


def _retrieve_creation_date_exif(file_path: Path) -> date:
    """Retrieves the creation date of a picture from its EXIF metadata.

    :raise ValueError: if EXIF metadata hold no readable date.
    """
    with file_path.open("rb") as file_path_stream:
        # Dates are stored in standard tags: maker notes and thumbnail are useless and slow to read
        file_img_exif = process_file(file_path_stream, details=False, extract_thumbnail=False)

    for file_creation_date_tag in _EXIF_DATE_TAGS:
        if file_creation_date_tag not in file_img_exif:
            continue

        file_creation_date = str(file_img_exif[file_creation_date_tag].values)
        for file_creation_date_format in ("%Y:%m:%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(file_creation_date, file_creation_date_format).date()
            except ValueError:
                pass

    raise ValueError(f"Unable to extract creation date from EXIF for file '{file_path}'")


def _retrieve_creation_date_dummy(file_path: Path) -> date:
    """Retrieves the creation date of a file from the file system."""
    info = file_path.stat()
    # Birth time is unavailable on some platforms (e.g. Linux). Moreover, a copy is a new file: its
    # birth time is the date of the copy, whereas its modification time is usually preserved. The
    # oldest of both is thus the closest to the real creation date.
    file_timestamps = [info.st_mtime]
    file_birthtime = getattr(info, "st_birthtime", None)
    if file_birthtime is not None:
        file_timestamps.append(file_birthtime)

    return date.fromtimestamp(min(file_timestamps))


__all__ = ["retrieve_file_creation_date"]

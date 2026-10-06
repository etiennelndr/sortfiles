"""Supported file types and their detection."""

import mimetypes
from enum import Enum
from pathlib import Path

mimetypes.init()


class FileType(Enum):
    """An enumeration of supported file types.

    Unless otherwise stated, values are MIME subtypes and not extensions: `.jpg` and `.jpeg` files
    are both `image/jpeg`, `.mov` files are `video/quicktime`.
    """


class ImageType(FileType):
    """An enumeration of supported image types."""

    ARW = "arw"
    CR2 = "cr2"
    DNG = "dng"
    HEIC = "heic"
    JPEG = "jpeg"
    NEF = "nef"
    PNG = "png"
    RAW = "raw"


class VideoType(FileType):
    """An enumeration of supported video types."""

    MOV = "quicktime"
    MP4 = "mp4"


class SidecarType(FileType):
    """An enumeration of supported sidecar types.

    A sidecar is a file holding metadata of a picture or a video (e.g. `IMG_1234.aae` for
    `IMG_1234.jpg`). It has no date of its own: it is sorted along with the file it is attached to.

    Values are extensions.
    """

    AAE = "aae"
    XMP = "xmp"


# MIME type of raw pictures is unknown or depends on the platform (e.g. `image/CR2` on Windows,
# `image/x-canon-cr2` on Linux): register them to get the same detection everywhere.
for _raw_type in (ImageType.ARW, ImageType.CR2, ImageType.DNG, ImageType.NEF, ImageType.RAW):
    mimetypes.add_type(f"image/{_raw_type.value}", f".{_raw_type.value}")


def get_file_type(file_path: Path) -> FileType | None:
    """Retrieves file type, or `None` if the path is not a file or its type is unsupported."""
    if not file_path.is_file():
        return None

    # Sidecars have no reliable MIME type: they are identified by their extension
    try:
        return SidecarType(file_path.suffix.removeprefix(".").lower())
    except ValueError:
        pass

    file_mimetype, _ = mimetypes.guess_type(file_path)
    if file_mimetype is None:
        return file_mimetype

    # Case of the MIME type depends on the platform (e.g. `image/RAW` on Windows)
    file_class, file_type = file_mimetype.lower().split("/", maxsplit=1)
    try:
        match file_class:
            case "image":
                return ImageType(file_type)
            case "video":
                return VideoType(file_type)
    except ValueError:
        pass

    return None


__all__ = ["FileType", "ImageType", "SidecarType", "VideoType", "get_file_type"]

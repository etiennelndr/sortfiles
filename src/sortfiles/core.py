import glob
import logging
import mimetypes
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Final

from exifread import process_file
from loguru import logger
from tqdm import tqdm

mimetypes.init()
# Files without any EXIF are expected: do not let `exifread` warn about each of them
logging.getLogger("exifread").setLevel(logging.ERROR)


class FileType(Enum):
    """An enumeration of supported file types."""


class ImageType(FileType):
    """An enumeration of supported image types."""

    HEIC = "heic"
    JPEG = "jpeg"
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


@dataclass
class FileInfo:
    """File information."""

    path: Path
    type: FileType
    creation_date: date


def get_file_information(file_path: Path) -> FileInfo | None:
    """Retrieves file information."""
    file_type = get_file_type(file_path)
    if file_type is None:
        return None

    file_creation_date = retrieve_file_creation_date(file_path, file_type)
    if file_creation_date is None:
        return None

    return FileInfo(
        path=file_path,
        type=file_type,
        creation_date=file_creation_date,
    )


def get_file_type(file_path: Path) -> FileType | None:
    """Retrieves file type."""
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


def retrieve_file_creation_date(file_path: Path, file_type: FileType | None = None) -> date | None:
    """Retrieves the creation date of a file.

    :param file_path: file path.
    :param file_type: pre-computed file type used to improve the process in some cases (e.g. reading
    date information in the EXIF).
    """
    if file_type is None:
        file_type = get_file_type(file_path)

    match file_type:
        case ImageType.JPEG | ImageType.PNG | ImageType.HEIC | ImageType.RAW:
            try:
                return _retrieve_creation_date_exif(file_path)
            except ValueError:
                return _retrieve_creation_date_dummy(file_path)
        case VideoType.MOV | VideoType.MP4:
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
    info = file_path.stat()
    # Birth time is unavailable on some platforms (e.g. Linux). Moreover, a copy is a new file: its
    # birth time is the date of the copy, whereas its modification time is usually preserved. The
    # oldest of both is thus the closest to the real creation date.
    file_timestamps = [info.st_mtime]
    file_birthtime = getattr(info, "st_birthtime", None)
    if file_birthtime is not None:
        file_timestamps.append(file_birthtime)

    return date.fromtimestamp(min(file_timestamps))


_YEAR_PATTERN: Final = re.compile(r"^[1-9][0-9]{3}$")
"""Year pattern.

Only years in the range [1000;9999] are valid.
"""
_MONTH_PATTERN: Final = re.compile(r"^(0[1-9]|1[0-2])$")


def is_valid(path: Path) -> bool:
    """Checks whether a path is sortable or not.

    A path is sortable iff it is not already sorted, i.e. it is not located in a year folder
    containing a month folder (e.g. `2024/10/...`).
    """
    file_path_elements = path.parts
    if len(file_path_elements) < 3:  # noqa: PLR2004
        return True

    return (
        _YEAR_PATTERN.fullmatch(file_path_elements[0]) is None
        or _MONTH_PATTERN.fullmatch(file_path_elements[1]) is None
    )


@dataclass
class ScanResult:
    """Result of the scan of a folder.

    All paths are relative to the scanned folder.
    """

    files: dict[date, list[Path]] = field(default_factory=lambda: defaultdict(list))
    """Files to sort, grouped by month (i.e. by the first day of their month)."""
    sorted_files: list[Path] = field(default_factory=list)
    """Files ignored because they are already sorted."""
    unsupported_files: list[Path] = field(default_factory=list)
    """Files ignored because their type or their date cannot be determined."""


def scan(folder: Path) -> ScanResult:
    """Recursively scans a folder to sort.

    Files which are already sorted or unsupported are reported in the result but are not sorted.
    """
    result = ScanResult()
    for file_path in folder.rglob("*"):
        if not file_path.is_file():
            continue

        file_path_relative = file_path.relative_to(folder)
        if not is_valid(file_path_relative):
            logger.debug(f"Ignoring already sorted file '{file_path}'")
            result.sorted_files.append(file_path_relative)
            continue

        file_info = get_file_information(file_path)
        if file_info is None:
            logger.debug(f"Ignoring unsupported file '{file_path}'")
            result.unsupported_files.append(file_path_relative)
            continue

        result.files[file_info.creation_date.replace(day=1)].append(file_path_relative)

    return result


def create_structure(folder: Path, scan_result: ScanResult) -> None:
    """Creates the `<year>/<month>` folders required by a scan result."""
    for scan_date in scan_result.files:
        scan_date_folder = folder / str(scan_date.year) / str(scan_date.month).zfill(2)
        logger.debug(f"Creating folder '{scan_date_folder}'")
        scan_date_folder.mkdir(parents=True, exist_ok=True)


def _compute_scan_result_size(scan_result: ScanResult) -> int:
    return sum(len(p) for p in scan_result.files.values())


def move_files(folder: Path, scan_result: ScanResult, dry_run: bool = False) -> int:
    """Moves files of a scan to their `<year>/<month>` folder.

    The path of a file relative to `folder` is kept: `holidays/IMG_1234.jpg` is moved to
    `<year>/<month>/holidays/IMG_1234.jpg`.

    Structure must be created before running this function. If not, an error is raised.

    :param folder: folder to sort.
    :param scan_result: result of the scan of `folder`.
    :param dry_run: whether to only log the moves instead of running them. Structure is not required
    in this mode.
    :return: number of moved files.
    """
    files_count = _compute_scan_result_size(scan_result)
    with tqdm(desc=f"Moving files in {folder}", total=files_count, disable=dry_run) as pbar:
        for scan_date, scan_elements in scan_result.files.items():
            scan_date_folder = folder / str(scan_date.year) / str(scan_date.month).zfill(2)
            if not dry_run and not scan_date_folder.exists():
                raise OSError(f"Date folder '{scan_date_folder}' does not exist")

            for element_path in scan_elements:
                old_element_path = folder / element_path
                new_element_path = scan_date_folder / element_path
                if dry_run:
                    already_exists = " (already exists)" if new_element_path.exists() else ""
                    logger.info(
                        f"Would move '{old_element_path}' to '{new_element_path}'{already_exists}"
                    )
                    continue

                new_element_path.parent.mkdir(parents=True, exist_ok=True)
                old_element_path.replace(new_element_path)

                # Update the progress after moving the file
                pbar.update()

    return files_count


def clean(folder: Path, scan_result: ScanResult) -> None:
    """Cleans the folders left empty after moving files.

    Folders which still contain something (e.g. unsupported files) are kept, and `folder` itself is
    never removed. This function must be run after moving files.
    """
    for scan_elements in scan_result.files.values():
        for element_path in scan_elements:
            # Walk up from the old parent folder to the root folder (excluded)
            for old_element_folder_relative in element_path.parents:
                if not old_element_folder_relative.parts:
                    break

                old_element_folder = folder / old_element_folder_relative
                if not old_element_folder.exists():
                    continue
                if any(old_element_folder.iterdir()):
                    logger.debug(f"Keeping non-empty folder '{old_element_folder}'")
                    break

                logger.debug(f"Removing empty folder '{old_element_folder}'")
                old_element_folder.rmdir()


_ORIGINAL_PREFIX: Final = "IMG_"
_EDITED_PREFIX: Final = "IMG_E"
_MERGEABLE_TYPES: Final = (ImageType.HEIC, ImageType.JPEG)


def _find_edited_file(file_path: Path) -> Path | None:
    """Finds the edited version of an original picture (e.g. `IMG_E1234` for `IMG_1234`).

    The edited version may have another extension than the original one (e.g. `IMG_1234.heic` and
    `IMG_E1234.jpg`). The one sharing the extension of the original picture is preferred.
    """
    edited_file_stem = _EDITED_PREFIX + file_path.stem.removeprefix(_ORIGINAL_PREFIX)
    edited_file_path = file_path.with_stem(edited_file_stem)
    if edited_file_path.is_file():
        return edited_file_path

    for edited_file_path in sorted(file_path.parent.glob(f"{glob.escape(edited_file_stem)}.*")):
        if get_file_type(edited_file_path) in _MERGEABLE_TYPES:
            return edited_file_path

    return None


def merge(folder: Path, dry_run: bool = False) -> None:
    """Merges duplicate files.

    Each original picture (`IMG_1234`) is replaced with its edited version (`IMG_E1234`) when both
    are found in the same folder. The merged picture keeps the name of the original one and the
    extension of the edited one.

    :param folder: folder containing the files to merge, scanned recursively.
    :param dry_run: whether to only log the merges instead of running them.
    """
    # Files are listed beforehand as merging removes and renames some of them
    file_paths = sorted(p for p in folder.rglob("*") if p.is_file())
    merged_files = 0
    for file_path in tqdm(file_paths, desc=f"Merging files in {folder}", disable=dry_run):
        file_stem = file_path.stem
        if not file_stem.startswith(_ORIGINAL_PREFIX) or file_stem.startswith(_EDITED_PREFIX):
            continue
        if get_file_type(file_path) not in _MERGEABLE_TYPES:
            continue

        edited_file_path = _find_edited_file(file_path)
        if edited_file_path is None:
            continue

        merged_file_path = file_path.with_suffix(edited_file_path.suffix)
        if dry_run:
            logger.info(f"Would replace '{file_path}' with '{edited_file_path}'")
        else:
            logger.debug(f"Replacing '{file_path}' with '{edited_file_path}'")
            if merged_file_path != file_path:
                file_path.unlink()
            edited_file_path.replace(merged_file_path)
        merged_files += 2

    if dry_run:
        logger.info(f"{merged_files} files would be merged in '{folder}'")
    else:
        logger.info(f"{merged_files} files have been merged in '{folder}'")


__all__ = ["clean", "create_structure", "merge", "move_files", "scan"]

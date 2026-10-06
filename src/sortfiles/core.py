import mimetypes
import re
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Final

from exifread import process_file
from loguru import logger
from tqdm import tqdm

mimetypes.init()


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
            case _:
                return None
    except ValueError:
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
        case _:
            # File type is unsupported: skip it
            return None


_EXIF_DATE_TAGS: Final = ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime")
"""EXIF tags holding a date, from the most to the least reliable.

`Image DateTime` is the last modification date: it is only used when the shooting date is missing.
"""


def _retrieve_creation_date_exif(file_path: Path) -> date:
    with file_path.open("rb") as file_path_stream:
        file_img_exif = process_file(file_path_stream)

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


type ScanResult = Mapping[date, Sequence[Path]]
type IterResult = tuple[Path, FileInfo]


def iterate(folder: Path, check_validity: bool = True) -> Iterator[IterResult]:
    """Iterates on a `folder` to retrieve files."""
    for file_path in folder.rglob("*"):
        file_path_relative = file_path.relative_to(folder)
        if not file_path.is_file() or (check_validity and not is_valid(file_path_relative)):
            logger.debug(f"Ignoring unsortable file '{file_path}'")
            continue

        file_info = get_file_information(file_path)
        if file_info is None:
            logger.warning(f"Unable to get information for file '{file_path}'")
            continue

        yield file_path, file_info


def scan(folder: Path) -> ScanResult:
    """Recursively scans a folder to sort.

    Files are grouped by date.
    """
    result: defaultdict[date, list[Path]] = defaultdict(list)
    for element_path, element_info in iterate(folder):
        element_creation_date = element_info.creation_date.replace(day=1)
        result[element_creation_date].append(element_path.relative_to(folder))

    return result


def create_structure(folder: Path, scan_result: ScanResult) -> None:
    """Creates structure from a scan result."""
    for scan_date in scan_result.keys():
        scan_date_folder = folder / str(scan_date.year) / str(scan_date.month).zfill(2)
        logger.debug(f"Creating folder '{scan_date_folder}'")
        scan_date_folder.mkdir(parents=True, exist_ok=True)


def _compute_scan_result_size(scan_result: ScanResult) -> int:
    return sum(len(p) for p in scan_result.values())


def move_files(folder: Path, scan_result: ScanResult, dry_run: bool = False) -> None:
    """Moves files of a scan.

    Structure must be created before running this function. If not, an error is raised.

    :param folder: folder to sort.
    :param scan_result: result of the scan of `folder`.
    :param dry_run: whether to only log the moves instead of running them. Structure is not required
    in this mode.
    """
    with tqdm(
        desc=f"Moving files in {folder}",
        total=_compute_scan_result_size(scan_result),
        disable=dry_run,
    ) as pbar:
        for scan_date, scan_elements in scan_result.items():
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


def clean(folder: Path, scan_result: ScanResult) -> None:
    """Cleans the folders left empty after moving files.

    Folders which still contain something (e.g. unsupported files) are kept, and `folder` itself is
    never removed. This function must be run after moving files.
    """
    for scan_elements in scan_result.values():
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


def _retrieve_deepest_subfolders(folder: Path) -> Iterator[Path]:
    """Retrieves the deepest subfolders within a root `folder`."""
    if not folder.is_dir():
        raise NotADirectoryError(f"'{folder}' is not a valid or existing folder")
    if not any(p.is_dir() for p in folder.iterdir()):
        yield folder
        return

    for path in folder.rglob("*/"):
        # Folder is at the bottom iff it doesn't contain any folder
        if not any(p.is_dir() for p in path.iterdir()):
            yield path


def merge(folder: Path, dry_run: bool = False) -> None:
    """Merges duplicate files.

    :param folder: folder containing the files to merge.
    :param dry_run: whether to only log the merges instead of running them.
    """
    for subfolder in _retrieve_deepest_subfolders(folder):
        logger.debug(f"Retrieving files from '{subfolder}'")
        merged_files = 0
        for file_path, file_info in tqdm(
            iterate(subfolder, check_validity=False),
            desc=f"Merging files in {subfolder}",
            disable=dry_run,
        ):
            match file_info.type:
                case ImageType.HEIC | ImageType.JPEG:
                    file_stem = file_path.stem
                    if file_stem.startswith("IMG_E"):
                        continue

                    new_file_stem = file_stem.removeprefix("IMG_")
                    new_file_stem = f"IMG_E{new_file_stem}"
                    new_file_path = file_path.with_stem(new_file_stem)
                    if new_file_path.exists():
                        if dry_run:
                            logger.info(f"Would replace '{file_path}' with '{new_file_path}'")
                        else:
                            logger.debug(f"Replacing '{file_path}' with '{new_file_path}'")
                            new_file_path.replace(file_path)
                        merged_files += 2

        if dry_run:
            logger.info(f"{merged_files} files would be merged in '{subfolder}'")
        else:
            logger.info(f"{merged_files} files have been merged in '{subfolder}'")


__all__ = ["clean", "create_structure", "iterate", "merge", "move_files", "scan"]

import mimetypes
import re
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Mapping, Sequence

from exifread import process_file
from loguru import logger
from tqdm import tqdm

mimetypes.init()


class FileType(Enum):
    """An enumeration of supported file types."""

    @classmethod
    def all(cls) -> set[str]:
        """Returns all file types."""
        return {ft.value for ft in cls}


class ImageType(FileType):
    """An enumeration of supported image types."""

    HEIC = "heic"
    JPG = "jpg"
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

    file_class, file_type = file_mimetype.split("/", maxsplit=1)
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

    if file_type is None:
        # File type is unsupported: skip it
        return None

    match file_type:
        case ImageType.JPG | ImageType.JPEG | ImageType.PNG | ImageType.HEIC | ImageType.RAW:
            try:
                return _retrieve_creation_date_exif(file_path)
            except ValueError:
                return _retrieve_creation_date_dummy(file_path)
        case VideoType.MOV | VideoType.MP4:
            return _retrieve_creation_date_dummy(file_path)
        case _:
            return None


def _retrieve_creation_date_exif(file_path: Path) -> date | None:
    with file_path.open("rb") as file_path_stream:
        file_img_exif = process_file(file_path_stream)

    try:
        file_creation_date = file_img_exif["Image DateTime"].values
    except KeyError as err:
        raise ValueError(
            f"Unable to extract creation date from EXIF for file '{file_path}'"
        ) from err

    for file_creation_date_format in ("%Y:%m:%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(file_creation_date, file_creation_date_format).date()
        except ValueError:
            pass

    raise ValueError(f"Unable to extract creation date from EXIF for file '{file_path}'")


def _retrieve_creation_date_dummy(file_path: Path) -> date:
    info = file_path.stat()
    return date.fromtimestamp(info.st_birthtime)


_YEAR_PATTERN: re.Pattern = re.compile(r"^[1-9][0-9]{3}$")
"""Year pattern.

Only years in the range [1000;9999] are valid.
"""
_MONTH_PATTERN: re.Pattern = re.compile(r"^(0[1-9])|(1[1-2])$")


def is_valid(path: Path) -> bool:
    """Checks whether a path is sortable or not.

    A path is sortable iff:

    * first path element is not a folder whose name is a valid year number;
    * second path element is not a folder whose name is a valid month number.
    """
    file_path_elements = path.parts
    if len(file_path_elements) < 2:  # noqa: PLR2004
        return True

    return (
        _YEAR_PATTERN.fullmatch(file_path_elements[0]) is None
        and _MONTH_PATTERN.fullmatch(file_path_elements[1]) is None
    )


type ScanResult = Mapping[date, Sequence[Path]]
type IterResult = tuple[Path, FileInfo]


def iterate(folder: Path, check_validity: bool = True) -> Iterator[IterResult]:
    """Iterates on a `folder` to retrieve files."""
    for element_path in folder.rglob("*"):
        file_path = element_path.relative_to(folder)
        if not element_path.is_file() or (check_validity and not is_valid(file_path)):
            logger.debug(f"Ignoring unsortable file '{element_path}'")
            continue

        element_info = get_file_information(element_path)
        if element_info is None:
            logger.warning(f"Unable to get information for file '{element_path}'")
            continue

        yield element_path, element_info


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


def move_files(folder: Path, scan_result: ScanResult) -> None:
    """Moves files of a scan.

    Structure must be created before running this function. If not, an error is raised.
    """
    with tqdm(
        desc=f"Moving files in {folder}", total=_compute_scan_result_size(scan_result)
    ) as pbar:
        for scan_date, scan_elements in scan_result.items():
            scan_date_folder = folder / str(scan_date.year) / str(scan_date.month).zfill(2)
            if not scan_date_folder.exists():
                raise OSError(f"Date folder '{scan_date_folder}' does not exist")

            for element_path in scan_elements:
                old_element_path = folder / element_path
                new_element_path = scan_date_folder / element_path
                new_element_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    old_element_path.rename(new_element_path)
                except FileExistsError:
                    old_element_path.unlink()

                # Update the progress after moving the file
                pbar.update()


def clean(folder: Path, scan_result: ScanResult) -> None:
    """Cleans empty folders.

    This function must be run after moving files. If ran before, OS errors should be expected.
    """
    for scan_elements in scan_result.values():
        for element_path in scan_elements:
            old_element_path = folder / element_path
            old_element_folder = old_element_path.parent
            if not old_element_folder.exists():
                continue

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


def merge(folder: Path) -> None:
    """Merges duplicate files."""
    for subfolder in _retrieve_deepest_subfolders(folder):
        logger.debug(f"Retrieving files from '{subfolder}'")
        merged_files = 0
        for file_path, file_info in tqdm(
            iterate(subfolder, check_validity=False), desc=f"Merging files in {subfolder}"
        ):
            match file_info.type:
                case ImageType.HEIC | ImageType.JPEG | ImageType.JPG:
                    file_stem = file_path.stem
                    if file_stem.startswith("IMG_E"):
                        continue

                    new_file_stem = file_stem.removeprefix("IMG_")
                    new_file_stem = f"IMG_E{new_file_stem}"
                    new_file_path = file_path.with_stem(new_file_stem)
                    if new_file_path.exists():
                        new_file_path.replace(file_path)

                    merged_files += 2

        logger.debug(f"{merged_files} files have been merged")


__all__ = ["create_structure", "move_files", "iterate", "scan", "merge"]

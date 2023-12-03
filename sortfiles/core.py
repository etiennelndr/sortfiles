import re
import shutil
from datetime import date
from pathlib import Path
from typing import Mapping, MutableMapping, MutableSequence, Sequence

from loguru import logger


def _retrieve_creation_date(fs_element: Path) -> date:
    """Retrieves the creation date of a filesystem element (file or folder).

    :param fs_element: element path.
    """
    if not fs_element.is_file() and not fs_element.is_dir():
        # This is an internal error, everyone is allowed to blame me
        raise ValueError("Creation date can only be retrieved from a file or folder")

    info = fs_element.stat()
    return date.fromtimestamp(info.st_mtime)


_YEAR_PATTERN: re.Pattern = re.compile(r"^[1-2][0-9]{3}$")
"""Year pattern.

Only years in the range [1000;2999] are valid.
"""
_MONTH_PATTERN: re.Pattern = re.compile(r"^(0[1-9])|(1[1-2])$")


def _sortable(path: Path) -> bool:
    """Checks whether a path is sortable or not.

    A path is sortable iff:

    * first path element is not a folder whose name is a valid year number;
    * second path element is not a folder whose name is a valid month number.
    """
    if path.is_absolute():
        # This is (also) an internal error, everyone is allowed to blame me
        raise ValueError("Unable to check whether an absolute file path is sortable or not")

    path_elements = path.parts
    if len(path_elements) < 3:
        return True

    return (
        _YEAR_PATTERN.fullmatch(path_elements[0]) is None
        and _MONTH_PATTERN.fullmatch(path_elements[1]) is None
    )


type ScanResult = Mapping[date, Sequence[Path]]


def scan(folder: Path) -> ScanResult:
    """Recursively scans a folder to sort.

    Files are grouped by date.
    """
    result: MutableMapping[date, MutableSequence[Path]] = {}
    for element in folder.rglob("*"):
        if not element.is_file():
            continue

        element_date = _retrieve_creation_date(element)
        element_date = date(element_date.year, element_date.month, 1)
        element = element.relative_to(folder)

        if not _sortable(element):
            logger.debug(f"Ignoring unsortable file '{element}'")
            continue

        date_elements = result.setdefault(element_date, [])
        date_elements.append(element)

    return result


def create_structure(folder: Path, scan_result: ScanResult) -> None:
    """Creates structure from a scan result."""
    for scan_date in scan_result.keys():
        scan_date_folder = folder / str(scan_date.year) / str(scan_date.month).zfill(2)
        logger.debug(f"Creating folder '{scan_date_folder}'")
        scan_date_folder.mkdir(parents=True, exist_ok=True)


def move_files(folder: Path, scan_result: ScanResult) -> None:
    """Moves files of a scan.

    Structure must be created before running this function. If not, an error is raised.
    """
    for scan_date, scan_elements in scan_result.items():
        scan_date_folder = folder / str(scan_date.year) / str(scan_date.month).zfill(2)
        if not scan_date_folder.exists():
            raise OSError("Date folder does not exist")

        for element_path in scan_elements:
            old_element_path = folder / element_path
            new_element_path = scan_date_folder / element_path
            new_element_path.parent.mkdir(parents=True, exist_ok=True)
            new_element_path.touch()
            logger.debug(f"Moving file '{old_element_path}' to '{new_element_path}'")
            shutil.move(old_element_path, new_element_path)


def clean(folder: Path, scan_result: ScanResult) -> None:
    """Cleans empty folders.

    This function can be run after moving files. If ran before, OS errors should be expected.
    """
    for scan_elements in scan_result.values():
        for element_path in scan_elements:
            old_element_path = folder / element_path
            old_element_folder = old_element_path.parent
            if not old_element_folder.exists():
                continue

            old_element_folder.rmdir()


__all__ = ["create_structure", "move_files", "scan"]

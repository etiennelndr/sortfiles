"""Sorting of pictures and videos by date."""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final

from loguru import logger
from tqdm import tqdm

from .dates import retrieve_file_creation_date

_YEAR_PATTERN: Final = re.compile(r"^[1-9][0-9]{3}$")
"""Year pattern.

Only years in the range [1000;9999] are valid.
"""
_MONTH_PATTERN: Final = re.compile(r"^(0[1-9]|1[0-2])$")


def is_valid(path: Path) -> bool:
    """Checks whether a path is sortable or not.

    A path is sortable iff it is not already sorted, i.e. it is not located in a year folder
    containing a month folder (e.g. `2024/10/...`).

    :param path: path relative to the folder to sort. Only its first two levels are checked.
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

        file_creation_date = retrieve_file_creation_date(file_path)
        if file_creation_date is None:
            logger.debug(f"Ignoring unsupported file '{file_path}'")
            result.unsupported_files.append(file_path_relative)
            continue

        result.files[file_creation_date.replace(day=1)].append(file_path_relative)

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


__all__ = ["ScanResult", "clean", "create_structure", "move_files", "scan"]

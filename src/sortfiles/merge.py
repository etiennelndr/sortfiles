"""Merge of duplicate pictures."""

import glob
from pathlib import Path
from typing import Final

from loguru import logger
from tqdm import tqdm

from .filetypes import ImageType, get_file_type

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


__all__ = ["merge"]

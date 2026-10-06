"""Helpers inspecting files."""

from pathlib import Path


def list_files(folder: Path) -> set[str]:
    """Lists the files of a folder.

    :param folder: folder to list, recursively.
    :return: POSIX paths of the files, relative to `folder`.
    """
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


__all__ = ["list_files"]

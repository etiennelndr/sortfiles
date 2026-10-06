"""Tests of the command line interface."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest
from click.testing import Result


def _list_files(folder: Path) -> set[str]:
    """Lists the files of a folder, as POSIX paths relative to it."""
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def test_sort(
    tmp_path: Path, make_file: Callable[..., Path], run_cli: Callable[..., Result]
) -> None:
    make_file("holidays/a.jpg", modified=date(2019, 6, 15))
    make_file("notes.txt")

    result = run_cli("sort", tmp_path)

    assert result.exit_code == 0
    assert _list_files(tmp_path) == {"2019/06/holidays/a.jpg", "notes.txt"}
    assert (tmp_path / "holidays").is_dir()


def test_sort_clean(
    tmp_path: Path, make_file: Callable[..., Path], run_cli: Callable[..., Result]
) -> None:
    make_file("holidays/a.jpg", modified=date(2019, 6, 15))

    result = run_cli("sort", tmp_path, "--clean")

    assert result.exit_code == 0
    assert _list_files(tmp_path) == {"2019/06/holidays/a.jpg"}
    assert not (tmp_path / "holidays").exists()


def test_sort_dry_run(
    tmp_path: Path, make_file: Callable[..., Path], run_cli: Callable[..., Result]
) -> None:
    make_file("holidays/a.jpg", modified=date(2019, 6, 15))

    result = run_cli("sort", tmp_path, "--clean", "--dry-run")

    assert result.exit_code == 0
    assert _list_files(tmp_path) == {"holidays/a.jpg"}
    assert not (tmp_path / "2019").exists()


def test_sort_without_file_to_sort(
    tmp_path: Path, make_file: Callable[..., Path], run_cli: Callable[..., Result]
) -> None:
    make_file("2019/06/a.jpg")
    make_file("notes.txt")

    result = run_cli("sort", tmp_path)

    assert result.exit_code == 0
    assert _list_files(tmp_path) == {"2019/06/a.jpg", "notes.txt"}


def test_merge(
    tmp_path: Path, make_file: Callable[..., Path], run_cli: Callable[..., Result]
) -> None:
    make_file("IMG_0001.jpg", b"original")
    make_file("IMG_E0001.jpg", b"edited")

    result = run_cli("merge", tmp_path)

    assert result.exit_code == 0
    assert _list_files(tmp_path) == {"IMG_0001.jpg"}
    assert (tmp_path / "IMG_0001.jpg").read_bytes() == b"edited"


def test_merge_dry_run(
    tmp_path: Path, make_file: Callable[..., Path], run_cli: Callable[..., Result]
) -> None:
    make_file("IMG_0001.jpg", b"original")
    make_file("IMG_E0001.jpg", b"edited")

    result = run_cli("merge", tmp_path, "--dry-run")

    assert result.exit_code == 0
    assert _list_files(tmp_path) == {"IMG_0001.jpg", "IMG_E0001.jpg"}


@pytest.mark.parametrize("command", ["sort", "merge"])
def test_missing_folder(tmp_path: Path, run_cli: Callable[..., Result], command: str) -> None:
    result = run_cli(command, tmp_path / "missing")

    assert result.exit_code == 2

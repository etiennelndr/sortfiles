"""Tests of the sorting of files."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from sortfiles.sort import ScanResult, clean, create_structure, is_valid, move_files, scan


def _list_files(folder: Path) -> set[str]:
    """Lists the files of a folder, as POSIX paths relative to it."""
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("picture.jpg", True),
        ("holidays/picture.jpg", True),
        ("2024/picture.jpg", True),
        ("2024/10/picture.jpg", False),
        ("2024/10/holidays/picture.jpg", False),
        ("2024/00/picture.jpg", True),
        ("2024/13/picture.jpg", True),
        ("2024/1/picture.jpg", True),
        ("0999/10/picture.jpg", True),
        ("holidays/2024/10/picture.jpg", True),
    ],
)
def test_is_valid(path: str, expected: bool) -> None:
    assert is_valid(Path(path)) is expected


def test_scan_groups_files_by_month(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("a.jpg", modified=date(2019, 6, 15))
    make_file("holidays/b.mp4", modified=date(2019, 6, 20))
    make_file("c.jpg", modified=date(2021, 3, 10))

    scan_result = scan(tmp_path)

    assert {month: sorted(paths) for month, paths in scan_result.files.items()} == {
        date(2019, 6, 1): [Path("a.jpg"), Path("holidays/b.mp4")],
        date(2021, 3, 1): [Path("c.jpg")],
    }
    assert scan_result.sorted_files == []
    assert scan_result.unsupported_files == []


def test_scan_reports_ignored_files(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("2020/01/a.jpg")
    make_file("notes.txt")
    make_file("orphan.aae")

    scan_result = scan(tmp_path)

    assert not scan_result.files
    assert scan_result.sorted_files == [Path("2020/01/a.jpg")]
    assert sorted(scan_result.unsupported_files) == [Path("notes.txt"), Path("orphan.aae")]


def test_create_structure(tmp_path: Path) -> None:
    scan_result = ScanResult(
        files={
            date(2019, 6, 1): [],
            date(2021, 11, 1): [],
        }
    )

    create_structure(tmp_path, scan_result)

    assert (tmp_path / "2019" / "06").is_dir()
    assert (tmp_path / "2021" / "11").is_dir()


def test_move_files_keeps_relative_path(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("a.jpg", modified=date(2019, 6, 15))
    make_file("holidays/b.jpg", modified=date(2021, 3, 10))
    scan_result = scan(tmp_path)
    create_structure(tmp_path, scan_result)

    files_count = move_files(tmp_path, scan_result)

    assert files_count == 2
    assert _list_files(tmp_path) == {"2019/06/a.jpg", "2021/03/holidays/b.jpg"}


def test_move_files_moves_sidecar_with_its_owner(
    tmp_path: Path, make_file: Callable[..., Path]
) -> None:
    make_file("a.jpg", modified=date(2019, 6, 15))
    make_file("a.aae")
    scan_result = scan(tmp_path)
    create_structure(tmp_path, scan_result)

    move_files(tmp_path, scan_result)

    assert _list_files(tmp_path) == {"2019/06/a.jpg", "2019/06/a.aae"}


def test_move_files_overwrites_existing_destination(
    tmp_path: Path, make_file: Callable[..., Path]
) -> None:
    make_file("2019/06/a.jpg", b"old")
    make_file("a.jpg", b"new", modified=date(2019, 6, 15))
    scan_result = scan(tmp_path)
    create_structure(tmp_path, scan_result)

    move_files(tmp_path, scan_result)

    assert _list_files(tmp_path) == {"2019/06/a.jpg"}
    assert (tmp_path / "2019" / "06" / "a.jpg").read_bytes() == b"new"


def test_move_files_requires_structure(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("a.jpg", modified=date(2019, 6, 15))
    scan_result = scan(tmp_path)

    with pytest.raises(OSError, match="does not exist"):
        move_files(tmp_path, scan_result)


def test_move_files_dry_run(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("a.jpg", modified=date(2019, 6, 15))
    scan_result = scan(tmp_path)

    files_count = move_files(tmp_path, scan_result, dry_run=True)

    assert files_count == 1
    assert _list_files(tmp_path) == {"a.jpg"}
    assert not (tmp_path / "2019").exists()


def test_clean_removes_empty_folders(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("a/b/c.jpg", modified=date(2019, 6, 15))
    scan_result = scan(tmp_path)
    create_structure(tmp_path, scan_result)
    move_files(tmp_path, scan_result)

    clean(tmp_path, scan_result)

    assert not (tmp_path / "a").exists()
    assert _list_files(tmp_path) == {"2019/06/a/b/c.jpg"}


def test_clean_keeps_non_empty_folders(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("a/b/c.jpg", modified=date(2019, 6, 15))
    make_file("a/notes.txt")
    scan_result = scan(tmp_path)
    create_structure(tmp_path, scan_result)
    move_files(tmp_path, scan_result)

    clean(tmp_path, scan_result)

    assert not (tmp_path / "a" / "b").exists()
    assert _list_files(tmp_path) == {"2019/06/a/b/c.jpg", "a/notes.txt"}


def test_clean_keeps_root_folder(tmp_path: Path, make_file: Callable[..., Path]) -> None:
    make_file("a.jpg", modified=date(2019, 6, 15))
    scan_result = scan(tmp_path)
    create_structure(tmp_path, scan_result)
    move_files(tmp_path, scan_result)

    clean(tmp_path, scan_result)

    assert _list_files(tmp_path) == {"2019/06/a.jpg"}

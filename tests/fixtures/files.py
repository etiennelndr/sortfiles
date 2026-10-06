"""Fixtures creating files."""

import os
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

import pytest


@pytest.fixture
def make_file(tmp_path: Path) -> Callable[..., Path]:
    """Returns a function creating a file in the temporary folder of the test."""

    def _make_file(
        relative_path: str, content: bytes = b"content", modified: date | None = None
    ) -> Path:
        """Creates a file.

        :param relative_path: path of the file, relative to the temporary folder.
        :param content: content of the file.
        :param modified: modification date of the file. It is today if not set.
        :return: path of the created file.
        """
        file_path = tmp_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        if modified is not None:
            timestamp = datetime(modified.year, modified.month, modified.day, 12).timestamp()
            os.utime(file_path, (timestamp, timestamp))

        return file_path

    return _make_file


__all__ = ["make_file"]

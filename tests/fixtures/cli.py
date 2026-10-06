"""Fixtures running the command line interface."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner, Result
from loguru import logger

from sortfiles.cli import main


@pytest.fixture
def run_cli() -> Iterator[Callable[..., Result]]:
    """Returns a function running the command line interface.

    Logging handlers set by the command line interface are removed after the test: they write to a
    stream which is closed as soon as a command returns.
    """

    def _run_cli(*args: str | Path) -> Result:
        """Runs the command line interface.

        :param args: arguments of the command line (e.g. `"sort", folder, "--clean"`).
        :return: result of the command, holding its exit code.
        """
        return CliRunner().invoke(main, [str(arg) for arg in args])

    yield _run_cli

    logger.remove()


__all__ = ["run_cli"]

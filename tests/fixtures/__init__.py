"""Fixtures shared by all tests."""

from .cli import run_cli
from .files import make_file

__all__ = ["make_file", "run_cli"]

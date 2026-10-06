import sys
from collections.abc import Sequence
from pathlib import Path
from typing import override

import click
from loguru import logger

from . import merge, sort


def _verbose_callback(_ctx: click.Context, _param: click.Parameter, value: bool) -> bool:
    """Configures logging given the value of the CLI's `verbose` flag."""
    logger_level = "DEBUG" if value else "INFO"
    # Remove default handlers
    logger.remove()
    logger.add(sys.stderr, level=logger_level)

    return value


class CLIGroup(click.Group):
    """A click group with default options attached to each command."""

    @override
    def add_command(self, cmd: click.Command, name: str | None = None) -> None:
        super().add_command(cmd, name)
        cmd.params.append(
            click.Option(
                ["--verbose", "-v"],
                is_flag=True,
                default=False,
                help="Use this flag to increase logging verbosity",
                callback=_verbose_callback,
                expose_value=False,
                is_eager=True,
            )
        )


@click.group("sortfiles", cls=CLIGroup)
def main() -> None:
    """Sorts pictures and videos by date."""


@main.command(name="sort", short_help="Sort files by date")
@click.argument(
    "folder",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--clean",
    "-c",
    type=bool,
    is_flag=True,
    default=False,
    help="Delete the old subfolders left empty after moving files",
)
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    default=False,
    help="Only log what would be moved, without modifying any file",
)
def main_sort(folder: Path, clean: bool, dry_run: bool) -> None:
    """Sorts pictures and videos of FOLDER by date.

    Each file is moved to a <year>/<month> subfolder of FOLDER, along with its sidecars. Files
    which are already sorted or unsupported are left untouched.
    """
    if not folder.is_dir():
        logger.error(f"Unable to sort files in unknown or invalid folder '{folder}'")
        sys.exit(1)

    logger.info(f"Sorting files in folder '{folder}'")
    logger.info("Scanning input folder to extract dates and files")
    scan_result = sort.scan(folder)
    ignored_summary = (
        f"{len(scan_result.sorted_files)} already sorted, "
        f"{len(scan_result.unsupported_files)} unsupported"
    )
    if not scan_result.files:
        logger.warning(f"No file to sort ({ignored_summary}), no further operations are required")
        return

    logger.info(f"Creating new structure in folder '{folder}'")
    if not dry_run:
        sort.create_structure(folder, scan_result)

    logger.info(f"Moving files in folder '{folder}'")
    files_count = sort.move_files(folder, scan_result, dry_run=dry_run)

    if clean:
        logger.info("Cleaning old subfolders")
        if not dry_run:
            sort.clean(folder, scan_result)
    else:
        logger.warning("Cleaning of old subfolders is disabled and should be carried out by you")

    folders_count = len(scan_result.files)
    if dry_run:
        logger.info(
            f"Dry run completed, no file has been modified: {files_count} file(s) would be moved "
            f"to {folders_count} folder(s), {ignored_summary}"
        )
    else:
        logger.success(
            f"File sorting successfully completed: {files_count} file(s) moved to "
            f"{folders_count} folder(s), {ignored_summary}"
        )


@main.command(name="merge", short_help="Merge duplicate files")
@click.argument(
    "folder",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    default=False,
    help="Only log what would be merged, without modifying any file",
)
def main_merge(folder: Path, dry_run: bool) -> None:
    """Merges duplicate pictures of FOLDER.

    Each original picture (IMG_1234) is replaced with its edited version (IMG_E1234) when both are
    found in the same folder.
    """
    if not folder.is_dir():
        logger.error(f"Unable to merge files in unknown or invalid folder '{folder}'")
        sys.exit(1)

    logger.info(f"Merging duplicate files in folder '{folder}'")
    merge.merge(folder, dry_run=dry_run)


def run(argv: Sequence[str] | None = None) -> None:
    """Runs application CLI."""
    if argv is None:
        # Exclude program name from the list of CLI arguments
        argv = sys.argv[1:]

    main.main(args=argv)


__all__ = ["run"]

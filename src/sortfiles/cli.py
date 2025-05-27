import sys
from pathlib import Path
from typing import Sequence, override

import click
from loguru import logger

from . import core


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
    pass


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
    help="Whether to delete old subfolders after moving files",
)
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    default=False,
    help="Whether to run in dry run mode (i.e. without file copy or deletion)",
)
def main_sort(folder: Path, clean: bool, dry_run: bool):
    """Sorts files by date."""
    if not folder.is_dir():
        logger.error(f"Unable to sort files in unknown or invalid folder '{folder}'")
        sys.exit(1)

    logger.info(f"Sorting files in folder '{folder}'")
    logger.info("Scanning input folder to extract dates and files")
    scan_result = core.scan(folder)
    if not scan_result:
        logger.warning("Scan result is empty, no further operations are required")
        return

    logger.info(f"Creating new structure in folder '{folder}'")
    if not dry_run:
        core.create_structure(folder, scan_result)

    logger.info(f"Moving files in folder '{folder}'")
    if not dry_run:
        core.move_files(folder, scan_result)

    if clean:
        logger.info("Cleaning old subfolders")
        if not dry_run:
            core.clean(folder, scan_result)
    else:
        logger.warning("Cleaning of old subfolders is disabled and should be carried out by you")

    logger.success("File sorting successfully completed")


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
    help="Whether to run in dry run mode (i.e. without file deletion)",
)
def main_merge(folder: Path, dry_run: bool) -> None:
    """Merges duplicate files."""
    if not folder.is_dir():
        logger.error(f"Unable to merge files in unknown or invalid folder '{folder}'")
        sys.exit(1)

    logger.info(f"Merging duplicate files in folder '{folder}'")
    logger.info("Scanning input folder to extract dates and files")
    if not dry_run:
        core.merge(folder)


def run(argv: Sequence[str] | None = None) -> None:
    """Runs application CLI."""
    if argv is None:
        # Exclude program name from the list of CLI arguments
        argv = sys.argv[1:]

    main.main(args=argv)


__all__ = ["run"]

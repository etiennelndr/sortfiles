import sys
from pathlib import Path
from typing import Sequence

import click
from loguru import logger

from . import core


@click.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--clean", "-c", type=bool, default=False)
def main(folder: Path, clean: bool):
    if not folder.is_dir():
        raise NotADirectoryError(f"Unable to sort files in unknown or invalid folder '{folder}'")

    logger.info(f"Sorting files in folder '{folder}'")
    logger.info(f"Scanning input folder to extract dates and files")
    scan_result = core.scan(folder)
    if not scan_result:
        logger.info(f"Scan result is empty, no further operations are required")
        return

    logger.info(f"Creating new structure before moving files")
    core.create_structure(folder, scan_result)
    logger.info(f"Moving files in previously created structure")
    core.move_files(folder, scan_result)

    if clean:
        logger.info("Cleaning old subfolders")
        core.clean(folder, scan_result)
    else:
        logger.info("Cleaning of old subfolders is disabled and should be carried out by you")


def run(argv: Sequence[str] | None = None) -> None:
    """Runs application CLI."""
    if argv is None:
        # Exclude program name from the list of CLI arguments
        argv = sys.argv[1:]

    main.main(args=argv)


__all__ = ["run"]

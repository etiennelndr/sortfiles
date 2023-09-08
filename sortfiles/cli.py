import os.path

import typer

from .core import (
    create_directories,
    move_files,
    move_files_to_correct_path,
    retrieve_all_files,
)


def run():
    cli_app = typer.Typer(name="sortfiles", no_args_is_help=True)
    cli_app.command(name="run", no_args_is_help=True)(_main)
    cli_app()


def _main(folder: str):
    if not os.path.isdir(folder):
        exit(
            "Error: this directory doesn't exist. Please create it or verify "
            "if you haven't made a mistake in the path."
        )

    elements = list()
    all_time = list()

    files_to_move = retrieve_all_files(folder, elements, all_time, [], False)
    move_files_to_correct_path(folder, all_time, files_to_move)
    create_directories(folder, all_time)
    move_files(folder, elements, all_time)


__all__ = ["run"]

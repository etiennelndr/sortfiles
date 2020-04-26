import os.path
import pathlib

import click

from .sortfiles import retrieve_all_files, move_files_to_correct_path, create_directories, move_files


@click.group()
def main():
    """
    Main method.
    """


@main.command()
@click.option("--folder", "-f", "folder", required=True)
def run(folder):
    if not os.path.isdir(folder):
        exit("Error: this directory doesn't exist. Please create it or verify "
             "if you haven't made a mistake in the path.")

    elements = list()
    all_time = list()

    files_to_move = retrieve_all_files(folder, elements, all_time, [], False)
    move_files_to_correct_path(folder, all_time, files_to_move)
    create_directories(folder, all_time)
    move_files(folder, elements, all_time)


if __name__ == "__main__":
    # Start the program
    main()

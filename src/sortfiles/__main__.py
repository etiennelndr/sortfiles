"""Application entrypoint."""

from . import cli


def main() -> None:
    """Runs the application."""
    cli.run()


if __name__ == "__main__":
    main()

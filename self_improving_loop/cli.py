"""Minimal command-line entrypoint for installation checks."""

from __future__ import annotations

import argparse

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="self-improving-loop",
        description="Rollback-first reliability layer for AI agents.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the installed package version and exit.",
    )
    args = parser.parse_args(argv)

    if args.version:
        print(f"self-improving-loop {__version__}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line entry point for the DianYi prototype."""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Sequence


SYSTEM_MODULES = ("gi", "Xlib")


def missing_system_modules() -> list[str]:
    """Return required system Python modules that cannot be imported."""
    missing: list[str] = []
    for module_name in SYSTEM_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
    return missing


def build_parser() -> argparse.ArgumentParser:
    """Build the prototype command-line parser."""
    parser = argparse.ArgumentParser(
        prog="dianyi",
        description="Offline English-to-Chinese selection translator",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check system dependencies and exit",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a dependency check while the capture service is under construction."""
    args = build_parser().parse_args(argv)
    missing = missing_system_modules()
    if missing:
        print("Missing system modules: " + ", ".join(missing))
        return 1
    if args.check:
        print("DianYi system dependencies are available.")
        return 0
    print("DianYi capture service is not enabled yet. Run with --check for now.")
    return 0


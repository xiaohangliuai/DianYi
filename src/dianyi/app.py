"""Command-line entry point for DianYi."""

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
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="dianyi",
        description="Offline English-to-Chinese word lookup",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check system dependencies and exit",
    )
    parser.add_argument(
        "--capture",
        action="store_true",
        help="run the interactive X11 word-lookup service",
    )
    parser.add_argument(
        "--install-dictionary",
        action="store_true",
        help="download, verify, and install the pinned ECDICT release",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run DianYi or one of its setup commands."""
    args = build_parser().parse_args(argv)
    missing = missing_system_modules()
    if missing:
        print("Missing system modules: " + ", ".join(missing))
        return 1
    if args.check:
        print("DianYi system dependencies are available.")
        return 0
    if args.capture:
        from dianyi.service import run_capture_service

        return run_capture_service()
    if args.install_dictionary:
        from dianyi.dictionary.install import install_dictionary

        result = install_dictionary()
        print(
            f"Installed {result.stats.entries} dictionary entries and "
            f"{result.stats.inflections} inflections at {result.database_path}"
        )
        return 0
    print("Run DianYi with --capture, or use --check to verify dependencies.")
    return 0

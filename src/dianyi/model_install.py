"""Verified installation of the pinned Argos English-to-Chinese model."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

from dianyi.dictionary.install import (
    AssetIntegrityError,
    RemoteAsset,
    download_verified,
    verify_asset,
)


ARGOS_MODEL_INDEX_COMMIT = "ff90de60728f7c1338ff6b75974e4c89b2442d22"
ARGOS_MODEL_VERSION = "1.9"
ARGOS_MODEL_ASSET = RemoteAsset(
    url="https://argos-net.com/v1/translate-en_zh-1_9.argosmodel",
    size=70_743_021,
    sha256="433e7c4f034d87fbe2353161e05f18646d7999452f801a4e1f0378522b9850ab",
)


class ArgosRuntimeUnavailableError(RuntimeError):
    """Raised when the pinned Argos Python runtime is not installed."""


@dataclass(frozen=True, slots=True)
class ModelInstallResult:
    archive_path: Path
    version: str
    already_installed: bool


def default_model_cache_path() -> Path:
    """Return the XDG cache path for the verified model archive."""
    cache_home = os.environ.get("XDG_CACHE_HOME")
    root = Path(cache_home).expanduser() if cache_home else Path.home() / ".cache"
    return root / "dianyi" / "translate-en_zh-1_9.argosmodel"


def _load_package_module() -> Any:
    """Import the separately installed Argos runtime."""
    try:
        from argostranslate import package
    except ImportError as error:
        raise ArgosRuntimeUnavailableError(
            "Argos Translate 1.11.0 is not installed"
        ) from error
    return package


def _ensure_model_archive(
    destination: Path,
    asset: RemoteAsset,
    opener: Callable[[str], Any],
) -> Path:
    """Reuse a verified archive or atomically download its replacement."""
    if destination.is_file():
        try:
            verify_asset(destination, asset)
            return destination
        except AssetIntegrityError:
            pass
    return download_verified(asset, destination, opener=opener)


def install_translation_model(
    *,
    cache_path: str | Path | None = None,
    asset: RemoteAsset = ARGOS_MODEL_ASSET,
    opener: Callable[[str], Any] = urlopen,
    package_loader: Callable[[], Any] = _load_package_module,
) -> ModelInstallResult:
    """Download, verify, and install the pinned Argos language model."""
    destination = (
        Path(cache_path).expanduser().resolve()
        if cache_path is not None
        else default_model_cache_path()
    )
    archive = _ensure_model_archive(destination, asset, opener)
    package_module = package_loader()
    installed = package_module.get_installed_packages()
    matching = any(
        package.from_code == "en"
        and package.to_code == "zh"
        and package.package_version == ARGOS_MODEL_VERSION
        for package in installed
    )
    if not matching:
        package_module.install_from_path(archive)
    return ModelInstallResult(
        archive_path=archive,
        version=ARGOS_MODEL_VERSION,
        already_installed=matching,
    )


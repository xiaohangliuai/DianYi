"""Download, verify, and install the pinned ECDICT release."""

from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

from dianyi.dictionary.importer import (
    ECDICT_COMMIT,
    ECDICT_CSV_URL,
    ECDICT_RELEASE,
    ImportStats,
    import_ecdict_csv,
)
from dianyi.dictionary.lookup import default_database_path


@dataclass(frozen=True, slots=True)
class RemoteAsset:
    url: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class DictionaryInstallResult:
    database_path: Path
    license_path: Path
    stats: ImportStats


class AssetIntegrityError(RuntimeError):
    """Raised when downloaded bytes do not match the pinned asset."""


ECDICT_CSV_ASSET = RemoteAsset(
    url=ECDICT_CSV_URL,
    size=65_936_699,
    sha256="d0ce61e560b50d9905d20de3173aa3ca80950ce235bedd21c53e025cf9f38cb0",
)
ECDICT_LICENSE_ASSET = RemoteAsset(
    url=(
        "https://raw.githubusercontent.com/skywind3000/ECDICT/"
        f"{ECDICT_COMMIT}/LICENSE"
    ),
    size=1_063,
    sha256="ebd1186ec36c0dba6bb2d77cc59b0b292d4429b1dbe19c39bd0eab121ec73369",
)


def default_cache_path() -> Path:
    """Return the XDG cache path for the pinned source CSV."""
    cache_home = os.environ.get("XDG_CACHE_HOME")
    root = Path(cache_home).expanduser() if cache_home else Path.home() / ".cache"
    return root / "dianyi" / f"ecdict-{ECDICT_RELEASE}.csv"


def sha256_file(path: str | Path) -> str:
    """Calculate a file's SHA-256 without loading it into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_asset(path: str | Path, asset: RemoteAsset) -> None:
    """Verify both the exact byte size and SHA-256 of a local asset."""
    asset_path = Path(path)
    actual_size = asset_path.stat().st_size
    if actual_size != asset.size:
        raise AssetIntegrityError(
            f"asset size mismatch: expected {asset.size}, got {actual_size}"
        )
    actual_digest = sha256_file(asset_path)
    if not hmac.compare_digest(actual_digest, asset.sha256):
        raise AssetIntegrityError("asset SHA-256 mismatch")


def download_verified(
    asset: RemoteAsset,
    destination: str | Path,
    *,
    opener: Callable[[str], Any] = urlopen,
) -> Path:
    """Download and verify an asset before atomically replacing its target."""
    destination_path = Path(destination).expanduser().resolve()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = tempfile.NamedTemporaryFile(
        prefix=f".{destination_path.name}.",
        suffix=".download",
        dir=destination_path.parent,
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    try:
        with temporary_file, opener(asset.url) as response:
            digest = hashlib.sha256()
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > asset.size:
                    raise AssetIntegrityError("download exceeded pinned asset size")
                temporary_file.write(chunk)
                digest.update(chunk)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if total != asset.size:
            raise AssetIntegrityError(
                f"asset size mismatch: expected {asset.size}, got {total}"
            )
        if not hmac.compare_digest(digest.hexdigest(), asset.sha256):
            raise AssetIntegrityError("asset SHA-256 mismatch")
        os.replace(temporary_path, destination_path)
        return destination_path
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _ensure_asset(
    asset: RemoteAsset,
    destination: Path,
    opener: Callable[[str], Any],
) -> Path:
    """Reuse a verified cached asset or replace it with a verified download."""
    if destination.is_file():
        try:
            verify_asset(destination, asset)
            return destination
        except AssetIntegrityError:
            pass
    return download_verified(asset, destination, opener=opener)


def install_dictionary(
    *,
    database_path: str | Path | None = None,
    cache_path: str | Path | None = None,
    csv_asset: RemoteAsset = ECDICT_CSV_ASSET,
    license_asset: RemoteAsset = ECDICT_LICENSE_ASSET,
    opener: Callable[[str], Any] = urlopen,
) -> DictionaryInstallResult:
    """Install the pinned ECDICT data and license for offline lookup."""
    target = (
        Path(database_path).expanduser().resolve()
        if database_path is not None
        else default_database_path()
    )
    cache = (
        Path(cache_path).expanduser().resolve()
        if cache_path is not None
        else default_cache_path()
    )
    source = _ensure_asset(csv_asset, cache, opener)
    license_path = _ensure_asset(
        license_asset,
        target.parent / "ECDICT-LICENSE",
        opener,
    )
    stats = import_ecdict_csv(source, target)
    return DictionaryInstallResult(
        database_path=target,
        license_path=license_path,
        stats=stats,
    )


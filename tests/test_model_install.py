from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from dianyi.dictionary.install import RemoteAsset
from dianyi.model_install import (
    ARGOS_MODEL_VERSION,
    install_translation_model,
)


MODEL_DATA = b"verified model archive"


class Response(io.BytesIO):
    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class FakePackageModule:
    def __init__(self, installed: list[object]) -> None:
        self.installed = installed
        self.install_calls: list[Path] = []

    def get_installed_packages(self) -> list[object]:
        return self.installed

    def install_from_path(self, path: Path) -> None:
        self.install_calls.append(path)


class ModelInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.temporary_directory.name) / "model.argosmodel"
        self.asset = RemoteAsset(
            url="https://example.test/model",
            size=len(MODEL_DATA),
            sha256=hashlib.sha256(MODEL_DATA).hexdigest(),
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_downloads_verified_archive_and_installs_model(self) -> None:
        package_module = FakePackageModule([])

        result = install_translation_model(
            cache_path=self.cache_path,
            asset=self.asset,
            opener=lambda _url: Response(MODEL_DATA),
            package_loader=lambda: package_module,
        )

        self.assertFalse(result.already_installed)
        self.assertEqual(result.version, ARGOS_MODEL_VERSION)
        self.assertEqual(package_module.install_calls, [self.cache_path])
        self.assertEqual(self.cache_path.read_bytes(), MODEL_DATA)

    def test_does_not_reinstall_matching_model(self) -> None:
        self.cache_path.write_bytes(MODEL_DATA)
        installed = SimpleNamespace(
            from_code="en",
            to_code="zh",
            package_version=ARGOS_MODEL_VERSION,
        )
        package_module = FakePackageModule([installed])

        result = install_translation_model(
            cache_path=self.cache_path,
            asset=self.asset,
            opener=lambda _url: self.fail("valid cache should be reused"),
            package_loader=lambda: package_module,
        )

        self.assertTrue(result.already_installed)
        self.assertEqual(package_module.install_calls, [])

    def test_other_model_version_does_not_satisfy_pin(self) -> None:
        self.cache_path.write_bytes(MODEL_DATA)
        installed = SimpleNamespace(
            from_code="en",
            to_code="zh",
            package_version="1.8",
        )
        package_module = FakePackageModule([installed])

        install_translation_model(
            cache_path=self.cache_path,
            asset=self.asset,
            package_loader=lambda: package_module,
        )

        self.assertEqual(package_module.install_calls, [self.cache_path])


if __name__ == "__main__":
    unittest.main()

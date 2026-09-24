from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from dianyi.dictionary.install import (
    AssetIntegrityError,
    RemoteAsset,
    download_verified,
    install_dictionary,
    sha256_file,
    verify_asset,
)
from dianyi.dictionary.lookup import lookup_word


CSV_DATA = (
    "word,phonetic,definition,translation,pos,collins,oxford,tag,bnc,frq,"
    "exchange,detail,audio\n"
    "run,rʌn,,vi. 跑,v,,,,500,400,i:running,,\n"
).encode()
LICENSE_DATA = b"test license\n"


def asset(url: str, content: bytes) -> RemoteAsset:
    return RemoteAsset(
        url=url,
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


class Response(io.BytesIO):
    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class DictionaryInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_download_verifies_before_replacing_destination(self) -> None:
        destination = self.root / "asset"
        expected = asset("https://example.test/asset", b"correct")

        download_verified(
            expected,
            destination,
            opener=lambda _url: Response(b"correct"),
        )

        self.assertEqual(destination.read_bytes(), b"correct")
        verify_asset(destination, expected)
        self.assertEqual(sha256_file(destination), expected.sha256)

    def test_bad_download_preserves_existing_destination(self) -> None:
        destination = self.root / "asset"
        destination.write_bytes(b"existing")
        expected = asset("https://example.test/asset", b"correct")

        with self.assertRaises(AssetIntegrityError):
            download_verified(
                expected,
                destination,
                opener=lambda _url: Response(b"wrong!!"),
            )

        self.assertEqual(destination.read_bytes(), b"existing")

    def test_rejects_wrong_size_before_hash(self) -> None:
        path = self.root / "asset"
        path.write_bytes(b"short")

        with self.assertRaisesRegex(AssetIntegrityError, "size mismatch"):
            verify_asset(path, asset("unused", b"longer content"))

    def test_installs_dictionary_and_license_from_verified_assets(self) -> None:
        csv_asset = asset("https://example.test/data", CSV_DATA)
        license_asset = asset("https://example.test/license", LICENSE_DATA)
        payloads = {
            csv_asset.url: CSV_DATA,
            license_asset.url: LICENSE_DATA,
        }
        database = self.root / "data/dictionary.sqlite3"

        result = install_dictionary(
            database_path=database,
            cache_path=self.root / "cache/ecdict.csv",
            csv_asset=csv_asset,
            license_asset=license_asset,
            opener=lambda url: Response(payloads[url]),
        )

        entry = lookup_word("running", database_path=database)
        assert entry is not None
        self.assertEqual(entry.headword, "run")
        self.assertEqual(result.stats.entries, 1)
        self.assertEqual(result.license_path.read_bytes(), LICENSE_DATA)

    def test_reuses_valid_cached_csv_without_redownloading_it(self) -> None:
        csv_asset = asset("https://example.test/data", CSV_DATA)
        license_asset = asset("https://example.test/license", LICENSE_DATA)
        cached_csv = self.root / "cache/ecdict.csv"
        cached_csv.parent.mkdir()
        cached_csv.write_bytes(CSV_DATA)
        opened_urls: list[str] = []

        def opener(url: str) -> Response:
            opened_urls.append(url)
            return Response(LICENSE_DATA)

        install_dictionary(
            database_path=self.root / "data/dictionary.sqlite3",
            cache_path=cached_csv,
            csv_asset=csv_asset,
            license_asset=license_asset,
            opener=opener,
        )

        self.assertEqual(opened_urls, [license_asset.url])


if __name__ == "__main__":
    unittest.main()

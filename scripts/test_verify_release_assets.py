import stat
import sys
import tempfile
import unittest
import zipfile
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_release_assets import (  # noqa: E402
    detect_network_apis,
    detect_network_hosts,
    scan_network_access,
    validate_archive,
    validate_url,
    verify,
)


class ReleaseArchiveTests(unittest.TestCase):
    def archive(self, entries: list[tuple[zipfile.ZipInfo | str, bytes]]) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "mod.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for name, contents in entries:
                archive.writestr(name, contents)
        return path

    def test_accepts_plugin_archive(self) -> None:
        validate_archive(self.archive([("plugin.dll", b"plugin")]))

    def test_rejects_zip_slip(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsafe entry"):
            validate_archive(self.archive([("../plugin.dll", b"plugin")]))

    def test_rejects_symlink(self) -> None:
        entry = zipfile.ZipInfo("plugin.dll")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaisesRegex(ValueError, "unsafe entry"):
            validate_archive(self.archive([(entry, b"target")]))

    def test_rejects_paths_that_collide_after_normalization(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate entry"):
            validate_archive(
                self.archive(
                    [
                        ("plugins\\plugin.dll", b"one"),
                        ("plugins/plugin.dll", b"two"),
                    ]
                )
            )

    def test_requires_plugin_dll(self) -> None:
        with self.assertRaisesRegex(ValueError, "no plugin DLL"):
            validate_archive(self.archive([("readme.txt", b"text")]))

    def test_accepts_network_free_plugin_declaration(self) -> None:
        scan_network_access(
            self.archive([("plugin.dll", b"ordinary plugin bytes")]),
            False,
            set(),
        )

    def test_rejects_undeclared_network_api(self) -> None:
        archive = self.archive([("plugin.dll", b"System.Net.Http\0HttpClient")])
        with self.assertRaisesRegex(ValueError, "network APIs were detected"):
            scan_network_access(archive, False, set())

    def test_rejects_undeclared_remote_host(self) -> None:
        archive = self.archive([("plugin.dll", b"https://telemetry.example.com/events")])
        with self.assertRaisesRegex(ValueError, "usesNetwork is false"):
            scan_network_access(archive, False, set())

    def test_accepts_declared_api_and_host(self) -> None:
        archive = self.archive(
            [("plugin.dll", b"System.Net.Http HttpClient https://api.example.com/v1")]
        )
        apis, hosts = scan_network_access(archive, True, {"api.example.com"})
        self.assertIn("HttpClient", apis["plugin.dll"])
        self.assertEqual(hosts["plugin.dll"], {"api.example.com"})

    def test_rejects_host_missing_from_allowlist(self) -> None:
        archive = self.archive([("plugin.dll", b"https://other.example.com/v1")])
        with self.assertRaisesRegex(ValueError, "undeclared remote hosts"):
            scan_network_access(archive, True, {"api.example.com"})

    def test_detects_utf16_network_metadata(self) -> None:
        binary = "System.Net.Sockets https://api.example.com".encode("utf-16-le")
        self.assertIn("System.Net.Sockets", detect_network_apis(binary))
        self.assertEqual(detect_network_hosts(binary), {"api.example.com"})

    def test_rejects_non_github_download_hosts(self) -> None:
        with self.assertRaisesRegex(ValueError, "untrusted release redirect"):
            validate_url("https://example.com/mod.zip")

    def test_stages_verified_bytes_under_a_deterministic_tag(self) -> None:
        source = self.archive([("plugin.dll", b"plugin")])
        digest = sha256(source.read_bytes()).hexdigest()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        definition = root / "mod.json"
        definition.write_text(
            "{"
            '"modId":"author.mod",'
            '"version":"1.2.3",'
            '"networkAccess":{"usesNetwork":false,"allowedHosts":[]},'
            '"release":{'
            '"repository":"author/mod",'
            '"tag":"v1.2.3",'
            '"asset":"author.mod.zip",'
            f'"sha256":"{digest}"'
            "}}",
            encoding="utf-8",
        )

        def copy_download(_url: str, destination: Path) -> str:
            destination.write_bytes(source.read_bytes())
            return digest

        with patch("verify_release_assets.download", side_effect=copy_download):
            tag, asset, staged = verify(definition, root / "staged")

        self.assertEqual(tag, "mod-author.mod-v1.2.3")
        self.assertEqual(asset, "author.mod.zip")
        self.assertEqual(staged.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()

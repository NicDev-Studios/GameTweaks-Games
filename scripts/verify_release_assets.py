#!/usr/bin/env python3
"""Verify untrusted upstream mod ZIPs without extracting or executing them."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import shutil
import ssl
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_ENTRIES = 1_000
MAX_REDIRECTS = 5
ALLOWED_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-releases.githubusercontent.com",
}
REPOSITORY = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$"
)
RELEASE_PART = re.compile(r"^[A-Za-z0-9._+-]{1,180}$")
ASSET = re.compile(r"^[A-Za-z0-9._+-]+\.zip$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,96}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def fail(message: str) -> None:
    raise ValueError(message)


def validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        fail(f"untrusted release redirect: {parsed.hostname or 'unknown'}")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        fail("release URL contains forbidden authority data")


def download(url: str, destination: Path) -> str:
    context = ssl.create_default_context()
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        validate_url(current)
        parsed = urlsplit(current)
        connection = http.client.HTTPSConnection(
            parsed.hostname, parsed.port or 443, timeout=30, context=context
        )
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
        connection.request("GET", path, headers={"User-Agent": "GameTweaks-Catalog/1"})
        response = connection.getresponse()
        if response.status in (301, 302, 303, 307, 308):
            location = response.getheader("Location")
            response.read()
            connection.close()
            if not location:
                fail("release redirect had no destination")
            current = urljoin(current, location)
            continue
        if response.status != 200:
            response.read()
            connection.close()
            fail(f"release download failed with HTTP {response.status}")
        length = response.getheader("Content-Length")
        if length and int(length) > MAX_ARCHIVE_BYTES:
            fail("release ZIP exceeds the compressed size limit")
        digest = hashlib.sha256()
        downloaded = 0
        with destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                downloaded += len(chunk)
                if downloaded > MAX_ARCHIVE_BYTES:
                    fail("release ZIP exceeds the compressed size limit")
                digest.update(chunk)
                output.write(chunk)
        connection.close()
        return digest.hexdigest()
    fail("release download exceeded the redirect limit")


def validate_archive(path: Path) -> None:
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        fail(f"release asset is not a valid ZIP: {error}")
    with archive:
        entries = archive.infolist()
        if not entries or len(entries) > MAX_ENTRIES:
            fail("release ZIP has an invalid entry count")
        paths: set[str] = set()
        total = 0
        has_dll = False
        for entry in entries:
            name = entry.filename.replace("\\", "/")
            parts = name.split("/")
            if entry.is_dir() and parts[-1:] == [""]:
                parts.pop()
            mode = entry.external_attr >> 16
            if (
                entry.flag_bits & 1
                or "\0" in name
                or name.startswith("/")
                or re.match(r"^[A-Za-z]:", name)
                or not parts
                or any(part in ("", ".", "..") for part in parts)
                or (mode & 0o170000) == 0o120000
            ):
                fail(f"release ZIP contains an unsafe entry: {name}")
            if name in paths:
                fail(f"release ZIP contains a duplicate entry: {name}")
            paths.add(name)
            total += entry.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                fail("release ZIP exceeds the uncompressed size limit")
            if not entry.is_dir() and name.lower().endswith(".dll"):
                has_dll = True
        if not has_dll:
            fail("release ZIP contains no plugin DLL")


def definitions(root: Path, selected: list[str]) -> list[Path]:
    if not selected:
        return sorted(root.glob("games/*/mods/*.json"))
    result = []
    for relative in selected:
        if not re.fullmatch(r"games/[0-9]+/mods/[A-Za-z0-9._-]+\.json", relative):
            fail(f"invalid mod definition path: {relative}")
        path = root / relative
        if path.is_file():
            result.append(path)
    return result


def verify(definition_path: Path, output_dir: Path | None) -> tuple[str, str, Path] | None:
    data = json.loads(definition_path.read_text(encoding="utf-8"))
    mod_id = data.get("modId", "")
    version = data.get("version", "")
    release = data.get("release", {})
    repository = release.get("repository", "")
    tag = release.get("tag", "")
    asset = release.get("asset", "")
    expected = release.get("sha256", "")
    if not IDENTIFIER.fullmatch(mod_id) or not RELEASE_PART.fullmatch(version):
        fail(f"invalid mod ID or version in {definition_path}")
    if not REPOSITORY.fullmatch(repository):
        fail(f"invalid upstream repository in {definition_path}")
    if (
        not RELEASE_PART.fullmatch(tag)
        or not ASSET.fullmatch(asset)
        or len(asset) > 180
    ):
        fail(f"invalid upstream release in {definition_path}")
    if not SHA256.fullmatch(expected):
        fail(f"invalid release digest in {definition_path}")

    url = (
        f"https://github.com/{repository}/releases/download/"
        f"{quote(tag, safe='')}/{quote(asset, safe='')}"
    )
    with tempfile.TemporaryDirectory(prefix="gametweaks-verify-") as temporary:
        archive = Path(temporary) / asset
        actual = download(url, archive)
        if actual != expected:
            fail(f"release digest mismatch in {definition_path}: expected {expected}, got {actual}")
        validate_archive(archive)
        if output_dir is not None:
            target_tag = f"mod-{mod_id}-v{version}"
            if not RELEASE_PART.fullmatch(target_tag):
                fail(f"generated catalog release tag is invalid for {definition_path}")
            target = output_dir / target_tag / asset
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(archive, target)
            return target_tag, asset, target
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--definition", action="append", default=[])
    args = parser.parse_args()
    root = args.catalog_root.resolve()
    output = args.output_dir.resolve() if args.output_dir else None
    if args.manifest and output is None:
        parser.error("--manifest requires --output-dir")
    rows = []
    for path in definitions(root, args.definition):
        print(f"Verifying {path.relative_to(root)}")
        row = verify(path, output)
        if row:
            rows.append(row)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            "".join(f"{tag}\t{asset}\t{path}\n" for tag, asset, path in rows),
            encoding="utf-8",
        )
    print(f"Verified {len(definitions(root, args.definition))} release asset(s).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Release verification failed: {error}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""Verify untrusted mod ZIPs and declared source provenance without executing them."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
import os
import re
import shutil
import ssl
import subprocess
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
SOURCE_COMMIT = re.compile(r"^[a-f0-9]{40}$")
WORKFLOW = re.compile(r"^\.github/workflows/[A-Za-z0-9._-]+\.ya?ml$")
NETWORK_HOST = re.compile(
    r"^(?:(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.)+[a-z][a-z0-9-]{1,62}$"
)
URL = re.compile(r"(?i)\b(?:https?|wss?)://[^\s\x00\"'<>]{1,2048}")
BARE_DOMAIN = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z][a-z0-9-]{1,62}(?![A-Za-z0-9_.-])"
)
IPV4 = re.compile(r"(?<![0-9.])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9.])")
PRINTABLE_ASCII = re.compile(rb"[\x20-\x7e]{4,}")
PRINTABLE_UTF16_LE = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")
NETWORK_API_INDICATORS = {
    "System.Net.Http": (b"System.Net.Http",),
    "System.Net.Sockets": (b"System.Net.Sockets",),
    "HttpClient": (b"HttpClient",),
    "HttpWebRequest": (b"HttpWebRequest",),
    "WebRequest": (b"WebRequest",),
    "WebClient": (b"WebClient",),
    "TcpClient": (b"TcpClient",),
    "UdpClient": (b"UdpClient",),
    "ClientWebSocket": (b"ClientWebSocket",),
    "Dns.GetHost": (b"GetHostAddresses", b"GetHostEntry"),
    "WinHTTP": (b"winhttp.dll", b"WinHttpOpen", b"WinHttpConnect"),
    "WinINet": (b"wininet.dll", b"InternetOpen", b"InternetConnect"),
    "URLMon": (b"urlmon.dll", b"URLDownloadToFile"),
    "libcurl": (b"libcurl", b"curl_easy_init", b"curl_easy_perform"),
}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


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
            basename = parts[-1].lower()
            if (
                not entry.is_dir()
                and basename.startswith("gametweaks.agent.")
                and basename.endswith(".dll")
            ):
                fail(f"release ZIP contains a shared Agent assembly: {name}")
            total += entry.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                fail("release ZIP exceeds the uncompressed size limit")
            if not entry.is_dir() and name.lower().endswith(".dll"):
                has_dll = True
        if not has_dll:
            fail("release ZIP contains no plugin DLL")


def parse_network_access(data: dict, definition_path: Path) -> tuple[bool, set[str]]:
    network = data.get("networkAccess")
    if not isinstance(network, dict) or set(network) - {"usesNetwork", "allowedHosts", "purpose"}:
        fail(f"invalid networkAccess declaration in {definition_path}")
    uses_network = network.get("usesNetwork")
    allowed = network.get("allowedHosts")
    if not isinstance(uses_network, bool) or not isinstance(allowed, list):
        fail(f"invalid networkAccess declaration in {definition_path}")
    if any(not isinstance(host, str) for host in allowed):
        fail(f"invalid network host in {definition_path}")
    normalized = [host.lower() for host in allowed]
    if len(normalized) != len(set(normalized)) or len(normalized) > 32:
        fail(f"duplicate or excessive network hosts in {definition_path}")
    for host in normalized:
        if host in LOCAL_HOSTS or not valid_remote_host(host):
            fail(f"invalid remote network host in {definition_path}: {host}")
    purpose = network.get("purpose")
    if uses_network:
        if not normalized or not valid_localized_purpose(purpose):
            fail(f"network access needs allowedHosts and a purpose in {definition_path}")
    elif normalized or purpose is not None:
        fail(f"networkAccess must be empty when usesNetwork is false in {definition_path}")
    return uses_network, set(normalized)


def parse_source_provenance(
    data: dict,
    release: dict,
    definition_path: Path,
) -> dict[str, str] | None:
    official = data.get("official")
    if not isinstance(official, bool):
        fail(f"invalid official status in {definition_path}")
    source = data.get("source")
    if source is None:
        if official:
            fail(f"Official mod has no source provenance in {definition_path}")
        return None
    if not isinstance(source, dict) or set(source) != {
        "repository",
        "tag",
        "commit",
        "workflow",
    }:
        fail(f"invalid source provenance in {definition_path}")
    repository = source.get("repository")
    tag = source.get("tag")
    commit = source.get("commit")
    workflow = source.get("workflow")
    if (
        not isinstance(repository, str)
        or not REPOSITORY.fullmatch(repository)
        or not isinstance(tag, str)
        or not RELEASE_PART.fullmatch(tag)
        or not isinstance(commit, str)
        or not SOURCE_COMMIT.fullmatch(commit)
        or not isinstance(workflow, str)
        or len(workflow) > 180
        or not WORKFLOW.fullmatch(workflow)
        or repository != release.get("repository")
        or tag != release.get("tag")
    ):
        fail(f"invalid source provenance in {definition_path}")
    return {
        "repository": repository,
        "tag": tag,
        "commit": commit,
        "workflow": workflow,
    }


def verify_source_provenance(archive: Path, source: dict[str, str]) -> None:
    repository = source["repository"]
    tag = source["tag"]
    commit = source["commit"]
    workflow = source["workflow"]
    try:
        resolved = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repository}/commits/{quote(tag, safe='')}",
                "--jq",
                ".sha",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        if resolved != commit:
            fail("the declared source tag does not resolve to the declared commit")
        subprocess.run(
            [
                "gh",
                "attestation",
                "verify",
                str(archive),
                "--repo",
                repository,
                "--signer-workflow",
                f"{repository}/{workflow}",
                "--source-digest",
                commit,
                "--source-ref",
                f"refs/tags/{tag}",
                "--deny-self-hosted-runners",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        fail("GitHub CLI is required to verify source provenance")
    except subprocess.TimeoutExpired:
        fail("source provenance verification timed out")
    except subprocess.CalledProcessError:
        fail("source provenance or artifact attestation verification failed")


def valid_remote_host(host: str) -> bool:
    if NETWORK_HOST.fullmatch(host):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.version == 4 and not address.is_loopback and not address.is_unspecified


def valid_localized_purpose(value: object) -> bool:
    if not isinstance(value, dict) or set(value) - {"en", "de"}:
        return False
    if not isinstance(value.get("en"), str) or not value["en"].strip():
        return False
    return all(isinstance(text, str) and 0 < len(text.strip()) <= 512 for text in value.values())


def scan_network_access(
    archive_path: Path,
    uses_network: bool,
    allowed_hosts: set[str],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    api_findings: dict[str, set[str]] = {}
    host_findings: dict[str, set[str]] = {}
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or not entry.filename.lower().endswith(".dll"):
                continue
            binary = archive.read(entry)
            apis = detect_network_apis(binary)
            hosts = detect_network_hosts(binary)
            if apis:
                api_findings[entry.filename] = apis
            if hosts:
                host_findings[entry.filename] = hosts

    detected_hosts = set().union(*host_findings.values()) if host_findings else set()
    if not uses_network and api_findings:
        fail("network APIs were detected but networkAccess.usesNetwork is false: " + format_findings(api_findings))
    if not uses_network and detected_hosts:
        fail("remote hosts were detected but networkAccess.usesNetwork is false: " + format_findings(host_findings))
    undeclared = detected_hosts - allowed_hosts
    if undeclared:
        fail("undeclared remote hosts were detected: " + ", ".join(sorted(undeclared)))

    print_network_report(api_findings, host_findings, allowed_hosts)
    return api_findings, host_findings


def detect_network_apis(binary: bytes) -> set[str]:
    findings = set()
    for label, indicators in NETWORK_API_INDICATORS.items():
        if any(indicator in binary or utf16_le(indicator) in binary for indicator in indicators):
            findings.add(label)
    return findings


def detect_network_hosts(binary: bytes) -> set[str]:
    strings = [match.group().decode("ascii", "ignore") for match in PRINTABLE_ASCII.finditer(binary)]
    strings.extend(
        match.group().decode("utf-16-le", "ignore")
        for match in PRINTABLE_UTF16_LE.finditer(binary)
    )
    hosts = set()
    for string in strings:
        for match in URL.finditer(string):
            host = urlsplit(match.group()).hostname
            if host:
                add_remote_host(hosts, host.lower())
        for match in BARE_DOMAIN.finditer(string):
            add_remote_host(hosts, match.group().lower())
        for match in IPV4.finditer(string):
            add_remote_host(hosts, match.group())
    return hosts


def add_remote_host(hosts: set[str], host: str) -> None:
    if host in LOCAL_HOSTS:
        return
    if valid_remote_host(host):
        hosts.add(host)


def utf16_le(value: bytes) -> bytes:
    return b"".join(bytes((byte, 0)) for byte in value)


def format_findings(findings: dict[str, set[str]]) -> str:
    return "; ".join(
        f"{path}: {', '.join(sorted(values))}" for path, values in sorted(findings.items())
    )


def print_network_report(
    api_findings: dict[str, set[str]],
    host_findings: dict[str, set[str]],
    allowed_hosts: set[str],
) -> None:
    if api_findings:
        print(f"  Network APIs: {format_findings(api_findings)}")
    if host_findings:
        print(f"  Remote hosts: {format_findings(host_findings)}")
    if not api_findings and not host_findings:
        print("  Network scan: no known APIs or remote hosts detected")
    if allowed_hosts:
        print(f"  Declared hosts: {', '.join(sorted(allowed_hosts))}")
    if os.environ.get("GITHUB_ACTIONS") == "true" and (api_findings or host_findings):
        print("::notice title=Mod network scan::" + format_findings({**api_findings, **host_findings}))


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
    uses_network, allowed_hosts = parse_network_access(data, definition_path)
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
    source = parse_source_provenance(data, release, definition_path)

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
        scan_network_access(archive, uses_network, allowed_hosts)
        if source is not None:
            verify_source_provenance(archive, source)
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

#!/usr/bin/env python3
"""
Manage python-build-standalone tarballs for the Kolibri .deb package.

Subcommands:
    download [ARCH]     Download and verify tarballs for bundling.
    update VERSION      Find latest release for a Python version, download,
                        compute checksums, and update python_versions.env.
"""

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "python_versions.env"

GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/astral-sh/python-build-standalone/releases"
)
DOWNLOAD_URL_BASE = (
    "https://github.com/astral-sh/python-build-standalone/releases/download"
)

SUPPORTED_ARCHES = ("x86_64", "aarch64")


# ---------------------------------------------------------------------------
# Config (.env) read/write
# ---------------------------------------------------------------------------


def read_config(path=CONFIG_PATH):
    """Parse a KEY="value" env file into a dict."""
    config = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip().strip('"')
    return config


def write_config(path, values):
    """Write a python_versions.env file with the given values."""
    with open(path, "w") as f:
        f.write(
            """\
# Python version configuration for kolibri-installer-debian
# This file is sourced by build and install scripts.
#
# To update, run: make update-python VERSION=3.xx
# Or manually update all fields below.

PYTHON_VERSION="{PYTHON_VERSION}"
PYTHON_BUILD_STANDALONE_TAG="{PYTHON_BUILD_STANDALONE_TAG}"
PYTHON_BUILD_STANDALONE_VERSION="{PYTHON_BUILD_STANDALONE_VERSION}"
PYTHON_SHA256_X86_64="{PYTHON_SHA256_X86_64}"
PYTHON_SHA256_AARCH64="{PYTHON_SHA256_AARCH64}"
PYTHON_URL_BASE="{PYTHON_URL_BASE}"

# Minimum Python version required by Kolibri.
# If the system Python is >= this version, the bundled Python is not installed.
PYTHON_MIN_MAJOR={PYTHON_MIN_MAJOR}
PYTHON_MIN_MINOR={PYTHON_MIN_MINOR}
""".format(**values)
        )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def tarball_filename(version, arch):
    return f"cpython-{version}-{arch}-unknown-linux-gnu-install_only_stripped.tar.gz"


def tarball_url(base, tag, version, arch):
    filename = tarball_filename(version, arch)
    # The + in the version must be URL-encoded as %2B
    url_filename = filename.replace("+", "%2B")
    return f"{base}/{tag}/{url_filename}"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(path, expected):
    actual = sha256_file(path)
    if actual != expected:
        raise SystemExit(
            f"ERROR: SHA256 mismatch for {path}\n"
            f"  Expected: {expected}\n"
            f"  Got:      {actual}"
        )
    return actual


def download_file(url, dest):
    """Download url to dest with progress indication."""
    print(f"Downloading {dest.name}...")

    def report(block, block_size, total):
        done = block * block_size
        if total > 0:
            pct = min(100, done * 100 // total)
            print(f"\r  {pct}%  ({done // (1 << 20)} / {total // (1 << 20)} MB)", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=report)
    print()


# ---------------------------------------------------------------------------
# download subcommand
# ---------------------------------------------------------------------------


def cmd_download(args):
    config = read_config()
    version = config["PYTHON_BUILD_STANDALONE_VERSION"]
    base = config["PYTHON_URL_BASE"]
    tag = config["PYTHON_BUILD_STANDALONE_TAG"]

    arches = [args.arch] if args.arch else list(SUPPORTED_ARCHES)
    dest_dir = REPO_ROOT / "build_src"
    dest_dir.mkdir(exist_ok=True)

    for arch in arches:
        sha_key = f"PYTHON_SHA256_{arch.upper()}"
        expected_sha = config.get(sha_key)
        if not expected_sha:
            raise SystemExit(f"ERROR: {sha_key} is not set in python_versions.env")

        filename = tarball_filename(version, arch)
        dest = dest_dir / filename
        url = tarball_url(base, tag, version, arch)

        if dest.exists():
            print(f"Already downloaded: {dest}")
            actual = sha256_file(dest)
            if actual == expected_sha:
                print("Checksum verified.")
                continue
            else:
                print("Checksum mismatch, re-downloading...")
                dest.unlink()

        download_file(url, dest)

        try:
            verify_sha256(dest, expected_sha)
        except SystemExit:
            dest.unlink(missing_ok=True)
            raise
        print("Checksum verified.")

    print("Done.")


# ---------------------------------------------------------------------------
# update subcommand
# ---------------------------------------------------------------------------


def find_release(releases, target):
    """Find the latest release with matching tarballs for target Python version."""
    suffix = "-unknown-linux-gnu-install_only_stripped.tar.gz"
    for r in releases:
        assets = {a["name"]: a["browser_download_url"] for a in r.get("assets", [])}
        urls = {}
        for arch in SUPPORTED_ARCHES:
            for name, url in assets.items():
                if name.startswith(f"cpython-{target}") and name.endswith(f"-{arch}{suffix}"):
                    urls[arch] = url
                    break
        if len(urls) != len(SUPPORTED_ARCHES):
            continue
        # Extract version from the matched filename, e.g. "3.10.20+20260325"
        matched_name = next(n for n in assets if n.endswith(f"-{SUPPORTED_ARCHES[0]}{suffix}") and n.startswith(f"cpython-{target}"))
        full_version = matched_name.split("-")[1]
        python_version = full_version.split("+")[0]
        return r["tag_name"], python_version, full_version, urls

    return None


def cmd_update(args):
    target = args.version

    # Normalize: "11" -> "3.11"
    if re.match(r"^\d+$", target):
        target = f"3.{target}"

    if not re.match(r"^3\.\d+$", target):
        raise SystemExit(f"ERROR: Version must be in format 3.XX (e.g. 3.11), got: {target}")

    print(f"Searching for latest python-build-standalone release with cpython-{target}...")

    url = f"{GITHUB_RELEASES_URL}?per_page=20"
    with urllib.request.urlopen(url) as resp:
        releases = json.load(resp)

    result = find_release(releases, target)
    if result is None:
        raise SystemExit(
            f"ERROR: Could not find a python-build-standalone release with cpython-{target}"
        )

    tag, python_version, full_version, urls = result
    print(f"Found: Python {python_version} ({full_version}) in release {tag}")
    for arch, u in urls.items():
        print(f"  {arch}: {u}")

    # Download into build_src/ so `make get-python` doesn't re-fetch the same
    # tarballs — once update completes, the checksums in python_versions.env
    # will match the files already on disk.
    dest_dir = REPO_ROOT / "build_src"
    dest_dir.mkdir(exist_ok=True)

    checksums = {}
    for arch in SUPPORTED_ARCHES:
        dest = dest_dir / tarball_filename(full_version, arch)
        if dest.exists():
            print(f"Already downloaded: {dest}")
        else:
            download_file(urls[arch], dest)
        checksums[arch] = sha256_file(dest)
        print(f"SHA256 {arch}: {checksums[arch]}")

    minor = target.split(".")[1]

    write_config(
        CONFIG_PATH,
        {
            "PYTHON_VERSION": python_version,
            "PYTHON_BUILD_STANDALONE_TAG": tag,
            "PYTHON_BUILD_STANDALONE_VERSION": full_version,
            "PYTHON_SHA256_X86_64": checksums["x86_64"],
            "PYTHON_SHA256_AARCH64": checksums["aarch64"],
            "PYTHON_URL_BASE": DOWNLOAD_URL_BASE,
            "PYTHON_MIN_MAJOR": "3",
            "PYTHON_MIN_MINOR": minor,
        },
    )

    print(f"\nUpdated {CONFIG_PATH}")
    print("Review the changes, then commit.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Manage python-build-standalone tarballs for the Kolibri .deb."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="Download and verify tarballs for bundling.")
    dl.add_argument(
        "arch",
        nargs="?",
        choices=SUPPORTED_ARCHES,
        help="Download only this architecture (default: both).",
    )

    up = sub.add_parser(
        "update",
        help="Find latest release, download, compute checksums, update config.",
    )
    up.add_argument("version", help="Target Python version, e.g. 3.11 or just 11.")

    args = parser.parse_args()
    if args.command == "download":
        cmd_download(args)
    elif args.command == "update":
        cmd_update(args)


if __name__ == "__main__":
    main()

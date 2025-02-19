import logging
import re
import requests
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("generate_changelog")

ROOT_DIR = Path(__file__).parent.resolve()
KOLIBRI_CHANGELOG_PATH = ROOT_DIR / "kolibri/CHANGELOG.md"
DEBIAN_CHANGELOG_PATH = ROOT_DIR / "debian/changelog"
GITHUB_API_RELEASES_URL = (
    "https://api.github.com/repos/learningequality/kolibri/releases"
)
MIN_VERSION = "0.17.3"

def fetch_github_releases():
    log.info("Fetching GitHub releases...")
    response = requests.get(GITHUB_API_RELEASES_URL)
    response.raise_for_status()
    log.info("Successfully fetched GitHub releases.")
    return response.json()

def download_kolibri_changelog(save_path):
    kolibri_changelog_url = "https://raw.githubusercontent.com/learningequality/kolibri/release-v0.17.x/CHANGELOG.md"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    log.info("Downloading Kolibri CHANGELOG.md...")
    response = requests.get(kolibri_changelog_url)
    if response.status_code == 200:
        with open(save_path, "w", encoding="utf-8") as file:
            file.write(response.text)
        log.info(f"Downloaded Kolibri CHANGELOG.md to {save_path}")
    else:
        log.error(f"Failed to download Kolibri CHANGELOG.md from {kolibri_changelog_url}")
        raise FileNotFoundError(
            f"Unable to download Kolibri CHANGELOG.md from {kolibri_changelog_url}"
        )

def parse_kolibri_changelog(path):
    if not path.exists():
        log.warning("Kolibri CHANGELOG.md not found. Downloading...")
        download_kolibri_changelog(path)
    
    log.info("Parsing Kolibri CHANGELOG.md...")
    with path.open("r") as f:
        content = f.read()

    pattern = re.compile(r"## (\d+\.\d+\.\d+)(.*?)## ", re.DOTALL)
    matches = pattern.findall(content)
    changes = {}

    for version, details in matches:
        if version >= MIN_VERSION:
            changes[version] = details.strip()
    log.info(f"Parsed {len(changes)} versions from Kolibri changelog.")
    return changes

def parse_debian_changelog(path):
    if not path.exists():
        log.error(f"{path} not found. Ensure the Debian changelog exists.")
        raise FileNotFoundError(f"{path} not found. Ensure the Debian changelog exists.")
    log.info("Parsing Debian changelog...")
    with path.open("r") as f:
        return f.read()

def generate_new_entries(kolibri_changes, github_releases):
    log.info("Generating new changelog entries...")
    new_entries = []
    github_timestamps = {r["tag_name"]: r["published_at"] for r in github_releases}

    for version, details in kolibri_changes.items():
        timestamp = github_timestamps.get(version)
        if not timestamp:
            log.warning(f"No timestamp found for version {version}. Skipping...")
            continue

        date_str = datetime.fromisoformat(timestamp[:-1]).strftime(
            "%a, %d %b %Y %H:%M:%S +0000"
        )
        entry = (
            f"kolibri-source ({version}-0ubuntu1) jammy; urgency=medium\n\n"
            f"  * New upstream release\n"
            f"  * Highlights:\n{details}\n\n"
            f" -- Maintainer <email@example.com>  {date_str}\n"
        )
        new_entries.append(entry)
    log.info(f"Generated {len(new_entries)} new entries.")
    return new_entries

def save_changelog(entries, path):
    if entries:
        with path.open("a") as f:
            f.write("\n".join(entries) + "\n")
        log.info(f"Added {len(entries)} new entries to the changelog.")
    else:
        log.info("No new entries to add to the changelog.")

def main():
    try:
        github_releases = fetch_github_releases()
        kolibri_changes = parse_kolibri_changelog(KOLIBRI_CHANGELOG_PATH)
        new_entries = generate_new_entries(kolibri_changes, github_releases)
        save_changelog(new_entries, DEBIAN_CHANGELOG_PATH)
        log.info("Debian changelog updated successfully!")
    except Exception as e:
        log.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

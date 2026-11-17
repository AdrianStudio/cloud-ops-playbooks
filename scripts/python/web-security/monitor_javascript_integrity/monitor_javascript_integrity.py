#!/usr/bin/env python3
"""Monitors the integrity of specified JavaScript files by comparing their current hash against a known good hash.

Requires the following environment variables:
- SCRIPT_URLS: Comma-separated list of URLs to monitor.
- HASH_FILE_PATH: Path to a JSON file storing known good hashes.

Usage:
    python monitor_javascript_integrity.py
    python monitor_javascript_integrity.py --apply
"""

import argparse
import hashlib
import json
import os
import sys
import requests


def calculate_sha256(content: bytes) -> str:
    """Calculates the SHA256 hash of the given content."""
    return hashlib.sha256(content).hexdigest()


def fetch_script_content(url: str) -> bytes:
    """Fetches the content of a script from a given URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as request_error:
        print(f"Error fetching {url}: {request_error}", file=sys.stderr)
        sys.exit(1)


def load_known_hashes(file_path: str) -> dict[str, str]:
    """Loads known good hashes from a JSON file."""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as hash_file:
            return json.load(hash_file)
    except json.JSONDecodeError as json_error:
        print(f"Error decoding JSON from {file_path}: {json_error}", file=sys.stderr)
        sys.exit(1)
    except IOError as io_error:
        print(f"Error reading {file_path}: {io_error}", file=sys.stderr)
        sys.exit(1)


def save_known_hashes(file_path: str, hashes: dict[str, str]):
    """Saves current hashes to a JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as hash_file:
            json.dump(hashes, hash_file, indent=4)
    except IOError as io_error:
        print(f"Error writing to {file_path}: {io_error}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Monitor JavaScript file integrity.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Update the stored hashes with the current calculated hashes."
    )
    args = parser.parse_args()

    script_urls_str = os.environ["SCRIPT_URLS"]
    hash_file_path = os.environ["HASH_FILE_PATH"]

    script_urls = [url.strip() for url in script_urls_str.split(',') if url.strip()]
    if not script_urls:
        print("No script URLs provided in SCRIPT_URLS environment variable.", file=sys.stderr)
        sys.exit(1)

    known_hashes = load_known_hashes(hash_file_path)
    current_hashes = {}
    integrity_issues_found = False

    for url in script_urls:
        print(f"Checking {url}...")
        script_content = fetch_script_content(url)
        current_hash = calculate_sha256(script_content)
        current_hashes[url] = current_hash

        if url not in known_hashes:
            print(f"  WARNING: No known hash for {url}. Current hash: {current_hash}")
            integrity_issues_found = True
        elif known_hashes[url] != current_hash:
            print(f"  ALERT: Hash mismatch for {url}!\n    Known: {known_hashes[url]}\n    Current: {current_hash}", file=sys.stderr)
            integrity_issues_found = True
        else:
            print(f"  Integrity OK for {url}.")

    if args.apply:
        if integrity_issues_found:
            print("WARNING: Integrity issues found. Updating hashes anyway due to --apply flag.")
        save_known_hashes(hash_file_path, current_hashes)
        print(f"Hashes updated in {hash_file_path}.")
    elif integrity_issues_found:
        print("\nIntegrity issues detected. Run with --apply to update known hashes if changes are legitimate.", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nAll monitored scripts are intact.")


if __name__ == "__main__":
    main()

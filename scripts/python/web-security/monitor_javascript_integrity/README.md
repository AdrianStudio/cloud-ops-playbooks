# monitor-javascript-integrity
Monitors the integrity of specified JavaScript files by comparing their current hash against a known good hash.

## Problem
Third-party JavaScript tags, often loaded from CDNs, are susceptible to supply chain attacks where the CDN can be compromised and malware injected. Manual monitoring is reactive and insufficient, leaving websites and users vulnerable to data theft and exploits.

## Prerequisites
* `SCRIPT_URLS`: Comma-separated list of full URLs to the JavaScript files to monitor (e.g., `https://example.com/script.js,https://cdn.thirdparty.com/lib.js`).
* `HASH_FILE_PATH`: Absolute or relative path to a JSON file where known good hashes are stored (e.g., `./known_hashes.json`).
* Python 3.12
* `requests` module (`pip install requests`)

## Usage
```bash
# Report only (default behavior)
export SCRIPT_URLS="https://example.com/script.js,https://cdn.thirdparty.com/lib.js"
export HASH_FILE_PATH="./known_hashes.json"
python monitor_javascript_integrity.py

# Update known hashes (after verifying legitimate changes)
export SCRIPT_URLS="https://example.com/script.js,https://cdn.thirdparty.com/lib.js"
export HASH_FILE_PATH="./known_hashes.json"
python monitor_javascript_integrity.py --apply
```

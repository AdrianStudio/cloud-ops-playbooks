# script-integrity-monitor
Monitors the integrity of specified third-party scripts by comparing their current hash with a known good hash.

## Problem
Malware injection via third-party CDNs, like the recent Optimizely incident, compromises user data on numerous websites. Existing reactive security measures often detect issues after damage occurs, requiring manual configuration and log reviews.

## Prerequisites
* `OPTIMIZELY_SCRIPT_URL`: The full URL of the Optimizely script to monitor (e.g., `https://cdn.optimizely.com/js/1234567890.js`).
* `OPTIMIZELY_EXPECTED_SHA256`: The known good SHA256 hash of the Optimizely script.
* `ALERT_WEBHOOK_URL`: (Optional, required with `--apply`) The URL of the webhook to send alerts to (e.g., a Slack or Teams webhook).
* Python 3.12
* `requests` module (`pip install requests`)

## Usage
```bash
# Report-only run: checks script integrity and prints status to console
python script_integrity_monitor.py

# Run with alerts: checks script integrity and sends alerts to webhook if compromised
python script_integrity_monitor.py --apply
```

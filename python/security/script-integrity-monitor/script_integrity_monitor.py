import argparse
import hashlib
import os
import requests
import sys

def _calculate_sha256(content: bytes) -> str:
    """Calculates the SHA256 hash of the given content."""
    return hashlib.sha256(content).hexdigest()

def _send_alert(webhook_url: str, message: str) -> None:
    """Sends an alert message to a specified webhook URL."""
    headers = {"Content-Type": "application/json"}
    payload = {"text": message}
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"Alert sent successfully to webhook: {webhook_url}")
    except requests.exceptions.RequestException as request_error:
        print(f"Error sending alert to webhook {webhook_url}: {request_error}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Monitor the integrity of third-party scripts by comparing their SHA256 hash."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Send alerts to a webhook if script integrity is compromised."
    )
    args = parser.parse_args()

    # Script configurations: URL and expected SHA256 hash
    # These should be updated with actual values for the scripts being monitored.
    # Example: Optimizely script URL and its known good hash.
    scripts_to_monitor = {
        "Optimizely_Main_Script": {
            "url": os.environ["OPTIMIZELY_SCRIPT_URL"],
            "expected_sha256": os.environ["OPTIMIZELY_EXPECTED_SHA256"]
        }
        # Add more scripts here as needed
        # "Another_Script": {
        #     "url": "https://example.com/another-script.js",
        #     "expected_sha256": "<known_good_sha256_for_another_script>"
        # }
    }

    if args.apply:
        webhook_url = os.environ["ALERT_WEBHOOK_URL"]

    for script_name, config in scripts_to_monitor.items():
        script_url = config["url"]
        expected_sha256 = config["expected_sha256"]

        print(f"Monitoring script: {script_name} from {script_url}")

        try:
            response = requests.get(script_url, timeout=15)
            response.raise_for_status()
            current_sha256 = _calculate_sha256(response.content)

            if current_sha256 != expected_sha256:
                alert_message = (
                    f"CRITICAL: Script integrity compromised for {script_name} ({script_url}). "
                    f"Expected SHA256: {expected_sha256}, Current SHA256: {current_sha256}."
                )
                print(alert_message, file=sys.stderr)
                if args.apply:
                    _send_alert(webhook_url, alert_message)
            else:
                print(f"Script {script_name} integrity verified. SHA256: {current_sha256}")

        except requests.exceptions.RequestException as request_error:
            error_message = f"Error fetching script {script_name} from {script_url}: {request_error}"
            print(error_message, file=sys.stderr)
            if args.apply:
                _send_alert(webhook_url, error_message)


if __name__ == "__main__":
    main()

import os
import requests
import argparse
import logging
import sys
import time

# --- Configuration Constants ---
# NOTE: These API endpoints should be verified against the N-Able API documentation.
NABLE_DEVICES_API_PATH = "/api/v1/devices"
NABLE_ISOLATE_DEVICE_API_PATH_TEMPLATE = "/api/v1/devices/{device_id}/isolate"
NABLE_VULNERABILITIES_API_PATH = "/api/v1/vulnerabilities"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def get_env_variable(name):
    """Gets an environment variable or raises an error if it's not set."""
    value = os.getenv(name)
    if not value:
        logging.error(f"Environment variable '{name}' not set. Please set it before running the script.")
        sys.exit(1)
    return value

def make_api_request(method, url, headers, params=None, json_data=None, timeout=30):
    """Helper function to make authenticated API requests."""
    try:
        response = requests.request(method, url, headers=headers, params=params, json=json_data, timeout=timeout)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error during {method} {url}: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error during {method} {url}: {e}")
        return None
    except requests.exceptions.Timeout as e:
        logging.error(f"Timeout error during {method} {url}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"An unexpected request error occurred during {method} {url}: {e}")
        return None

def get_all_paginated_results(api_url, headers, path, params=None):
    """Fetches all results from a paginated API endpoint."""
    all_results = []
    page = 1
    per_page = 100  # N-Able API default or common page size
    while True:
        current_params = {'page': page, 'per_page': per_page}
        if params:
            current_params.update(params)

        url = f"{api_url}{path}"
        logging.debug(f"Fetching page {page} from {url} with params: {current_params}")
        response_data = make_api_request('GET', url, headers, params=current_params)

        if response_data is None:
            logging.error(f"Failed to fetch data from {url} at page {page}.")
            break

        # Assuming N-Able API returns results in a 'data' or similar key and pagination info
        # This part might need adjustment based on actual N-Able API response structure
        items = response_data.get('data', []) # Common pattern, adjust if N-Able uses different key
        all_results.extend(items)

        total_pages = response_data.get('meta', {}).get('total_pages') # Common pattern
        if not items or (total_pages and page >= total_pages):
            break # No more items or reached last page

        page += 1
        time.sleep(0.1) # Small delay to prevent hammering the API

    return all_results

def main():
    """Main function to identify and isolate vulnerable N-Able endpoints."""
    parser = argparse.ArgumentParser(description="Identify and isolate vulnerable N-Able endpoints.")
    parser.add_argument('--apply', action='store_true', help='Apply the isolation action. Default is dry-run.')
    args = parser.parse_args()

    nable_api_url = get_env_variable("NABLE_API_URL")
    nable_api_token = get_env_variable("NABLE_API_TOKEN")

    headers = {
        "Authorization": f"Bearer {nable_api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    logging.info("Fetching all devices...")
    devices = get_all_paginated_results(nable_api_url, headers, NABLE_DEVICES_API_PATH)
    if not devices:
        logging.warning("No devices found or failed to retrieve devices. Exiting.")
        sys.exit(0)
    logging.info(f"Found {len(devices)} devices.")

    logging.info("Fetching all vulnerabilities...")
    # N-Able API might have a way to filter vulnerabilities by 'active' or 'unpatched'
    # For simplicity, we fetch all and filter locally, but API filtering is preferred if available.
    vulnerabilities = get_all_paginated_results(nable_api_url, headers, NABLE_VULNERABILITIES_API_PATH)
    if not vulnerabilities:
        logging.warning("No vulnerabilities found or failed to retrieve vulnerabilities. Exiting.")
        sys.exit(0)
    logging.info(f"Found {len(vulnerabilities)} vulnerabilities.")

    # Create a set of device IDs that have active vulnerabilities
    vulnerable_device_ids = set()
    for vul in vulnerabilities:
        # Assuming 'device_id' is a key in the vulnerability object and 'status' indicates active/unpatched
        # This part is highly dependent on the actual N-Able API response structure for vulnerabilities.
        device_id = vul.get('device_id')
        status = vul.get('status') # e.g., 'active', 'unpatched', 'detected'
        if device_id and status in ['active', 'unpatched', 'detected']:
            vulnerable_device_ids.add(device_id)

    if not vulnerable_device_ids:
        logging.info("No devices with active vulnerabilities identified. Exiting.")
        sys.exit(0)

    logging.info(f"Identified {len(vulnerable_device_ids)} unique devices with active vulnerabilities.")

    isolated_count = 0
    for device in devices:
        device_id = device.get('id')
        device_name = device.get('name', 'Unknown Device')

        if device_id in vulnerable_device_ids:
            logging.info(f"Device '{device_name}' (ID: {device_id}) is vulnerable.")
            isolate_url = f"{nable_api_url}{NABLE_ISOLATE_DEVICE_API_PATH_TEMPLATE.format(device_id=device_id)}"

            if args.apply:
                logging.info(f"Applying isolation to device '{device_name}' (ID: {device_id})...")
                # N-Able API might require a specific payload for isolation, e.g., {'action': 'isolate'}
                # Assuming a POST request to the isolate endpoint is sufficient without a body for now.
                # Adjust 'json_data' if a specific payload is needed.
                response = make_api_request('POST', isolate_url, headers, json_data={})
                if response:
                    logging.info(f"Successfully initiated isolation for device '{device_name}' (ID: {device_id}).")
                    isolated_count += 1
                else:
                    logging.error(f"Failed to initiate isolation for device '{device_name}' (ID: {device_id}).")
            else:
                logging.info(f"Dry run: Would isolate device '{device_name}' (ID: {device_id}).")

    if args.apply:
        logging.info(f"Script finished. Isolated {isolated_count} vulnerable devices.")
    else:
        logging.info(f"Script finished in dry-run mode. {isolated_count} devices would have been isolated if --apply was used.")


if __name__ == "__main__":
    main()

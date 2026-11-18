# endpoint-isolator
Finds N-able managed devices with active vulnerabilities and, on request, sends each one an isolation command.

## Problem
MSP teams on N-able face a constant flow of CVEs that need urgent patching. Until a patch lands, a vulnerable endpoint stays reachable on the client network, and isolating each device by hand from the console is slow.

## Prerequisites
* `NABLE_API_URL`: base URL of the N-able API for your instance.
* `NABLE_API_TOKEN`: API token with permission to read devices and vulnerabilities and to run the isolation action.
* Python 3.12
* `requests` module (`pip install requests`)

## Usage
```bash
# Report-only run: lists the vulnerable devices that would be isolated
python endpoint_isolator.py

# Isolates every device with an active, unpatched or detected vulnerability
python endpoint_isolator.py --apply
```

## Unverified
The API paths `/api/v1/devices`, `/api/v1/vulnerabilities` and `/api/v1/devices/{device_id}/isolate`, the `data` and `meta.total_pages` pagination fields and the vulnerability `status` values are assumptions. Check them against the N-able API documentation for your instance before running with `--apply`.

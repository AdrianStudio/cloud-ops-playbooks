# report-ncentral-cves
Reports N-Able N-Central CVEs by fetching data from a GitHub repository.

## Problem
MSPs using N-Able N-Central need to quickly identify and respond to new CVE disclosures. Manually tracking these vulnerabilities across various sources is inefficient and increases the risk of delayed patching, leaving systems exposed.

## Prerequisites
* `GITHUB_API_TOKEN`: A GitHub Personal Access Token with `public_repo` scope.
* Python 3.12
* `requests` module (`pip install requests`)

## Usage
```bash
python report_ncentral_cves.py
```

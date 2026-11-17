import os
import requests
import argparse
import json

# Module docstring: Purpose, required environment variables, and usage.
"""Retrieves N-Able N-Central CVE information from a GitHub repository.

This script fetches CVE details from a public GitHub repository, parses the content,
and outputs a structured report. It helps MSPs stay informed about new vulnerabilities.

Required environment variables:
    - GITHUB_API_TOKEN: A GitHub Personal Access Token with 'public_repo' scope.

Usage:
    python report_ncentral_cves.py
"""

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_REPO_OWNER = "MSPNightmare"
GITHUB_REPO_NAME = "CVEs"
GITHUB_PATH = "main/0-Days/N-Central N-Able"

def fetch_github_directory_contents(owner: str, repo: str, path: str, token: str) -> list[dict]:
    """Fetches the contents of a specific directory in a GitHub repository."""
    url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def fetch_file_content(url: str, token: str) -> str:
    """Fetches the content of a file from a given URL."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.raw"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text

def parse_cve_content(content: str) -> dict:
    """Parses the content of a CVE file (assuming JSON format)."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # If a file is not valid JSON, return its raw content under a 'raw_content' key
        return {"error": "Invalid JSON format", "raw_content": content}

def main():
    parser = argparse.ArgumentParser(description="Report N-Able N-Central CVEs from GitHub.")
    args = parser.parse_args()

    github_token = os.environ["GITHUB_API_TOKEN"]

    print("Fetching N-Able N-Central CVEs...")
    try:
        directory_contents = fetch_github_directory_contents(
            GITHUB_REPO_OWNER, GITHUB_REPO_NAME, GITHUB_PATH, github_token
        )

        cve_reports = []
        for item in directory_contents:
            if item["type"] == "file" and item["name"].endswith(".json"):
                print(f"  Processing file: {item['name']}")
                file_content = fetch_file_content(item["download_url"], github_token)
                parsed_cve = parse_cve_content(file_content)
                cve_reports.append({"filename": item["name"], "data": parsed_cve})

        if cve_reports:
            print("\n--- N-Able N-Central CVE Report ---")
            for report in cve_reports:
                print(f"\nFile: {report['filename']}")
                if "error" in report["data"]:
                    print(f"  Error: {report['data']['error']}")
                    print(f"  Content snippet: {report['data']['raw_content'][:200]}...")
                else:
                    # Assuming CVE data has a 'cve_id' and 'description' for display
                    cve_id = report["data"]["cve_id"]
                    description = report["data"]["description"]
                    print(f"  CVE ID: {cve_id}")
                    print(f"  Description: {description}")
                    # Print full JSON for detailed inspection
                    print("  Full Details:")
                    print(json.dumps(report["data"], indent=2))
        else:
            print("No CVE files found in the specified GitHub path.")

    except requests.exceptions.HTTPError as http_error:
        print(f"HTTP error occurred: {http_error}")
        print(f"Response content: {http_error.response.text}")
    except requests.exceptions.ConnectionError as connection_error:
        print(f"Connection error occurred: {connection_error}")
    except requests.exceptions.Timeout as timeout_error:
        print(f"Request timed out: {timeout_error}")
    except requests.exceptions.RequestException as request_error:
        print(f"An unexpected request error occurred: {request_error}")


if __name__ == "__main__":
    main()

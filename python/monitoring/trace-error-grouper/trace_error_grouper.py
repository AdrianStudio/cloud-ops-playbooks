"""Group Loki error logs by trace and summarise the failing Tempo traces.

Required environment variables: LOKI_URL, TEMPO_URL, LOKI_QUERY.
Optional: LOKI_TENANT_ID, TEMPO_TENANT_ID, GITHUB_API_URL.
Required with --apply only: GITHUB_TOKEN, GITHUB_REPOSITORY (owner/name).

Usage:
    python trace_error_grouper.py [--since-minutes 60] [--limit 1000]
    python trace_error_grouper.py --apply
"""
import argparse
import hashlib
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

REQUEST_TIMEOUT_SECONDS = 30
LOKI_QUERY_PATH = "/loki/api/v1/query_range"
TEMPO_TRACE_PATH = "/api/v2/traces/"
TRACE_ID_LABEL = "trace_id"
ERROR_STATUS_CODES = ("STATUS_CODE_ERROR", 2)
MAX_EXCEPTION_CHARS = 300
GITHUB_DEFAULT_API_URL = "https://api.github.com"
ISSUE_LABEL = "trace-error-group"
FINGERPRINT_PATTERN = re.compile(r"\[trace-error ([0-9a-f]{12})\]")
# Allowlist keeps secrets and personal data in span attributes out of reports and issues.
KEY_ATTRIBUTES = (
    "http.request.method",
    "http.method",
    "http.route",
    "http.response.status_code",
    "http.status_code",
    "rpc.system",
    "rpc.method",
    "db.system",
    "db.operation.name",
    "messaging.system",
    "peer.service",
)


def tenant_headers(tenant_variable: str) -> dict:
    headers = {}
    if tenant_variable in os.environ:
        headers["X-Scope-OrgID"] = os.environ[tenant_variable]
    return headers


def fetch_error_logs(query: str, since_minutes: int, limit: int) -> tuple[dict, int]:
    now_ns = time.time_ns()
    response = requests.get(
        os.environ["LOKI_URL"].rstrip("/") + LOKI_QUERY_PATH,
        params={
            "query": query,
            "start": now_ns - since_minutes * 60 * 10**9,
            "end": now_ns,
            "limit": limit,
            "direction": "backward",
        },
        headers=tenant_headers("LOKI_TENANT_ID"),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    log_timestamps_by_trace = defaultdict(list)
    untraced_log_count = 0
    for log_stream in response.json()["data"]["result"]:
        labels = log_stream["stream"]
        for entry in log_stream["values"]:
            if TRACE_ID_LABEL in labels:
                log_timestamps_by_trace[labels[TRACE_ID_LABEL]].append(int(entry[0]))
            else:
                untraced_log_count += 1
    return log_timestamps_by_trace, untraced_log_count


def fetch_trace(trace_id: str) -> list | None:
    response = requests.get(
        os.environ["TEMPO_URL"].rstrip("/") + TEMPO_TRACE_PATH + trace_id,
        headers={**tenant_headers("TEMPO_TENANT_ID"), "Accept": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    # Traces that were not sampled or are past retention return 404 and are reported separately.
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()["trace"]["resourceSpans"]


def attribute_map(attributes: list) -> dict:
    return {
        attribute["key"]: next(iter(attribute["value"].values()))
        for attribute in attributes
    }


def summarize_trace(trace_id: str, resource_spans: list) -> dict:
    trace_spans = []
    for resource_span in resource_spans:
        service_name = attribute_map(resource_span["resource"]["attributes"])["service.name"]
        for scope_span in resource_span["scopeSpans"]:
            for span in scope_span["spans"]:
                span_attributes = attribute_map(span["attributes"]) if "attributes" in span else {}
                exceptions = []
                if "events" in span:
                    for event in span["events"]:
                        if event["name"] != "exception":
                            continue
                        event_attributes = attribute_map(event["attributes"])
                        exceptions.append({
                            key: event_attributes[key]
                            for key in ("exception.type", "exception.message")
                            if key in event_attributes
                        })
                trace_spans.append({
                    "span_id": span["spanId"],
                    "parent_span_id": span["parentSpanId"] if "parentSpanId" in span else "",
                    "service": service_name,
                    "name": span["name"],
                    "start_ns": int(span["startTimeUnixNano"]),
                    "end_ns": int(span["endTimeUnixNano"]),
                    "failed": "status" in span and "code" in span["status"]
                    and span["status"]["code"] in ERROR_STATUS_CODES,
                    "exceptions": exceptions,
                    "key_attributes": {
                        key: span_attributes[key] for key in KEY_ATTRIBUTES if key in span_attributes
                    },
                })
    trace_spans.sort(key=lambda span: span["start_ns"])

    failed_spans = [span for span in trace_spans if span["failed"]]
    failed_parent_ids = {span["parent_span_id"] for span in failed_spans}
    deepest_failed_spans = [span for span in failed_spans if span["span_id"] not in failed_parent_ids]
    # Without a failed span the error was only logged, so the earliest span is the best anchor.
    root_cause_span = deepest_failed_spans[0] if deepest_failed_spans else trace_spans[0]
    return {"trace_id": trace_id, "spans": trace_spans, "root_cause_span": root_cause_span}


def root_cause_exception_type(root_cause_span: dict) -> str:
    for exception in root_cause_span["exceptions"]:
        if "exception.type" in exception:
            return exception["exception.type"]
    return ""


def fingerprint_trace(trace_summary: dict) -> str:
    root_cause_span = trace_summary["root_cause_span"]
    fingerprint_source = "|".join([
        root_cause_span["service"],
        root_cause_span["name"],
        root_cause_exception_type(root_cause_span),
    ])
    return hashlib.sha256(fingerprint_source.encode()).hexdigest()[:12]


def format_trace_summary(trace_summary: dict) -> str:
    summary_lines = []
    for span in trace_summary["spans"]:
        status_marker = "FAILED" if span["failed"] else "ok"
        duration_ms = (span["end_ns"] - span["start_ns"]) / 10**6
        summary_lines.append(f"[{status_marker}] {span['service']} / {span['name']} ({duration_ms:.1f} ms)")
        for exception in span["exceptions"]:
            exception_text = ": ".join(str(value) for value in exception.values())
            summary_lines.append(f"    exception: {exception_text[:MAX_EXCEPTION_CHARS]}")
        if span["key_attributes"]:
            attribute_text = ", ".join(f"{key}={value}" for key, value in span["key_attributes"].items())
            summary_lines.append(f"    attributes: {attribute_text}")
    return "\n".join(summary_lines)


def group_traces(log_timestamps_by_trace: dict) -> tuple[dict, list]:
    error_groups = {}
    missing_trace_ids = []
    for trace_id, log_timestamps in log_timestamps_by_trace.items():
        resource_spans = fetch_trace(trace_id)
        if resource_spans is None:
            missing_trace_ids.append(trace_id)
            continue
        trace_summary = summarize_trace(trace_id, resource_spans)
        fingerprint = fingerprint_trace(trace_summary)
        if fingerprint not in error_groups:
            error_groups[fingerprint] = {
                "sample_summary": trace_summary,
                "trace_ids": [],
                "log_count": 0,
                "first_seen_ns": min(log_timestamps),
                "last_seen_ns": max(log_timestamps),
            }
        error_group = error_groups[fingerprint]
        error_group["trace_ids"].append(trace_id)
        error_group["log_count"] += len(log_timestamps)
        error_group["first_seen_ns"] = min(error_group["first_seen_ns"], min(log_timestamps))
        error_group["last_seen_ns"] = max(error_group["last_seen_ns"], max(log_timestamps))
    return error_groups, missing_trace_ids


def iso_timestamp(timestamp_ns: int) -> str:
    return datetime.fromtimestamp(timestamp_ns / 10**9, tz=timezone.utc).isoformat()


def format_occurrences(error_group: dict) -> str:
    return (
        f"Error logs: {error_group['log_count']}\n"
        f"Traces: {len(error_group['trace_ids'])}\n"
        f"First seen: {iso_timestamp(error_group['first_seen_ns'])}\n"
        f"Last seen: {iso_timestamp(error_group['last_seen_ns'])}"
    )


def find_open_issue_numbers(github_api_url: str, repository: str, github_headers: dict) -> dict:
    issues_url = f"{github_api_url}/repos/{repository}/issues"
    request_params = {"labels": ISSUE_LABEL, "state": "open", "per_page": 100}
    issue_numbers_by_fingerprint = {}
    while issues_url:
        response = requests.get(
            issues_url, params=request_params, headers=github_headers, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        for issue in response.json():
            fingerprint_match = FINGERPRINT_PATTERN.search(issue["title"])
            if fingerprint_match:
                issue_numbers_by_fingerprint[fingerprint_match.group(1)] = issue["number"]
        issues_url = response.links["next"]["url"] if "next" in response.links else None
        # The next link already carries the query string.
        request_params = None
    return issue_numbers_by_fingerprint


def publish_error_groups(error_groups: dict) -> None:
    github_api_url = GITHUB_DEFAULT_API_URL
    if "GITHUB_API_URL" in os.environ:
        github_api_url = os.environ["GITHUB_API_URL"].rstrip("/")
    repository = os.environ["GITHUB_REPOSITORY"]
    github_headers = {
        "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
        "Accept": "application/vnd.github+json",
    }
    open_issue_numbers = find_open_issue_numbers(github_api_url, repository, github_headers)

    for fingerprint, error_group in error_groups.items():
        occurrence_text = format_occurrences(error_group)
        if fingerprint in open_issue_numbers:
            issue_number = open_issue_numbers[fingerprint]
            response = requests.post(
                f"{github_api_url}/repos/{repository}/issues/{issue_number}/comments",
                json={"body": "Seen again.\n\n" + occurrence_text},
                headers=github_headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            print(f"{fingerprint}: commented on issue #{issue_number}")
            continue

        sample_summary = error_group["sample_summary"]
        root_cause_span = sample_summary["root_cause_span"]
        issue_title = (
            f"[trace-error {fingerprint}] {root_cause_span['service']} / {root_cause_span['name']}"
        )
        issue_body = (
            f"{occurrence_text}\n\nSample trace: {sample_summary['trace_id']}\n\n"
            f"```\n{format_trace_summary(sample_summary)}\n```"
        )
        response = requests.post(
            f"{github_api_url}/repos/{repository}/issues",
            json={"title": issue_title, "body": issue_body, "labels": [ISSUE_LABEL]},
            headers=github_headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        print(f"{fingerprint}: created issue #{response.json()['number']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Group Loki error logs by trace and summarise Tempo traces.")
    parser.add_argument("--since-minutes", type=int, default=60)
    parser.add_argument("--limit", type=int, default=1000, help="maximum Loki log lines to read")
    parser.add_argument("--apply", action="store_true", help="create or update GitHub issues")
    arguments = parser.parse_args()

    log_timestamps_by_trace, untraced_log_count = fetch_error_logs(
        os.environ["LOKI_QUERY"], arguments.since_minutes, arguments.limit
    )
    error_groups, missing_trace_ids = group_traces(log_timestamps_by_trace)

    print(
        f"Traces with errors: {len(log_timestamps_by_trace)}, groups: {len(error_groups)}, "
        f"logs without {TRACE_ID_LABEL}: {untraced_log_count}, traces not found in Tempo: {len(missing_trace_ids)}"
    )
    for fingerprint, error_group in error_groups.items():
        print(f"\nGroup {fingerprint}\n{format_occurrences(error_group)}")
        print(format_trace_summary(error_group["sample_summary"]))

    if arguments.apply:
        publish_error_groups(error_groups)
    else:
        print("\nReport only. Run with --apply to create or update GitHub issues.")


if __name__ == "__main__":
    main()

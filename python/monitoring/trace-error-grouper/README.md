# Trace Error Grouper

Reads error logs from Loki, fetches their traces from Tempo, groups them by root-cause fingerprint and prints a condensed trace summary per group, optionally opening GitHub issues.

## Problem
SREs and developers on OpenTelemetry stacks see one bug as thousands of log lines. Message-based grouping merges different bugs with similar text and splits one bug with variable text. Diagnosis then means reading large OTLP trace JSON manually.

## Prerequisites
- Python 3.12 and `requests`.
- `LOKI_URL`: base URL of Loki.
- `TEMPO_URL`: base URL of Tempo.
- `LOKI_QUERY`: LogQL query selecting error logs. It must expose `trace_id` as a stream label (for example through a parser stage).
- `LOKI_TENANT_ID` (optional): sent as `X-Scope-OrgID` to Loki.
- `TEMPO_TENANT_ID` (optional): sent as `X-Scope-OrgID` to Tempo.
- `GITHUB_TOKEN` (only with `--apply`): token with Issues read and write on the target repository.
- `GITHUB_REPOSITORY` (only with `--apply`): `owner/name` of the repository receiving issues.
- `GITHUB_API_URL` (optional): GitHub Enterprise API base URL, defaults to `https://api.github.com`.
- Only an allowlist of span attributes is reported. Exception messages are included, truncated to 300 characters, so review them before using `--apply` on a public repository.

## Usage
```
export LOKI_URL=<loki-base-url>
export TEMPO_URL=<tempo-base-url>
export LOKI_QUERY='<logql-error-query>'

python trace_error_grouper.py --since-minutes 60 --limit 1000

export GITHUB_TOKEN=<github-token>
export GITHUB_REPOSITORY=<owner>/<repository>
python trace_error_grouper.py --apply
```

- The default run only prints the report.
- `--apply` opens one issue per fingerprint, or comments on the open issue whose title carries the same `[trace-error <fingerprint>]` tag.
- Logs without `trace_id` are counted but not grouped.

## Unverified
- `TRACE_ID_LABEL` (`trace_id`): the label name under which the Loki stream exposes the trace ID depends on the ingestion setup.
- `TEMPO_TRACE_PATH` (`/api/v2/traces/`): the response shape `trace.resourceSpans` is assumed from the Tempo v2 trace by ID API and depends on the Tempo version.

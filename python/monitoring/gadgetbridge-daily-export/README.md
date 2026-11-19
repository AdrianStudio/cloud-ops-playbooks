# Gadgetbridge Daily Export

Reads the newest Gadgetbridge auto export zip and writes one JSON summary per day (heart rate and steps).

## Problem
People who keep wearable data off the manufacturer cloud receive Gadgetbridge export zips on a home server through Syncthing. Turning each zip into stable per-day files is usually a hand-written script that breaks silently when the export or schema changes. This script reads the database read-only and fails loudly when the zip, the member or a column is missing.

## Prerequisites
- Python 3.12, standard library only.
- `GADGETBRIDGE_EXPORT_DIR`: directory that holds the exported `.zip` files. Read access is enough.
- `DAILY_JSON_DIR`: directory for the `YYYY-MM-DD.json` files. Write access is needed only with `--apply`.
- No API tokens and no network access.
- Days are split using the local time zone of the machine running the script.

## Usage
```
export GADGETBRIDGE_EXPORT_DIR=<path-to-syncthing-folder>
export DAILY_JSON_DIR=<path-to-output-folder>

python gadgetbridge_daily_export.py
python gadgetbridge_daily_export.py --apply
```

## Unverified
- `DATABASE_ZIP_MEMBER` (`Gadgetbridge`): name of the database file inside the zip.
- `ACTIVITY_SAMPLE_TABLE` (`GARMIN_ACTIVITY_SAMPLE`): table with the per-sample data.
- `TIMESTAMP_COLUMN`, `HEART_RATE_COLUMN`, `STEPS_COLUMN`: column names. Timestamps are assumed to be Unix seconds.
- Check these constants against a real export from your Gadgetbridge version and edit them at the top of the script if they differ.

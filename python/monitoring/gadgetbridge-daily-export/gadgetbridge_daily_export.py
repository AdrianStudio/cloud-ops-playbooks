"""Convert the newest Gadgetbridge auto export into one JSON summary per day.

Environment variables:
    GADGETBRIDGE_EXPORT_DIR  directory where Syncthing delivers the export zip files
    DAILY_JSON_DIR           directory that receives one YYYY-MM-DD.json file per day

Usage:
    python gadgetbridge_daily_export.py          # report what would be written
    python gadgetbridge_daily_export.py --apply  # write the files
"""

import argparse
import json
import os
import sqlite3
import statistics
import tempfile
import zipfile
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from pathlib import Path

# Unverified against a specific Gadgetbridge release: check them with
# ".tables" and ".schema" on a real export before relying on the output.
DATABASE_ZIP_MEMBER = "Gadgetbridge"
ACTIVITY_SAMPLE_TABLE = "GARMIN_ACTIVITY_SAMPLE"
TIMESTAMP_COLUMN = "TIMESTAMP"
HEART_RATE_COLUMN = "HEART_RATE"
STEPS_COLUMN = "STEPS"

# Gadgetbridge stores 0 and 255 when the sensor produced no reading.
INVALID_HEART_RATES = {0, 255}


def find_newest_export(export_dir: Path) -> Path:
    export_archives = sorted(export_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime)
    if not export_archives:
        raise SystemExit(f"No .zip export found in {export_dir}")
    return export_archives[-1]


def read_activity_samples(export_archive: Path) -> list[tuple[int, int, int]]:
    query = (
        f"SELECT {TIMESTAMP_COLUMN}, {HEART_RATE_COLUMN}, {STEPS_COLUMN} "
        f"FROM {ACTIVITY_SAMPLE_TABLE} ORDER BY {TIMESTAMP_COLUMN}"
    )
    with tempfile.TemporaryDirectory() as extraction_dir:
        with zipfile.ZipFile(export_archive) as archive:
            database_path = archive.extract(DATABASE_ZIP_MEMBER, extraction_dir)
        with closing(sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)) as database:
            return database.execute(query).fetchall()


def summarize_by_day(activity_samples: list[tuple[int, int, int]]) -> dict[str, dict]:
    heart_rates_by_day = defaultdict(list)
    steps_by_day = defaultdict(int)
    for timestamp, heart_rate, steps in activity_samples:
        day = datetime.fromtimestamp(timestamp).date().isoformat()
        steps_by_day[day] += max(steps, 0)
        if heart_rate not in INVALID_HEART_RATES and heart_rate > 0:
            heart_rates_by_day[day].append(heart_rate)

    daily_summaries = {}
    for day in sorted(steps_by_day):
        day_heart_rates = heart_rates_by_day[day]
        heart_rate_summary = None
        if day_heart_rates:
            heart_rate_summary = {
                "samples": len(day_heart_rates),
                "min": min(day_heart_rates),
                "avg": round(statistics.fmean(day_heart_rates), 1),
                "max": max(day_heart_rates),
            }
        daily_summaries[day] = {
            "date": day,
            "heart_rate": heart_rate_summary,
            "steps": steps_by_day[day],
        }
    return daily_summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the daily JSON files")
    arguments = parser.parse_args()

    export_dir = Path(os.environ["GADGETBRIDGE_EXPORT_DIR"])
    daily_json_dir = Path(os.environ["DAILY_JSON_DIR"])

    export_archive = find_newest_export(export_dir)
    daily_summaries = summarize_by_day(read_activity_samples(export_archive))
    print(f"Source export: {export_archive.name}, {len(daily_summaries)} day(s)")

    if arguments.apply:
        daily_json_dir.mkdir(parents=True, exist_ok=True)

    for day, summary in daily_summaries.items():
        daily_file = daily_json_dir / f"{day}.json"
        serialized_summary = json.dumps(summary, indent=2, sort_keys=True) + "\n"
        if daily_file.exists() and daily_file.read_text(encoding="utf-8") == serialized_summary:
            print(f"{day}: unchanged")
            continue
        if arguments.apply:
            daily_file.write_text(serialized_summary, encoding="utf-8")
            print(f"{day}: written to {daily_file}")
        else:
            print(f"{day}: would write {daily_file}")


if __name__ == "__main__":
    main()

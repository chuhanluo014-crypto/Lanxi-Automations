from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATAPOOL_ROOT = PROJECT_ROOT / "Database" / "Datapool"
DEFAULT_POOL_PATH = DATAPOOL_ROOT / "data-pool" / "xhs_sample_pool_v1.csv"

STANDARD_COLUMNS = [
    "id",
    "note_id",
    "url",
    "title",
    "content",
    "author_id",
    "author_name",
    "likes",
    "comments",
    "collects",
    "tags",
    "images",
    "local_image_path",
    "scraped_at",
    "media_type",
    "push_time",
    "topic",
    "scene",
    "emotion",
    "hook",
    "reusable_structure",
    "risk_level",
    "keep_status",
    "notes",
    "review_status",
]

RAW_COLUMNS = [
    "note-slider-img src",
    "username",
    "name href",
    "title",
    "desc",
    "date",
    "total",
    "like-wrapper",
    "collect-wrapper",
    "chat-wrapper",
    "comment-inner-container",
    "cover href",
]

EMPTY_ANNOTATION_COLUMNS = [
    "topic",
    "scene",
    "emotion",
    "hook",
    "reusable_structure",
    "risk_level",
    "keep_status",
    "notes",
]


def stringify(value: Any) -> str:
    return "" if value is None else str(value).strip()


def clean_number(value: Any) -> str:
    text = stringify(value).replace(",", "")
    if not text:
        return "0"
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return "0"
    number = float(match.group(0))
    if "\u4e07" in text or "w" in text.lower():
        number *= 10000
    return str(int(round(number)))


def normalize_url(url: str) -> str:
    return stringify(url).split("?")[0]


def extract_note_id(url: str) -> str:
    match = re.search(r"/(?:search_result|explore)/([^?/#]+)", url or "")
    return match.group(1) if match else ""


def extract_author_id(author_url: str) -> str:
    match = re.search(r"/user/profile/([^?/#]+)", author_url or "")
    return match.group(1) if match else ""


def extract_tags(text: str) -> list[str]:
    tags: list[str] = []
    for match in re.finditer(r"#[^#\s,.;:!/?~|\\，。；：、！？～]+", text or ""):
        tag = match.group(0).strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def strip_tags(text: str) -> str:
    text = re.sub(r"#[^#\s,.;:!/?~|\\，。；：、！？～]+", "", text or "")
    text = re.sub(r"[\t\r\n]+", "  ", text)
    text = re.sub(r"\s{3,}", "  ", text)
    return text.strip()


def validate_raw_record_shape(record: dict[str, Any]) -> bool:
    return all(column in record for column in RAW_COLUMNS)


def normalize_record(record: dict[str, Any], next_id: int, scraped_at: str) -> dict[str, str] | None:
    if not validate_raw_record_shape(record):
        return None

    url = stringify(record["cover href"])
    image = stringify(record["note-slider-img src"])
    if not url or not image:
        return None

    title = stringify(record["title"])
    desc = stringify(record["desc"])
    note_id = extract_note_id(url)
    author_url = stringify(record["name href"])

    row = {column: "" for column in STANDARD_COLUMNS}
    row.update(
        {
            "id": str(next_id),
            "note_id": note_id,
            "url": url,
            "title": title,
            "content": strip_tags(desc),
            "author_id": extract_author_id(author_url),
            "author_name": stringify(record["username"]),
            "likes": clean_number(record["like-wrapper"]),
            "comments": clean_number(record["chat-wrapper"] or record["total"]),
            "collects": clean_number(record["collect-wrapper"]),
            "tags": "; ".join(extract_tags(f"{title}\n{desc}")),
            "images": image,
            "local_image_path": "",
            "scraped_at": scraped_at,
            "media_type": "image_text",
            "push_time": stringify(record["date"]),
            "review_status": "待审核",
        }
    )
    for column in EMPTY_ANNOTATION_COLUMNS:
        row[column] = ""
    return row


def read_pool(pool_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not pool_path.exists():
        raise FileNotFoundError(f"Sample pool not found: {pool_path}")
    with pool_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    missing = [column for column in STANDARD_COLUMNS if column not in fieldnames]
    if missing:
        raise ValueError(f"Sample pool is missing required columns: {missing}")
    return fieldnames, rows


def read_raw_json(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() != ".json":
        raise ValueError(f"Only Easy Scraper JSON files are supported: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"JSON root must be a list matching the 6.json structure: {path}")
    return [item for item in data if isinstance(item, dict)]


def discover_input_files(input_paths: list[str]) -> list[Path]:
    if not input_paths:
        raise ValueError("Please provide one or more Easy Scraper JSON files.")
    paths = [Path(path).expanduser().resolve() for path in input_paths]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Input file not found: {missing[0]}")
    return paths


def build_existing_keys(rows: list[dict[str, str]]) -> tuple[set[str], set[str]]:
    urls = {normalize_url(row.get("url", "")) for row in rows if normalize_url(row.get("url", ""))}
    note_ids = {row.get("note_id", "").strip() for row in rows if row.get("note_id", "").strip()}
    return urls, note_ids


def next_pool_id(rows: list[dict[str, str]]) -> int:
    ids = [int(row["id"]) for row in rows if str(row.get("id", "")).isdigit()]
    return (max(ids) if ids else 0) + 1


def append_raw_to_pool(input_files: list[Path], pool_path: Path, dry_run: bool) -> dict[str, Any]:
    fieldnames, pool_rows = read_pool(pool_path)
    existing_urls, existing_note_ids = build_existing_keys(pool_rows)
    seen_urls: set[str] = set()
    seen_note_ids: set[str] = set()
    new_rows: list[dict[str, str]] = []
    skipped_invalid = 0
    skipped_duplicate = 0
    raw_total = 0
    next_id = next_pool_id(pool_rows)
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for input_file in input_files:
        records = read_raw_json(input_file)
        raw_total += len(records)
        for record in records:
            row = normalize_record(record, next_id, scraped_at)
            if row is None:
                skipped_invalid += 1
                continue

            normalized_url = normalize_url(row["url"])
            note_id = row["note_id"].strip()
            is_duplicate = (
                (normalized_url and normalized_url in existing_urls)
                or (normalized_url and normalized_url in seen_urls)
                or (note_id and note_id in existing_note_ids)
                or (note_id and note_id in seen_note_ids)
            )
            if is_duplicate:
                skipped_duplicate += 1
                continue

            new_rows.append(row)
            if normalized_url:
                seen_urls.add(normalized_url)
            if note_id:
                seen_note_ids.add(note_id)
            next_id += 1

    if not dry_run and new_rows:
        with pool_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(pool_rows + new_rows)

    return {
        "pool_path": str(pool_path),
        "input_files": [str(path) for path in input_files],
        "raw_total": raw_total,
        "appended": len(new_rows),
        "skipped_invalid": skipped_invalid,
        "skipped_duplicate": skipped_duplicate,
        "id_start": new_rows[0]["id"] if new_rows else "",
        "id_end": new_rows[-1]["id"] if new_rows else "",
        "dry_run": dry_run,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append Easy Scraper JSON exports matching 6.json to xhs_sample_pool_v1.csv."
    )
    parser.add_argument("inputs", nargs="*", help="Easy Scraper JSON files matching the 6.json structure.")
    parser.add_argument("--pool", default=str(DEFAULT_POOL_PATH), help="Path to xhs_sample_pool_v1.csv.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing to the CSV.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pool_path = Path(args.pool).expanduser().resolve()
    try:
        input_files = discover_input_files(args.inputs)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    result = append_raw_to_pool(input_files, pool_path, args.dry_run)

    print("append_raw_to_pool completed")
    print(f"pool_path: {result['pool_path']}")
    print(f"input_files: {len(result['input_files'])}")
    for path in result["input_files"]:
        print(f"  - {path}")
    print(f"raw_total: {result['raw_total']}")
    print(f"appended: {result['appended']}")
    print(f"skipped_duplicate: {result['skipped_duplicate']}")
    print(f"skipped_invalid: {result['skipped_invalid']}")
    if result["appended"]:
        print(f"id_range: {result['id_start']} - {result['id_end']}")
    print(f"dry_run: {result['dry_run']}")


if __name__ == "__main__":
    main()


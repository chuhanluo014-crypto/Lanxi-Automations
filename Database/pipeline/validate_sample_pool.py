from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATAPOOL_ROOT = PROJECT_ROOT / "Database" / "Datapool"
DEFAULT_POOL_PATH = DATAPOOL_ROOT / "data-pool" / "xhs_sample_pool_v1.csv"

REQUIRED_COLUMNS = [
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

REQUIRED_ANNOTATIONS = [
    "topic",
    "scene",
    "emotion",
    "hook",
    "reusable_structure",
    "risk_level",
    "keep_status",
]

VALID_RISK_LEVELS = {"低", "中", "高"}
VALID_KEEP_STATUS = {"保留", "降权", "剔除"}
VALID_REVIEW_STATUS = {"待审核", "已确认", "需修改"}


def normalize_url(url: str) -> str:
    return (url or "").split("?")[0].strip()


def read_pool(pool_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not pool_path.exists():
        raise FileNotFoundError(f"Sample pool not found: {pool_path}")
    with pool_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def duplicate_values(rows: list[dict[str, str]], column: str, normalizer=None) -> list[str]:
    values: list[str] = []
    for row in rows:
        value = str(row.get(column, "") or "").strip()
        if normalizer:
            value = normalizer(value)
        if value:
            values.append(value)
    return [value for value, count in Counter(values).items() if count > 1]


def invalid_int_rows(rows: list[dict[str, str]], column: str) -> list[str]:
    bad: list[str] = []
    for row in rows:
        value = str(row.get(column, "") or "").strip()
        if not re.fullmatch(r"\d+", value):
            bad.append(row.get("id", ""))
    return bad


def rows_missing_any(rows: list[dict[str, str]], columns: list[str]) -> list[str]:
    return [
        row.get("id", "")
        for row in rows
        if any(not str(row.get(column, "") or "").strip() for column in columns)
    ]


def missing_local_images(rows: list[dict[str, str]]) -> list[str]:
    missing: list[str] = []
    for row in rows:
        local_path = str(row.get("local_image_path", "") or "").strip()
        if not local_path or not (DATAPOOL_ROOT / local_path).is_file():
            missing.append(row.get("id", ""))
    return missing


def invalid_choice_rows(rows: list[dict[str, str]], column: str, valid_values: set[str]) -> list[str]:
    bad: list[str] = []
    for row in rows:
        value = str(row.get(column, "") or "").strip()
        if value and value not in valid_values:
            bad.append(row.get("id", ""))
    return bad


def summarize_sample_pool(pool_path: Path, require_confirmed: bool) -> tuple[list[str], list[str], dict[str, Any]]:
    fieldnames, rows = read_pool(pool_path)
    errors: list[str] = []
    warnings: list[str] = []

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing_columns:
        errors.append(f"missing_columns: {missing_columns}")
        return errors, warnings, {"rows": len(rows)}

    duplicate_ids = duplicate_values(rows, "id")
    duplicate_note_ids = duplicate_values(rows, "note_id")
    duplicate_urls = duplicate_values(rows, "url", normalize_url)
    if duplicate_ids:
        errors.append(f"duplicate_ids: {len(duplicate_ids)} {duplicate_ids[:20]}")
    if duplicate_note_ids:
        errors.append(f"duplicate_note_ids: {len(duplicate_note_ids)} {duplicate_note_ids[:20]}")
    if duplicate_urls:
        errors.append(f"duplicate_urls: {len(duplicate_urls)} {duplicate_urls[:20]}")

    for column in ["id", "likes", "comments", "collects"]:
        bad = invalid_int_rows(rows, column)
        if bad:
            errors.append(f"invalid_integer_{column}: {len(bad)} ids={bad[:20]}")

    missing_images = rows_missing_any(rows, ["images"])
    if missing_images:
        errors.append(f"missing_images_column_value: {len(missing_images)} ids={missing_images[:20]}")

    missing_local = missing_local_images(rows)
    if missing_local:
        errors.append(f"missing_local_image_files: {len(missing_local)} ids={missing_local[:20]}")

    missing_annotations = rows_missing_any(rows, REQUIRED_ANNOTATIONS)
    if missing_annotations:
        errors.append(f"missing_required_annotations: {len(missing_annotations)} ids={missing_annotations[:20]}")

    invalid_risk = invalid_choice_rows(rows, "risk_level", VALID_RISK_LEVELS)
    invalid_keep = invalid_choice_rows(rows, "keep_status", VALID_KEEP_STATUS)
    invalid_review = invalid_choice_rows(rows, "review_status", VALID_REVIEW_STATUS)
    if invalid_risk:
        errors.append(f"invalid_risk_level: {len(invalid_risk)} ids={invalid_risk[:20]}")
    if invalid_keep:
        errors.append(f"invalid_keep_status: {len(invalid_keep)} ids={invalid_keep[:20]}")
    if invalid_review:
        errors.append(f"invalid_review_status: {len(invalid_review)} ids={invalid_review[:20]}")

    pending = [
        row.get("id", "")
        for row in rows
        if str(row.get("review_status", "") or "").strip() == "待审核"
    ]
    if pending and require_confirmed:
        errors.append(f"pending_review_rows: {len(pending)} ids={pending[:20]}")
    elif pending:
        warnings.append(f"pending_review_rows: {len(pending)} ids={pending[:20]}")

    medium_or_high_without_notes = [
        row.get("id", "")
        for row in rows
        if str(row.get("risk_level", "") or "").strip() in {"中", "高"}
        and not str(row.get("notes", "") or "").strip()
    ]
    down_or_removed_without_notes = [
        row.get("id", "")
        for row in rows
        if str(row.get("keep_status", "") or "").strip() in {"降权", "剔除"}
        and not str(row.get("notes", "") or "").strip()
    ]
    if medium_or_high_without_notes:
        warnings.append(
            f"medium_or_high_risk_without_notes: {len(medium_or_high_without_notes)} "
            f"ids={medium_or_high_without_notes[:20]}"
        )
    if down_or_removed_without_notes:
        warnings.append(
            f"down_or_removed_without_notes: {len(down_or_removed_without_notes)} "
            f"ids={down_or_removed_without_notes[:20]}"
        )

    summary = {
        "rows": len(rows),
        "review_status": dict(Counter(row.get("review_status", "") for row in rows)),
        "keep_status": dict(Counter(row.get("keep_status", "") for row in rows)),
        "risk_level": dict(Counter(row.get("risk_level", "") for row in rows)),
    }
    return errors, warnings, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate xhs_sample_pool_v1.csv before MySQL import.")
    parser.add_argument("--pool", default=str(DEFAULT_POOL_PATH), help="Path to xhs_sample_pool_v1.csv.")
    parser.add_argument(
        "--require-confirmed",
        action="store_true",
        help="Fail if any row still has review_status=待审核.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors, warnings, summary = summarize_sample_pool(
        pool_path=Path(args.pool).expanduser().resolve(),
        require_confirmed=args.require_confirmed,
    )
    print("validate_sample_pool completed")
    print(f"rows: {summary.get('rows')}")
    print(f"review_status: {summary.get('review_status', {})}")
    print(f"keep_status: {summary.get('keep_status', {})}")
    print(f"risk_level: {summary.get('risk_level', {})}")
    print(f"errors: {len(errors)}")
    for error in errors:
        print(f"  ERROR {error}")
    print(f"warnings: {len(warnings)}")
    for warning in warnings:
        print(f"  WARNING {warning}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()


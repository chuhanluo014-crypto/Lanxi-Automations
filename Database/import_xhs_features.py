from __future__ import annotations

import argparse
import csv
import getpass
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = PROJECT_ROOT / "Database" / "Datapool" / "features" / "xhs_text_features_v1.csv"
DEFAULT_DATABASE = "xhs_ip_lab"
DEFAULT_TABLE = "xhs_text_features"

TABLE_COLUMNS = [
    "sample_id",
    "note_id",
    "url",
    "title",
    "topic",
    "scene",
    "emotion",
    "pain_point",
    "content_structure",
    "title_template",
    "title_length_bucket",
    "hook",
    "platform_keywords",
    "likes",
    "comments",
    "collects",
    "engagement_score",
    "keep_status",
    "risk_level",
    "review_status",
    "push_time",
    "engagement_level",
]


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `{table}` (
    `sample_id` INT NOT NULL,
    `note_id` VARCHAR(80) NULL,
    `url` VARCHAR(1200) NULL,
    `title` TEXT NULL,
    `topic` VARCHAR(255) NULL,
    `scene` VARCHAR(255) NULL,
    `emotion` VARCHAR(255) NULL,
    `pain_point` VARCHAR(255) NULL,
    `content_structure` VARCHAR(255) NULL,
    `title_template` VARCHAR(255) NULL,
    `title_length_bucket` VARCHAR(50) NULL,
    `hook` VARCHAR(255) NULL,
    `platform_keywords` TEXT NULL,
    `likes` INT NOT NULL DEFAULT 0,
    `comments` INT NOT NULL DEFAULT 0,
    `collects` INT NOT NULL DEFAULT 0,
    `engagement_score` DECIMAL(10,4) NOT NULL DEFAULT 0,
    `keep_status` VARCHAR(50) NULL,
    `risk_level` VARCHAR(50) NULL,
    `review_status` VARCHAR(50) NULL,
    `push_time` DATE NULL,
    `engagement_level` VARCHAR(50) NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`sample_id`),
    KEY `idx_xhs_text_features_note_id` (`note_id`),
    KEY `idx_xhs_text_features_pain_point` (`pain_point`),
    KEY `idx_xhs_text_features_title_template` (`title_template`),
    KEY `idx_xhs_text_features_engagement_level` (`engagement_level`),
    CONSTRAINT `fk_xhs_text_features_sample`
        FOREIGN KEY (`sample_id`) REFERENCES `xhs_samples` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def load_mysql_driver() -> tuple[Any, str]:
    try:
        import mysql.connector  # type: ignore

        return mysql.connector, "mysql-connector-python"
    except ImportError:
        pass

    try:
        import pymysql  # type: ignore

        return pymysql, "pymysql"
    except ImportError as exc:
        raise SystemExit(
            "MySQL Python driver is missing. Install one of these:\n"
            "  pip install mysql-connector-python\n"
            "or:\n"
            "  pip install pymysql"
        ) from exc


def parse_int(value: Any) -> int:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def parse_decimal(value: Any) -> Decimal:
    text = str(value or "").strip()
    if not text:
        return Decimal("0")
    try:
        return Decimal(text).quantize(Decimal("0.0001"))
    except InvalidOperation:
        return Decimal("0")


def parse_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {column: normalize_text(row.get(column)) for column in TABLE_COLUMNS}
    normalized["sample_id"] = parse_int(row.get("sample_id"))
    normalized["likes"] = parse_int(row.get("likes"))
    normalized["comments"] = parse_int(row.get("comments"))
    normalized["collects"] = parse_int(row.get("collects"))
    normalized["engagement_score"] = parse_decimal(row.get("engagement_score"))
    normalized["push_time"] = parse_date(row.get("push_time"))
    return normalized


def read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Feature CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing_columns = [column for column in TABLE_COLUMNS if column not in (reader.fieldnames or [])]
        if missing_columns:
            raise ValueError(f"Feature CSV missing columns: {missing_columns}")
        rows = [normalize_row(row) for row in reader]

    rows = [row for row in rows if row["sample_id"]]
    if not rows:
        raise ValueError("No importable rows found in the feature CSV file.")
    return rows


def prompt_password_if_needed(args: argparse.Namespace) -> None:
    if args.password is None:
        print("Password input is hidden. Type the password and press Enter.")
        args.password = getpass.getpass(f"MySQL password for {args.user}@{args.host}: ")


def connect_with_driver(driver: Any, driver_name: str, args: argparse.Namespace) -> Any:
    config = {
        "host": args.host,
        "port": args.port,
        "user": args.user,
        "password": args.password,
        "database": args.database,
        "charset": "utf8mb4",
    }
    try:
        if driver_name == "mysql-connector-python":
            return driver.connect(**config)
        return driver.connect(**config, autocommit=False)
    except Exception as exc:
        raise SystemExit(
            "MySQL login failed.\n"
            f"User: {args.user}\n"
            f"Host: {args.host}:{args.port}\n"
            f"Database: {args.database}\n"
            "Check that the database was initialized, the user exists, and the password is correct."
        ) from exc


def create_table_if_needed(connection: Any, table: str) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(CREATE_TABLE_SQL.format(table=table))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def build_upsert_sql(table: str) -> str:
    quoted_columns = ", ".join(f"`{column}`" for column in TABLE_COLUMNS)
    placeholders = ", ".join(["%s"] * len(TABLE_COLUMNS))
    updates = ", ".join(
        f"`{column}` = VALUES(`{column}`)"
        for column in TABLE_COLUMNS
        if column != "sample_id"
    )
    return (
        f"INSERT INTO `{table}` ({quoted_columns}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {updates}"
    )


def import_rows(connection: Any, rows: list[dict[str, Any]], table: str) -> None:
    sql = build_upsert_sql(table)
    values = [tuple(row[column] for column in TABLE_COLUMNS) for row in rows]
    cursor = connection.cursor()
    try:
        cursor.executemany(sql, values)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import xhs_text_features_v1.csv into local MySQL.")
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH), help="Path to xhs_text_features_v1.csv.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "xhs_user"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD"))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE", DEFAULT_DATABASE))
    parser.add_argument("--table", default=os.getenv("MYSQL_FEATURE_TABLE", DEFAULT_TABLE))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv).expanduser().resolve()
    rows = read_csv_rows(csv_path)
    prompt_password_if_needed(args)
    driver, driver_name = load_mysql_driver()
    connection = connect_with_driver(driver, driver_name, args)
    try:
        create_table_if_needed(connection, args.table)
        import_rows(connection, rows, args.table)
    finally:
        connection.close()

    print(f"Import completed: {len(rows)} rows -> {args.database}.{args.table}")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()

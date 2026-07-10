from __future__ import annotations

import argparse
import csv
import getpass
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_PATH = PROJECT_ROOT / "Database" / "Datapool" / "data-pool" / "xhs_sample_pool_v1.csv"
DEFAULT_DATABASE = "xhs_ip_lab"
DEFAULT_TABLE = "xhs_samples"

TABLE_COLUMNS = [
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
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return 0
    number = float(match.group(0))
    if "\u4e07" in text or "w" in text.lower():
        number *= 10000
    return int(round(number))


def parse_datetime(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


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


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {column: str(row.get(column, "") or "").strip() for column in TABLE_COLUMNS}
    normalized["id"] = parse_int(row.get("id"))
    normalized["likes"] = parse_int(row.get("likes"))
    normalized["comments"] = parse_int(row.get("comments"))
    normalized["collects"] = parse_int(row.get("collects"))
    normalized["scraped_at"] = parse_datetime(row.get("scraped_at"))
    normalized["push_time"] = parse_date(row.get("push_time"))
    return normalized


def read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = [normalize_row(row) for row in reader]

    rows = [row for row in rows if row["id"]]
    if not rows:
        raise ValueError("No importable rows found in the CSV file.")
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
            "Check that the database was initialized, the user exists, and the password is correct.\n"
            "If needed, log in as root and run:\n"
            "  CREATE USER IF NOT EXISTS 'xhs_user'@'localhost' IDENTIFIED BY 'your_password';\n"
            "  GRANT ALL PRIVILEGES ON xhs_ip_lab.* TO 'xhs_user'@'localhost';\n"
            "  FLUSH PRIVILEGES;"
        ) from exc


def build_upsert_sql(table: str) -> str:
    quoted_columns = ", ".join(f"`{column}`" for column in TABLE_COLUMNS)
    placeholders = ", ".join(["%s"] * len(TABLE_COLUMNS))
    updates = ", ".join(
        f"`{column}` = VALUES(`{column}`)"
        for column in TABLE_COLUMNS
        if column != "id"
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
    parser = argparse.ArgumentParser(description="Import xhs_sample_pool_v1.csv into local MySQL.")
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH), help="Path to xhs_sample_pool_v1.csv.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "xhs_user"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD"))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE", DEFAULT_DATABASE))
    parser.add_argument("--table", default=os.getenv("MYSQL_TABLE", DEFAULT_TABLE))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv).expanduser().resolve()
    rows = read_csv_rows(csv_path)
    prompt_password_if_needed(args)
    driver, driver_name = load_mysql_driver()
    connection = connect_with_driver(driver, driver_name, args)
    try:
        import_rows(connection, rows, args.table)
    finally:
        connection.close()
    print(f"Import completed: {len(rows)} rows -> {args.database}.{args.table}")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATAPOOL_ROOT = PROJECT_ROOT / "Database" / "Datapool"
DEFAULT_POOL_PATH = DATAPOOL_ROOT / "data-pool" / "xhs_sample_pool_v1.csv"
DEFAULT_IMAGE_DIR = DATAPOOL_ROOT / "data-images"
RELATIVE_IMAGE_DIR = "data-images"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Referer": "https://www.xiaohongshu.com/",
}


def safe_name(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text)
    return text[:80] or fallback


def first_image_url(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    item_text = str(item or "").strip()
                    if item_text.startswith("http"):
                        return item_text
        except json.JSONDecodeError:
            pass
    for part in re.split(r"\s*;\s*", text):
        if part.strip().startswith("http"):
            return part.strip()
    return text if text.startswith("http") else ""


def extension_from_response(url: str, content_type: str | None) -> str:
    content_type = (content_type or "").split(";")[0].strip().lower()
    if content_type:
        extension = mimetypes.guess_extension(content_type)
        if extension:
            return ".jpg" if extension == ".jpe" else extension
    path = urlparse(url).path.lower()
    for extension in [".webp", ".jpg", ".jpeg", ".png", ".gif"]:
        if path.endswith(extension):
            return ".jpg" if extension == ".jpeg" else extension
    return ".webp"


def read_pool(pool_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not pool_path.exists():
        raise FileNotFoundError(f"Sample pool not found: {pool_path}")
    with pool_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_pool(pool_path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with pool_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def local_file_exists(datapool_root: Path, local_path: str) -> bool:
    if not local_path:
        return False
    return (datapool_root / local_path).is_file()


def should_download(row: dict[str, str], datapool_root: Path, overwrite: bool, ids: set[str]) -> bool:
    if ids and row.get("id", "") not in ids:
        return False
    if not first_image_url(row.get("images", "")):
        return False
    if overwrite:
        return True
    return not local_file_exists(datapool_root, row.get("local_image_path", "").strip())


def download_one(url: str, target_path: Path, timeout: int) -> None:
    request = Request(url, headers=REQUEST_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        content = response.read()
        if len(content) < 500:
            raise ValueError(f"downloaded content is too small: {len(content)} bytes")
        target_path.write_bytes(content)


def download_images(
    pool_path: Path,
    image_dir: Path,
    dry_run: bool,
    overwrite: bool,
    ids: set[str],
    timeout: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    fieldnames, rows = read_pool(pool_path)
    if "local_image_path" not in fieldnames:
        raise ValueError("Sample pool is missing local_image_path column.")

    image_dir.mkdir(parents=True, exist_ok=True)
    targets = [
        row for row in rows if should_download(row, DATAPOOL_ROOT, overwrite=overwrite, ids=ids)
    ]
    downloaded = 0
    failed: list[tuple[str, str]] = []

    for row in targets:
        image_url = first_image_url(row.get("images", ""))
        note_id = row.get("note_id", "")
        row_id = row.get("id", "")
        extension = ".webp"

        if not dry_run:
            try:
                request = Request(image_url, headers=REQUEST_HEADERS)
                with urlopen(request, timeout=timeout) as response:
                    content = response.read()
                    if len(content) < 500:
                        raise ValueError(f"downloaded content is too small: {len(content)} bytes")
                    extension = extension_from_response(image_url, response.headers.get("Content-Type"))
                    filename = f"{safe_name(row_id)}_{safe_name(note_id)}{extension}"
                    target_path = image_dir / filename
                    target_path.write_bytes(content)
                    row["local_image_path"] = f"{RELATIVE_IMAGE_DIR}/{filename}"
                    downloaded += 1
            except Exception as exc:  # noqa: BLE001
                failed.append((row_id, str(exc)))
            time.sleep(sleep_seconds)

    if not dry_run:
        write_pool(pool_path, fieldnames, rows)

    return {
        "pool_path": str(pool_path),
        "image_dir": str(image_dir),
        "targets": len(targets),
        "downloaded": downloaded,
        "failed": failed,
        "dry_run": dry_run,
    }


def parse_id_filter(value: str) -> set[str]:
    if not value:
        return set()
    ids: set[str] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            if start.strip().isdigit() and end.strip().isdigit():
                ids.update(str(number) for number in range(int(start), int(end) + 1))
        else:
            ids.add(part)
    return ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download images and fill local_image_path.")
    parser.add_argument("--pool", default=str(DEFAULT_POOL_PATH), help="Path to xhs_sample_pool_v1.csv.")
    parser.add_argument("--image-dir", default=str(DEFAULT_IMAGE_DIR), help="Directory for downloaded images.")
    parser.add_argument("--ids", default="", help="Only process selected ids, e.g. 468-520 or 468,469.")
    parser.add_argument("--dry-run", action="store_true", help="Preview targets without downloading.")
    parser.add_argument("--overwrite", action="store_true", help="Re-download even if local_image_path exists.")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--sleep", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = download_images(
        pool_path=Path(args.pool).expanduser().resolve(),
        image_dir=Path(args.image_dir).expanduser().resolve(),
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        ids=parse_id_filter(args.ids),
        timeout=args.timeout,
        sleep_seconds=args.sleep,
    )
    print("download_images completed")
    print(f"pool_path: {result['pool_path']}")
    print(f"image_dir: {result['image_dir']}")
    print(f"targets: {result['targets']}")
    print(f"downloaded: {result['downloaded']}")
    print(f"failed: {len(result['failed'])}")
    for row_id, error in result["failed"][:20]:
        print(f"  - id={row_id}: {error}")
    print(f"dry_run: {result['dry_run']}")


if __name__ == "__main__":
    main()


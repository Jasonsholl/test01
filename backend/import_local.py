from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT_DIR / "site"
IMAGES_DIR = SITE_DIR / "images"
INDEX_PATH = SITE_DIR / "index.json"
MANIFEST_PATH = SITE_DIR / "manifest.json"
MINIAPP_DIR = ROOT_DIR / "miniapp"
MINIAPP_ASSETS_DIR = MINIAPP_DIR / "assets"
LOCAL_MANIFEST_PATH = MINIAPP_DIR / "utils" / "localManifest.js"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now_shanghai() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_images(source: Path) -> list[Path]:
    if source.is_file():
        candidates = [source]
    else:
        candidates = sorted(path for path in source.iterdir() if path.is_file())

    return [path for path in candidates if path.suffix.lower() in IMAGE_EXTENSIONS]


def _existing_hashes(index: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("sha256")) for item in index if item.get("sha256")}


def _build_manifest(index: list[dict[str, Any]], max_items: int = 10) -> dict[str, Any]:
    items = sorted(index, key=lambda item: str(item.get("datetimeUtc", "")), reverse=True)[:max_items]
    return {
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(items),
        "items": [
            {
                "id": str(item["id"]),
                "date": str(item["date"]),
                "caption": str(item.get("caption") or ""),
                "path": str(item["path"]),
                "datetimeUtc": str(item["datetimeUtc"]),
            }
            for item in items
        ],
    }


def _sync_miniapp_bundle(manifest: dict[str, Any]) -> None:
    if MINIAPP_ASSETS_DIR.exists():
        shutil.rmtree(MINIAPP_ASSETS_DIR)
    MINIAPP_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    local_items: list[dict[str, Any]] = []
    for item in manifest.get("items", []):
        source = SITE_DIR / str(item["path"])
        if not source.exists():
            continue

        local_path = Path("assets") / str(item["path"])
        target = MINIAPP_DIR / local_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

        local_item = dict(item)
        local_item["path"] = str(local_path).replace("\\", "/")
        local_items.append(local_item)

    local_manifest = {
        "updatedAt": manifest.get("updatedAt", ""),
        "count": len(local_items),
        "items": local_items,
    }
    content = "module.exports = {\n  LOCAL_MANIFEST: "
    content += json.dumps(local_manifest, ensure_ascii=False, indent=2)
    content += "\n};\n"
    LOCAL_MANIFEST_PATH.write_text(content, encoding="utf-8")


def _unique_target_path(day_dir: Path, image_hash: str, suffix: str) -> Path:
    target = day_dir / f"{image_hash[:16]}{suffix.lower()}"
    counter = 2
    while target.exists():
        target = day_dir / f"{image_hash[:16]}-{counter}{suffix.lower()}"
        counter += 1
    return target


def import_images(source: Path, date: str, limit: int, caption: str) -> int:
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source does not exist: {source}")

    images = _collect_images(source)
    if limit > 0:
        images = images[:limit]

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    index: list[dict[str, Any]] = _load_json(INDEX_PATH, default=[])
    seen_hashes = _existing_hashes(index)
    day_dir = IMAGES_DIR / date
    day_dir.mkdir(parents=True, exist_ok=True)

    imported = 0
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for image in images:
        image_hash = _file_hash(image)
        if image_hash in seen_hashes:
            continue

        target = _unique_target_path(day_dir, image_hash, image.suffix)
        shutil.copy2(image, target)

        relative_path = str(Path("images") / date / target.name).replace("\\", "/")
        item_id = f"local_{image_hash[:16]}"
        index.append(
            {
                "id": item_id,
                "source": "local",
                "originalName": image.name,
                "sha256": image_hash,
                "date": date,
                "datetimeUtc": now_utc,
                "caption": caption,
                "path": relative_path,
            }
        )
        seen_hashes.add(image_hash)
        imported += 1

    index.sort(key=lambda item: str(item.get("datetimeUtc", "")), reverse=True)
    _dump_json(INDEX_PATH, index)
    manifest = _build_manifest(index, max_items=10)
    _dump_json(MANIFEST_PATH, manifest)
    _sync_miniapp_bundle(manifest)

    return imported


def main() -> None:
    parser = argparse.ArgumentParser(description="Import local images into the miniapp static site.")
    parser.add_argument("source", help="Image file or folder to import.")
    parser.add_argument("--date", default=_now_shanghai().strftime("%Y-%m-%d"), help="Image date, default today in UTC+8.")
    parser.add_argument("--limit", type=int, default=10, help="Max images to import from the source folder. Use 0 for no limit.")
    parser.add_argument("--caption", default="", help="Optional caption stored in manifest.")
    args = parser.parse_args()

    imported = import_images(Path(args.source), args.date, args.limit, args.caption)
    if imported:
        print(f"Imported {imported} image(s) for {args.date}.")
    else:
        print(f"No new images imported for {args.date}; manifest refreshed.")


if __name__ == "__main__":
    main()

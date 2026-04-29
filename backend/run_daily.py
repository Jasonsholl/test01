from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from telethon import TelegramClient


ROOT_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT_DIR / "site"
IMAGES_DIR = SITE_DIR / "images"
INDEX_PATH = SITE_DIR / "index.json"
MANIFEST_PATH = SITE_DIR / "manifest.json"
SESSION_PATH = Path(__file__).resolve().parent / ".tg.session"


@dataclass(frozen=True)
class PhotoItem:
    channel: str
    message_id: int
    date: str  # YYYY-MM-DD in Asia/Shanghai
    datetime_utc: str  # ISO string in UTC
    caption: str
    path: str  # site/ relative path, e.g. images/2026-04-27/123.jpg

    @property
    def id(self) -> str:
        return f"{self.channel}_{self.message_id}"


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now_shanghai() -> datetime:
    # Asia/Shanghai = UTC+8, no DST.
    return datetime.now(timezone(timedelta(hours=8)))


def _day_bounds_shanghai(day: datetime) -> tuple[datetime, datetime]:
    start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def _iter_recent_photo_messages(
    client: TelegramClient, channel: str, start_utc: datetime, end_utc: datetime
) -> Iterable[Any]:
    # Iterate newest → older, stop once we are older than start_utc.
    for message in client.iter_messages(channel, limit=400):
        if not message:
            continue
        if not message.date:
            continue
        message_dt_utc = message.date
        if message_dt_utc.tzinfo is None:
            message_dt_utc = message_dt_utc.replace(tzinfo=timezone.utc)
        if message_dt_utc < start_utc:
            break
        if message_dt_utc >= end_utc:
            continue
        if message.photo:
            yield message


def _load_seen_ids(index: list[dict[str, Any]]) -> set[int]:
    seen: set[int] = set()
    for item in index:
        mid = item.get("messageId")
        if isinstance(mid, int):
            seen.add(mid)
    return seen


def _index_item_from_photo(photo: PhotoItem) -> dict[str, Any]:
    return {
        "channel": photo.channel,
        "messageId": photo.message_id,
        "date": photo.date,
        "datetimeUtc": photo.datetime_utc,
        "caption": photo.caption,
        "path": photo.path,
    }


def _photo_from_index_item(item: dict[str, Any]) -> PhotoItem | None:
    try:
        return PhotoItem(
            channel=str(item["channel"]),
            message_id=int(item["messageId"]),
            date=str(item["date"]),
            datetime_utc=str(item["datetimeUtc"]),
            caption=str(item.get("caption") or ""),
            path=str(item["path"]),
        )
    except Exception:
        return None


def _build_manifest(index: list[dict[str, Any]], max_items: int = 10) -> dict[str, Any]:
    photos: list[PhotoItem] = []
    for raw in index:
        photo = _photo_from_index_item(raw)
        if photo:
            photos.append(photo)

    photos.sort(key=lambda p: p.datetime_utc, reverse=True)
    photos = photos[:max_items]

    return {
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(photos),
        "items": [
            {
                "id": p.id,
                "date": p.date,
                "caption": p.caption,
                "path": p.path,
                "datetimeUtc": p.datetime_utc,
            }
            for p in photos
        ],
    }


def main() -> None:
    api_id = int(_env("TG_API_ID"))
    api_hash = _env("TG_API_HASH")
    channel = os.environ.get("TG_CHANNEL", "SpecialHer")

    now_sh = _now_shanghai()
    start_sh, end_sh = _day_bounds_shanghai(now_sh)
    start_utc = start_sh.astimezone(timezone.utc)
    end_utc = end_sh.astimezone(timezone.utc)
    date_str = start_sh.strftime("%Y-%m-%d")

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    index: list[dict[str, Any]] = _load_json(INDEX_PATH, default=[])
    seen_message_ids = _load_seen_ids(index)

    new_items: list[dict[str, Any]] = []

    with TelegramClient(str(SESSION_PATH), api_id, api_hash) as client:
        for message in _iter_recent_photo_messages(client, channel, start_utc, end_utc):
            if message.id in seen_message_ids:
                continue

            day_dir = IMAGES_DIR / date_str
            day_dir.mkdir(parents=True, exist_ok=True)
            out_path = day_dir / f"{message.id}.jpg"

            client.download_media(message, file=str(out_path))

            msg_dt_utc = message.date
            if msg_dt_utc.tzinfo is None:
                msg_dt_utc = msg_dt_utc.replace(tzinfo=timezone.utc)

            caption = (message.message or "").strip()
            photo = PhotoItem(
                channel=channel,
                message_id=message.id,
                date=date_str,
                datetime_utc=msg_dt_utc.astimezone(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                caption=caption,
                path=str(Path("images") / date_str / out_path.name).replace("\\", "/"),
            )
            new_items.append(_index_item_from_photo(photo))
            seen_message_ids.add(message.id)

    if new_items:
        index.extend(new_items)
        index.sort(key=lambda x: x.get("datetimeUtc", ""), reverse=True)
        _dump_json(INDEX_PATH, index)

    manifest = _build_manifest(index, max_items=10)
    _dump_json(MANIFEST_PATH, manifest)

    if not new_items:
        print(f"[{date_str}] no new photos; manifest refreshed.")
    else:
        print(f"[{date_str}] downloaded {len(new_items)} new photos; manifest updated.")


if __name__ == "__main__":
    main()


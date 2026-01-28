from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from tinydb import Query, TinyDB

import config

Posted = Query()
_DB: TinyDB | None = None


def _ensure_db_path() -> None:
    dir_name = os.path.dirname(config.DB_FILENAME)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)


def get_db() -> TinyDB:
    global _DB
    if _DB is None:
        _ensure_db_path()
        _DB = TinyDB(config.DB_FILENAME)
    return _DB


def _parse_any_timestamp(value: Any) -> datetime | None:
    """Parse multiple timestamp formats (supports old schema too)."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None

    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None

        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass

        try:
            dt = datetime.strptime(v, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    return None


def initialize_database() -> None:
    """Ensure DB exists and remove very old records (keeps the file small)."""
    db = get_db()
    db.all()  # touch file
    cleanup_old_records()


def cleanup_old_records() -> None:
    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.DB_RETENTION_DAYS)

    to_remove: list[int] = []
    for doc in db.all():
        last_ts = doc.get("last_posted_at") or doc.get("timestamp") or doc.get("date")
        dt = _parse_any_timestamp(last_ts)
        if dt and dt < cutoff:
            to_remove.append(doc.doc_id)

    if to_remove:
        db.remove(doc_ids=to_remove)


def should_skip_deal(asin: str, current_price: float | None) -> bool:
    """Return True if we should NOT post this ASIN again right now."""
    if not asin:
        return False

    db = get_db()
    existing = db.get(Posted.asin == asin)
    if not existing:
        return False

    last_dt = _parse_any_timestamp(existing.get("last_posted_at") or existing.get("timestamp") or existing.get("date"))
    if not last_dt:
        return False

    hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600.0
    if hours_since >= config.POST_COOLDOWN_HOURS:
        return False

    last_price = existing.get("last_price")
    try:
        last_price_f = float(last_price) if last_price is not None else None
    except (TypeError, ValueError):
        last_price_f = None

    if last_price_f and current_price and last_price_f > 0:
        drop_pct = ((last_price_f - current_price) / last_price_f) * 100.0
        if drop_pct >= config.REPOST_PRICE_DROP_PERCENT:
            return False

    return True


def record_posted_deal(deal: dict[str, Any], affiliate_url: str | None = None) -> None:
    if not deal.get("asin"):
        return

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    asin = str(deal["asin"]).strip()
    existing = db.get(Posted.asin == asin)

    payload: dict[str, Any] = {
        "asin": asin,
        "title": deal.get("title"),
        "url": deal.get("product_url"),
        "affiliate_url": affiliate_url,
        "last_price": deal.get("deal_price"),
        "last_original_price": deal.get("original_price"),
        "last_discount": deal.get("discount"),
        "last_posted_at": now,
    }

    if not existing or not existing.get("first_seen_at"):
        payload["first_seen_at"] = now

    db.upsert(payload, Posted.asin == asin)

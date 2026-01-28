#!/usr/bin/env python3
from __future__ import annotations

import html as html_lib
import json
import logging
import random
import sys
import time
from typing import Any

import requests

import config
import database
import scraper

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if config.LOG_TO_FILE:
        handlers.append(logging.FileHandler(config.LOG_FILENAME))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


_TG_SESSION: requests.Session | None = None


def _get_tg_session() -> requests.Session:
    global _TG_SESSION
    if _TG_SESSION is None:
        _TG_SESSION = requests.Session()
    return _TG_SESSION


def send_telegram_message(text: str, image_url: str | None = None, button_url: str | None = None) -> bool:
    """Send message to Telegram.

    - Escapes must be done BEFORE calling this function.
    - If sendPhoto fails, we automatically fall back to sendMessage.
    """
    base_url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
    session = _get_tg_session()

    payload: dict[str, Any] = {
        "chat_id": config.TELEGRAM_CHANNEL_ID,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    if button_url:
        payload["reply_markup"] = json.dumps(
            {"inline_keyboard": [[{"text": "🛒 Buy Now on Amazon", "url": button_url}]]}
        )

    for attempt in range(1, 4):
        try:
            if image_url:
                data = dict(payload)
                data["photo"] = image_url
                data["caption"] = text
                resp = session.post(f"{base_url}/sendPhoto", data=data, timeout=20)

                if resp.status_code != 200:
                    logger.warning("Telegram sendPhoto failed (attempt %s): %s", attempt, resp.text[:300])
                    image_url = None
                    time.sleep(1.5 * attempt)
                    continue

                return True

            data = dict(payload)
            data["text"] = text
            resp = session.post(f"{base_url}/sendMessage", data=data, timeout=20)
            if resp.status_code == 200:
                return True

            logger.warning("Telegram sendMessage failed (attempt %s): %s", attempt, resp.text[:300])
        except requests.RequestException as e:
            logger.warning("Telegram connection error (attempt %s): %s", attempt, e)

        time.sleep(1.5 * attempt)

    return False


def create_affiliate_link(asin: str) -> str:
    return f"{config.BASE_URL}/dp/{asin}/?tag={config.AMAZON_ASSOCIATE_ID}"


def format_message(deal: dict[str, Any]) -> str | None:
    asin = deal.get("asin")
    title = deal.get("title")
    dp = deal.get("deal_price")
    op = deal.get("original_price")
    discount = deal.get("discount")

    if not asin or not title or dp is None or op is None or discount is None:
        return None
    if op <= dp:
        return None

    emoji = config.CATEGORY_EMOJIS.get(deal.get("category", ""), "🔥")
    safe_title = html_lib.escape(str(title))

    if len(safe_title) > 120:
        safe_title = safe_title[:117] + "…"

    msg_lines = [
        f"{emoji} <b>{safe_title}</b>",
        "",
        f"📉 <b>{int(discount)}% OFF</b>",
        f"❌ <s>₹{op:,.0f}</s>",
        f"✅ <b>Deal Price: ₹{dp:,.0f}</b>",
    ]

    if deal.get("limited_time"):
        msg_lines.append("⏳ Limited time deal")

    return "\n".join(msg_lines)


def choose_discount_threshold(deals: list[dict[str, Any]]) -> int:
    base = config.MINIMUM_DISCOUNT
    if not config.ENABLE_DYNAMIC_DISCOUNT:
        return base

    discounts = [d.get("discount") for d in deals if isinstance(d.get("discount"), int)]
    if not discounts:
        return base

    threshold = base
    while threshold > config.LOWEST_DISCOUNT_FLOOR:
        count = sum(1 for d in deals if isinstance(d.get("discount"), int) and d["discount"] >= threshold)
        if count >= config.TARGET_DEALS_PER_RUN:
            return threshold
        threshold -= config.DISCOUNT_FALLBACK_STEP

    return max(config.LOWEST_DISCOUNT_FLOOR, threshold)


def run_bot() -> int:
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("Missing TELEGRAM_BOT_TOKEN environment variable")
        return 2

    database.initialize_database()

    logger.info("Starting scan...")
    deals, captcha_hit = scraper.discover_deals()

    if captcha_hit:
        logger.warning("Stopped early because Amazon returned a CAPTCHA/bot wall.")
        return 0

    logger.info("Discovered %s raw candidates", len(deals))

    threshold = choose_discount_threshold(deals)
    if threshold != config.MINIMUM_DISCOUNT:
        logger.info(
            "Dynamic discount enabled: using %s%% (base=%s%%, floor=%s%%)",
            threshold,
            config.MINIMUM_DISCOUNT,
            config.LOWEST_DISCOUNT_FLOOR,
        )
    else:
        logger.info("Using minimum discount threshold: %s%%", threshold)

    candidates: list[dict[str, Any]] = [
        d
        for d in deals
        if isinstance(d.get("discount"), int)
        and d["discount"] >= threshold
        and isinstance(d.get("deal_price"), (int, float))
        and isinstance(d.get("original_price"), (int, float))
        and d["original_price"] > d["deal_price"]
    ]

    def _sort_key(d: dict[str, Any]) -> tuple[int, float]:
        disc = int(d.get("discount") or 0)
        savings = float(d.get("original_price") or 0) - float(d.get("deal_price") or 0)
        return (disc, savings)

    candidates.sort(key=_sort_key, reverse=True)
    logger.info("%s candidates after filtering", len(candidates))

    posted = 0
    for deal in candidates:
        if posted >= config.MAX_POSTS_PER_RUN:
            break

        asin = str(deal.get("asin") or "").strip()
        dp = float(deal.get("deal_price"))

        if database.should_skip_deal(asin, current_price=dp):
            logger.debug("Skip (cooldown): %s", asin)
            continue

        msg = format_message(deal)
        if not msg:
            continue

        aff_link = create_affiliate_link(asin)
        ok = send_telegram_message(msg, image_url=deal.get("image_url"), button_url=aff_link)
        if not ok:
            logger.warning("Failed to post ASIN=%s", asin)
            continue

        database.record_posted_deal(deal, affiliate_url=aff_link)
        posted += 1

        logger.info(
            "Posted %s/%s | %s%% | %s",
            posted,
            config.MAX_POSTS_PER_RUN,
            deal.get("discount"),
            deal.get("title", "")[:60],
        )

        if config.VALUE_ADD_CONTENT_FREQUENCY > 0 and (posted % config.VALUE_ADD_CONTENT_FREQUENCY == 0):
            tip = random.choice(config.TIPS_AND_TRICKS)
            tip_msg = f"💡 <b>Shopping tip:</b> {html_lib.escape(tip)}"
            send_telegram_message(tip_msg)

        time.sleep(random.uniform(0.8, 1.6))

    logger.info("Run complete. Posted=%s (max_per_run=%s)", posted, config.MAX_POSTS_PER_RUN)
    return 0


if __name__ == "__main__":
    setup_logging()
    sys.exit(run_bot())

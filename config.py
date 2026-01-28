"""Project configuration.

Everything is tuned for Amazon India (amazon.in) + Telegram.

Most values can be overridden via environment variables, so you can tweak
behavior in GitHub Actions/your server without editing code.
"""

from __future__ import annotations

import os


# -----------------------------
# Telegram
# -----------------------------

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHANNEL_ID: str = os.getenv("TELEGRAM_CHANNEL_ID", "@SEMMAOFFERS").strip()


# -----------------------------
# Amazon India + Affiliate
# -----------------------------

BASE_URL: str = "https://www.amazon.in"
AMAZON_ASSOCIATE_ID: str = os.getenv("AMAZON_ASSOCIATE_ID", "semmaoffers-21").strip()


# -----------------------------
# Categories
# Node IDs are Amazon browse node IDs for amazon.in
# -----------------------------

HIGH_TRAFFIC_CATEGORIES: dict[str, str] = {
    "Electronics & Gadgets": "976420031",
    "Fashion & Apparel": "1571272031",
    "Beauty": "1355017031",
    "Health & Personal Care": "1350385031",
    "Jewellery": "1951046031",
    "Sports, Fitness & Outdoors": "1984444031",
}

STANDARD_CATEGORIES: dict[str, str] = {
    "Biscuits & Cookies": "2899877031",
    "Snacks & Nuts (General)": "2899879031",
    "Namkeen & Savory Snacks": "2899881031",
    "Headphones": "1388921031",
    "Luxury Beauty": "5311359031",
    "Chocolates & Confectionery": "2899882031",
}


# Emoji mapping (keys must match category names above)
CATEGORY_EMOJIS: dict[str, str] = {
    "Electronics & Gadgets": "⚡",
    "Fashion & Apparel": "👗",
    "Beauty": "💄",
    "Health & Personal Care": "💊",
    "Jewellery": "💎",
    "Sports, Fitness & Outdoors": "🏋️",
    "Biscuits & Cookies": "🍪",
    "Snacks & Nuts (General)": "🥜",
    "Namkeen & Savory Snacks": "🍿",
    "Headphones": "🎧",
    "Luxury Beauty": "🧴",
    "Chocolates & Confectionery": "🍫",
}


# -----------------------------
# Deal selection
# -----------------------------

# Your original config was 75% which is *extremely* strict and typically yields
# very few deals per day.
MINIMUM_DISCOUNT: int = int(os.getenv("MINIMUM_DISCOUNT", "60"))

# If enabled, the bot will automatically relax the discount threshold when a run
# has too few candidates (so you don't end up with 0–4 posts/day).
ENABLE_DYNAMIC_DISCOUNT: bool = os.getenv("ENABLE_DYNAMIC_DISCOUNT", "1") != "0"
TARGET_DEALS_PER_RUN: int = int(os.getenv("TARGET_DEALS_PER_RUN", "12"))
LOWEST_DISCOUNT_FLOOR: int = int(os.getenv("LOWEST_DISCOUNT_FLOOR", "40"))
DISCOUNT_FALLBACK_STEP: int = int(os.getenv("DISCOUNT_FALLBACK_STEP", "5"))

# Max number of posts to send to Telegram per run
MAX_POSTS_PER_RUN: int = int(os.getenv("MAX_POSTS_PER_RUN", "8"))


# -----------------------------
# Scraper tuning
# -----------------------------

REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
MAX_REQUEST_RETRIES: int = int(os.getenv("MAX_REQUEST_RETRIES", "4"))

# Sleep/jitter between requests to avoid hammering Amazon (polite scraping)
MIN_SLEEP_SECONDS: float = float(os.getenv("MIN_SLEEP_SECONDS", "0.8"))
MAX_SLEEP_SECONDS: float = float(os.getenv("MAX_SLEEP_SECONDS", "2.2"))

# Pages to scan per category (keep low to reduce blocks)
PAGES_PER_HIGH_TRAFFIC_CATEGORY: int = int(os.getenv("PAGES_PER_HIGH_TRAFFIC_CATEGORY", "2"))
PAGES_PER_STANDARD_CATEGORY: int = int(os.getenv("PAGES_PER_STANDARD_CATEGORY", "1"))

# How many items to keep per category (after parsing search page)
MAX_CANDIDATES_PER_CATEGORY: int = int(os.getenv("MAX_CANDIDATES_PER_CATEGORY", "35"))

# Amazon search sort order
AMAZON_SORT: str = os.getenv("AMAZON_SORT", "discount-rank")

# If Amazon shows a CAPTCHA page, stop early to avoid wasting requests.
STOP_ON_CAPTCHA: bool = os.getenv("STOP_ON_CAPTCHA", "1") != "0"


# -----------------------------
# Dedup / database
# -----------------------------

DB_FILENAME: str = os.getenv("DB_FILENAME", "data.json")

# Retain DB records (keeps file small)
DB_RETENTION_DAYS: int = int(os.getenv("DB_RETENTION_DAYS", "14"))

# Skip reposting same ASIN for this long, *unless* price dropped significantly.
POST_COOLDOWN_HOURS: int = int(os.getenv("POST_COOLDOWN_HOURS", "72"))

# Allow repost inside cooldown if price drops by at least this % compared to last
# posted price (helps when deals get better).
REPOST_PRICE_DROP_PERCENT: float = float(os.getenv("REPOST_PRICE_DROP_PERCENT", "8"))


# -----------------------------
# Logging
# -----------------------------

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "0") == "1"
LOG_FILENAME: str = os.getenv("LOG_FILENAME", "bot.log")


# -----------------------------
# User-Agents (static list: avoids fake_useragent failures in CI)
# -----------------------------

USER_AGENTS: list[str] = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    # Chrome (Linux)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


# -----------------------------
# Optional: Value-add content
# -----------------------------

VALUE_ADD_CONTENT_FREQUENCY: int = int(os.getenv("VALUE_ADD_CONTENT_FREQUENCY", "10"))
TIPS_AND_TRICKS: list[str] = [
    "Pro tip: Combine bank cashback + coupon codes for extra savings.",
    "Shopping hack: Check Subscribe & Save for extra discounts.",
    "Sale alert: Big sale seasons are usually Jan and Oct.",
    "Gift card trick: Buy gift cards during sales for extra value.",
    "Free shipping: Add items totaling ₹499+ for free delivery (eligible orders).",
]

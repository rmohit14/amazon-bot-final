# config.py
import os

# --- Telegram Bot Configuration ---
# The token is now loaded securely from an environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = "@SEMMAOFFERS"

# --- Amazon Affiliate Configuration ---
AMAZON_ASSOCIATE_ID = "semmaoffers-21"

# --- Category Split ---
HIGH_TRAFFIC_CATEGORIES = {
    "Health & Personal Care": "1374667031",
    "Home & Kitchen Essentials": "976442031",
    "Mobile Accessories": "1389401031"
}

STANDARD_CATEGORIES = {
    "Electronics": "976419031",
    "Large Appliances": "976418031",
    "Smartwatches": "11599648031",
    "Headphones": "1388921031",
    "Luxury Beauty": "5311359031",
    "Fashion": "6648217031",
    "Books": "976389031"
}

# Minimum discount percentage to consider
MINIMUM_DISCOUNT = 70

# User-Agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
]

# Scheduler intervals (minutes)
HIGH_TRAFFIC_INTERVAL_MIN = 30
STANDARD_INTERVAL_MIN = 60

# Scraper & requests tuning
REQUEST_TIMEOUT = 12
MAX_REQUEST_RETRIES = 4

# Database & logging
# The database path will be read from an environment variable in the cloud,
# defaulting to 'deals.db' when run locally.
DB_FILENAME = os.path.join("/tmp", "data.db")
LOG_FILENAME = "bot.log"

# How many products to fetch per category per run (keeps runs short)

LIMIT_PER_CATEGORY = 10

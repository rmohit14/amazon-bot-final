import os

# --- Telegram Bot Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = "@SEMMAOFFERS"

# --- Amazon Affiliate Configuration ---
AMAZON_ASSOCIATE_ID = "semmaoffers-21"

# --- Category Split ---
HIGH_TRAFFIC_CATEGORIES = {
    "Electronics & Gadgets": "976420031",
    "Fashion & Apparel": "1571272031",
    "Beauty": "1355017031",
    "Health & Personal Care": "1350385031",
    "Jewellery": "1951046031",
    "Sports, Fitness & Outdoors": "1984444031"
}

STANDARD_CATEGORIES = {
    "Biscuits & Cookies": "2899877031",
    "Snacks & Nuts (General)": "2899879031",
    "Namkeen & Savory Snacks": "2899881031",
    "Headphones": "1388921031",
    "Luxury Beauty": "5311359031",
    "Chocolates & Confectionery": "2899882031"
}

# Minimum discount percentage to consider
MINIMUM_DISCOUNT = 75

# User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

# Value-add content configuration
VALUE_ADD_CONTENT_FREQUENCY = 10
TIPS_AND_TRICKS = [
    "💡 *Pro Tip:* Combine bank cashback + coupon codes!",
    "🎯 *Shopping Hack:* Check Subscribe & Save for 15% extra off.",
    "⏰ *Sale Alert:* Great Indian Festival is in Jan & Oct.",
    "🎁 *Gift Card Trick:* Buy gift cards during sales for double savings!",
    "🚚 *Free Shipping:* Add items to cart > ₹499 for free delivery!"
]

# Tuning
REQUEST_TIMEOUT = 15
MAX_REQUEST_RETRIES = 3

# --- CRITICAL FIX: DB must be relative to repo root for GHA persistence ---
DB_FILENAME = "data.json" 
LOG_FILENAME = "bot.log"

# How many products to fetch per category per run
LIMIT_PER_CATEGORY = 15

# Emoji mappings
CATEGORY_EMOJIS = {
    "Electronics": "⚡", "Fashion": "👗", "Beauty": "💄", 
    "Health": "💊", "Jewellery": "💎", "Sports": "🏋️",
    "Snacks": "🍪", "Headphones": "🎧"
}

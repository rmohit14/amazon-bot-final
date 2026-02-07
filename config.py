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

# User-Agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
]

# Scraper & requests tuning
REQUEST_TIMEOUT = 12
MAX_REQUEST_RETRIES = 4

# Database & logging
DB_FILENAME = os.path.join("/tmp", "data.db")
LOG_FILENAME = "bot.log"

# How many products to fetch per category per run
LIMIT_PER_CATEGORY = 15

# --- Scheduling Configuration ---
POSTING_SCHEDULE = {
    "morning": {"hour": 8, "minute": 0},   # 8:00 AM
    "afternoon": {"hour": 14, "minute": 0}, # 2:00 PM
    "evening": {"hour": 20, "minute": 0}    # 8:00 PM
}

# --- Value-add content configuration ---
VALUE_ADD_CONTENT_FREQUENCY = 10  # Post educational content every 5 deals
TIPS_AND_TRICKS = [
    "💡 *Pro Tip:* Always combine bank cashback + coupon codes to stack extra savings!",
    "🎯 *Shopping Hack:* Use Amazon's 'Subscribe & Save' for up to 15% extra discount on regular purchases!",
    "⏰ *Sale Alert:* Amazon Great Indian Festival happens twice a year - January & October. Mark your calendar!",
    "💳 *Money Saver:* Check if your credit card offers additional cashback on Amazon purchases!",
    "📱 *App Exclusive:* Many deals are app-only. Download Amazon app for extra discounts!",
    "🔔 *Never Miss a Deal:* Enable notifications for this channel to get instant deal alerts!",
    "🎁 *Gift Card Trick:* Buy Amazon gift cards during sales and use them later for double savings!",
    "🚚 *Free Shipping Hack:* Add items to cart worth ₹499+ to get free delivery!",
    "⭐ *Review Power:* Products with 4+ star ratings are usually better quality deals!",
    "🔄 *Price Tracker:* Use browser extensions like 'Keepa' to track Amazon price history!"
]

# --- Emoji mappings for categories ---
CATEGORY_EMOJIS = {
    # High Traffic Categories
    "Electronics & Gadgets": "⚡",
    "Fashion & Apparel": "👗",
    "Beauty": "💄",
    "Health & Personal Care": "💊",
    "Jewellery": "💎",
    "Sports, Fitness & Outdoors": "🏋️",

    # Standard Categories
    "Biscuits & Cookies": "🍪",
    "Snacks & Nuts (General)": "🥜",
    "Namkeen & Savory Snacks": "🍿",
    "Headphones": "🎧",
    "Luxury Beauty": "✨",
    "Pet Supplies": "🐾",
    "Chocolates & Confectionery": "🍫",
    "Car & Motorbike Accessories": "🚗"
}

import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = "@YourChannelID"

# Category mapping (example)
CATEGORIES = {
    'Electronics': '12345',
    'Fashion': '67890'
}

# Minimum discount percentage
MINIMUM_DISCOUNT = 75

# Logging & database paths
DB_FILENAME = "data.json"
LOG_FILENAME = "bot.log"

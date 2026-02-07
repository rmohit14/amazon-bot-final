import logging
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN
from telegram import Bot
from scraper import find_deals, scrape_product_details
import database

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def send_to_telegram(chat_id, text):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    bot.send_message(chat_id=chat_id, text=text)

def run_all_cycles():
    categories = {
        'Electronics': '12345',  # Sample category node
        'Fashion': '67890'
    }
    seen_urls = set()
    deal_urls = find_deals(categories, seen_urls)
    
    for url in deal_urls:
        details = scrape_product_details(url)
        if details:
            send_to_telegram(
                '@my_telegram_channel', 
                f"Deal: {details['title']} - {details['deal_price']}! MRP: {details['original_price']}")
        else:
            logging.warning(f"Failed to scrape details for {url}")

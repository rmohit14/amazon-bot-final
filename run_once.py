#!/usr/bin/env python3
import logging
import sys
import os
import random
import time
from datetime import datetime

import config
import scraper
import database

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(config.LOG_FILENAME)]
)

def create_affiliate_link(asin):
    return f"https://www.amazon.in/dp/{asin}/?tag={config.AMAZON_ASSOCIATE_ID}"

def send_telegram_message(text, image_url=None, button_url=None):
    """Unified Telegram sender"""
    import requests
    import json
    
    base_url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
    payload = {
        "chat_id": config.TELEGRAM_CHANNEL_ID,
        "parse_mode": "HTML"
    }
    
    if button_url:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": [[{"text": "🛒 Buy Now on Amazon", "url": button_url}]]
        })

    try:
        if image_url:
            payload["photo"] = image_url
            payload["caption"] = text
            resp = requests.post(f"{base_url}/sendPhoto", data=payload, timeout=20)
        else:
            payload["text"] = text
            resp = requests.post(f"{base_url}/sendMessage", data=payload, timeout=20)
            
        if resp.status_code != 200:
            logging.error(f"Telegram Error: {resp.text}")
            return False
        return True
    except Exception as e:
        logging.error(f"Telegram Connection Error: {e}")
        return False

def format_message(item):
    """Create the formatted deal message"""
    discount = 0
    dp = float(item['deal_price']) if item['deal_price'] else 0
    op = float(item['original_price']) if item['original_price'] else 0
    
    if op > dp > 0:
        discount = int(((op - dp) / op) * 100)

    if discount < config.MINIMUM_DISCOUNT:
        return None

    emoji = config.CATEGORY_EMOJIS.get(item.get('category', ''), '🔥')
    
    msg = f"{emoji} <b>{item['title'][:80]}...</b>\n\n"
    msg += f"📉 <b>{discount}% OFF</b>\n"
    msg += f"❌ <s>₹{item['original_price']}</s>\n"
    msg += f"✅ <b>Deal Price: ₹{item['deal_price']}</b>\n\n"
    msg += "⏳ Limited Time Deal!\n"
    
    return msg, discount

def run_bot():
    logging.info("🚀 Starting Deal Hunt...")
    database.initialize_database()
    
    seen_urls = set()
    
    # Merge categories to run everything in one go
    all_categories = {**config.HIGH_TRAFFIC_CATEGORIES, **config.STANDARD_CATEGORIES}
    
    urls = scraper.find_deals(all_categories, seen_urls)
    logging.info(f"Found {len(urls)} potential deals. Scraping details...")
    
    deals_posted = 0
    
    for url in urls:
        details = scraper.scrape_product_details(url)
        if not details or not details['asin']: continue
        
        if database.is_deal_already_posted(details['asin']):
            logging.info(f"Skipping known deal: {details['asin']}")
            continue
            
        msg_data = format_message(details)
        if not msg_data: continue # Discount too low
        
        caption, discount = msg_data
        aff_link = create_affiliate_link(details['asin'])
        
        success = send_telegram_message(caption, details['image_url'], aff_link)
        
        if success:
            database.record_posted_deal(details['asin'], details['title'], url)
            logging.info(f"✅ Posted: {details['title'][:30]}")
            deals_posted += 1
            time.sleep(random.uniform(5, 10))
        
        # Value Add Content logic
        if deals_posted > 0 and deals_posted % config.VALUE_ADD_CONTENT_FREQUENCY == 0:
            tip = random.choice(config.TIPS_AND_TRICKS)
            send_telegram_message(f"💡 <b>SHOPPING TIP:</b>\n\n{tip}\n\n#SemmaTips")

if __name__ == "__main__":
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        logging.error("Missing TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    run_bot()

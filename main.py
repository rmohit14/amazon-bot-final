# main.py
import os
import time
import random
import logging
import schedule
import requests
import re
from datetime import datetime, timedelta

import config
import scraper
import database

# ---------- Logging ----------
LOG_FILE = config.LOG_FILENAME
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

# ---------- Utilities ----------
def cleanup_old_logs(days=7):
    try:
        cutoff = datetime.now() - timedelta(days=days)
        if os.path.exists(LOG_FILE):
            mtime = datetime.fromtimestamp(os.path.getmtime(LOG_FILE))
            if mtime < cutoff:
                new_name = f"{LOG_FILE}.{mtime.strftime('%Y%m%d_%H%M%S')}.bak"
                os.rename(LOG_FILE, new_name)
                logging.info(f"Rotated old log to {new_name}")
                # Re-initialize logging to the original filename
                for handler in logging.getLogger().handlers[:]:
                    if isinstance(handler, logging.FileHandler) and handler.baseFilename == os.path.abspath(new_name):
                        logging.getLogger().removeHandler(handler)
                file_handler = logging.FileHandler(LOG_FILE)
                file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
                logging.getLogger().addHandler(file_handler)

    except Exception as e:
        logging.error(f"Error cleaning logs: {e}")

def create_affiliate_link(asin: str) -> str | None:
    if not asin:
        return None
    return f"https://www.amazon.in/dp/{asin}/?tag={config.AMAZON_ASSOCIATE_ID}"

def _send_telegram_request(api_url: str, data: dict, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            resp = requests.post(api_url, data=data, timeout=20)
            if resp.status_code == 200:
                return True
            # For specific error codes that shouldn't be retried
            elif resp.status_code in [400, 404]: 
                logging.error(f"Telegram API Error (will not retry): {resp.status_code} {resp.text}")
                return False
            else:
                logging.warning(f"Telegram API failed (attempt {attempt+1}/{retries}): {resp.status_code} {resp.text}")
        except requests.RequestException as e:
            logging.error(f"Telegram request error (attempt {attempt+1}/{retries}): {e}")
        
        if attempt < retries - 1:
            time.sleep(5) # Wait before retrying
            
    return False

def send_to_telegram_photo(chat_id: str, photo_url: str, caption_html: str) -> bool:
    api = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {"chat_id": chat_id, "photo": photo_url, "caption": caption_html, "parse_mode": "HTML"}
    return _send_telegram_request(api, data)

def send_to_telegram_message(chat_id: str, text: str) -> bool:
    api = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    return _send_telegram_request(api, data)

def _clean_price(price_str: str | None) -> float | None:
    if not price_str:
        return None
    try:
        cleaned = re.sub(r"[^\d.]", "", price_str)
        return float(cleaned)
    except (ValueError, TypeError):
        return None

# ---------- Processing ----------
def process_deals_cycle(category_name: str, categories: dict, seen_urls_in_run: set):
    logging.info(f"--- Starting cycle: {category_name} ({len(categories)} categories) ---")
    
    urls = scraper.find_deals(categories, seen_urls=seen_urls_in_run)
    if not urls:
        logging.info(f"No new product URLs found in {category_name} cycle.")
        return

    logging.info(f"Found {len(urls)} new product URLs in {category_name} cycle. Scraping details...")
    for url in urls:
        details = scraper.scrape_product_details(url)

        if not details:
            logging.warning(f"Skipping URL due to scraping failure: {url}")
            continue

        title = details.get("title")
        deal_price_str = details.get("deal_price")
        asin = details.get("asin")
        
        if not title:
            logging.info(f"Skipping (missing title): {url}")
            continue
        if not deal_price_str:
            logging.info(f"Skipping (missing deal price): {title} - {url}")
            continue
        if not asin:
            logging.info(f"Skipping (missing ASIN): {title} - {url}")
            continue

        if database.is_deal_already_posted(asin):
            logging.info(f"Already posted (from DB): {asin} - {title}")
            continue

        # ----------- 💬 ATTRACTIVE CAPTION -------------
        aff_link = create_affiliate_link(asin)
        title_escaped = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        original_price_str = details.get("original_price")

        deal_price_num = _clean_price(deal_price_str)
        original_price_num = _clean_price(original_price_str)

        discount_line = ""
        if deal_price_num and original_price_num and original_price_num > deal_price_num:
            discount_percent = round(((original_price_num - deal_price_num) / original_price_num) * 100)
            if discount_percent >= config.MINIMUM_DISCOUNT:
                 discount_line = f"💚 <b>{discount_percent}% OFF</b> ✅"

        caption = f"🛍️ <b>{title_escaped}</b>\n\n"

        if original_price_str and original_price_str != deal_price_str:
            caption += f"<s>MRP: {original_price_str}</s>\n"

        caption += f"💰 <b>Deal: {deal_price_str}</b>\n"
        if discount_line:
            caption += discount_line + "\n"

        caption += f"\n<a href='{aff_link}'>🛒 <b>Shop Now on Amazon</b></a>\n"
        caption += "⚡ Hurry! Limited time deal.\n\n"
        caption += "#Deals #Amazon #Offers #LootDeals #Discounts"

        # ----------------------------------------------------

        posted = False
        if details.get("image_url"):
            posted = send_to_telegram_photo(config.TELEGRAM_CHANNEL_ID, details["image_url"], caption)

        # Fallback to text message if photo fails
        if not posted:
            logging.warning(f"Failed to send with photo for {asin}, falling back to text message.")
            posted = send_to_telegram_message(config.TELEGRAM_CHANNEL_ID, caption)

        if posted:
            database.record_posted_deal(asin, title, url)
            logging.info(f"✅ Posted and recorded: {asin} - {title}")
        else:
            logging.error(f"❌ Failed to post to Telegram: {asin} - {title}")

        time.sleep(random.uniform(5, 10))

    logging.info(f"--- Finished cycle: {category_name} ---")


# ---------- Scheduling ----------
def run_high_traffic_cycle(seen_urls: set):
    process_deals_cycle("High-Traffic", config.HIGH_TRAFFIC_CATEGORIES, seen_urls)

def run_standard_cycle(seen_urls: set):
    process_deals_cycle("Standard", config.STANDARD_CATEGORIES, seen_urls)

def run_all_cycles():
    logging.info("================== Starting New Run ==================")
    # This set ensures a product found in high-traffic isn't re-scraped in standard during the same run
    seen_urls_in_this_run = set() 
    try:
        run_high_traffic_cycle(seen_urls_in_this_run)
        run_standard_cycle(seen_urls_in_this_run)
    except Exception as e:
        logging.critical(f"An unexpected error occurred during the scheduled run: {e}", exc_info=True)
    logging.info("================== Finished Run ==================\n")


def main():
    logging.info("Starting bot")
    database.initialize_database()
    cleanup_old_logs(days=7)

    # Combine schedules into a single job to run them sequentially
    # This avoids overlap and uses the `seen_urls_in_this_run` set effectively
    schedule.every(config.HIGH_TRAFFIC_INTERVAL_MIN).minutes.do(run_all_cycles)
    
    logging.info(f"Bot scheduled to run all cycles every {config.HIGH_TRAFFIC_INTERVAL_MIN} minutes.")
    
    # Run once immediately on start
    run_all_cycles()

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logging.critical(f"Scheduler failed: {e}", exc_info=True)
        time.sleep(1)

if __name__ == "__main__":
    main()
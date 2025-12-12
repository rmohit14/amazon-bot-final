import os
import time
import random
import logging
import schedule
import requests
import re
import json
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

# ---------- Global Counter for Value-Add Content ----------
deal_counter = 0

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
            elif resp.status_code in [400, 404]:
                logging.error(f"Telegram API Error (will not retry): {resp.status_code} {resp.text}")
                return False
            else:
                logging.warning(f"Telegram API failed (attempt {attempt+1}/{retries}): {resp.status_code} {resp.text}")
        except requests.RequestException as e:
            logging.error(f"Telegram request error (attempt {attempt+1}/{retries}): {e}")
        if attempt < retries - 1:
            time.sleep(5)
    return False

# NEW: Enhanced function with inline buttons
def send_to_telegram_photo(chat_id: str, photo_url: str, caption_html: str, inline_keyboard=None) -> bool:
    api = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption_html,
        "parse_mode": "HTML"
    }
    
    if inline_keyboard:
        data["reply_markup"] = json.dumps({"inline_keyboard": inline_keyboard})
    
    return _send_telegram_request(api, data)

def send_to_telegram_message(chat_id: str, text: str, inline_keyboard=None) -> bool:
    api = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    if inline_keyboard:
        data["reply_markup"] = json.dumps({"inline_keyboard": inline_keyboard})
    
    return _send_telegram_request(api, data)

def _clean_price(price_str: str | None) -> float | None:
    if not price_str:
        return None
    try:
        cleaned = re.sub(r"[^\d.]", "", price_str)
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def get_category_emoji(category_name: str) -> str:
    """Get emoji for category, default to 🔥 if not found"""
    for key in config.CATEGORY_EMOJIS:
        if key.lower() in category_name.lower():
            return config.CATEGORY_EMOJIS[key]
    return "🔥"

# NEW: Create enhanced caption with emojis and formatting
def create_enhanced_caption(title: str, deal_price_str: str, original_price_str: str, 
                           discount_percent: int, aff_link: str, category: str = "") -> str:
    """Create visually appealing, scannable caption with emojis"""
    
    title_escaped = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Limit title length for better readability
    if len(title_escaped) > 80:
        title_escaped = title_escaped[:77] + "..."
    
    # Get category emoji
    cat_emoji = get_category_emoji(category) if category else "🔥"
    
    # Build caption with clear structure
    caption = f"{cat_emoji} <b>{title_escaped}</b>\n\n"
    
    # Discount badge with fire emojis for high discounts
    if discount_percent >= 80:
        discount_line = f"🔥🔥🔥 <b>{discount_percent}% OFF</b> 🔥🔥🔥"
    elif discount_percent >= 75:
        discount_line = f"🔥🔥 <b>{discount_percent}% OFF</b> 🔥🔥"
    else:
        discount_line = f"🔥 <b>{discount_percent}% OFF</b>"
    
    caption += f"{discount_line}\n\n"
    
    # Price comparison
    if original_price_str and original_price_str != deal_price_str:
        caption += f"<s>MRP: {original_price_str}</s>\n"
    
    caption += f"💰 <b>Deal Price: {deal_price_str}</b>\n\n"
    
    # Urgency indicators
    caption += "⏰ <b>Limited Time Deal!</b>\n"
    caption += "⚡ <b>Stock Running Out Fast!</b>\n\n"
    
    # Call to action
    caption += "👉 Don't miss this amazing offer!\n\n"
    
    # Hashtags for discoverability
    caption += f"#Deals #Amazon #Offers #{discount_percent}PercentOff #LootDeals #Discounts"
    
    return caption

# NEW: Function to send value-add content
def send_value_add_content():
    """Send educational tips and shopping hacks"""
    global deal_counter
    
    tip = random.choice(config.TIPS_AND_TRICKS)
    
    message = f"━━━━━━━━━━━━━━━\n"
    message += f"🎓 <b>SHOPPING TIP OF THE DAY</b>\n"
    message += f"━━━━━━━━━━━━━━━\n\n"
    message += tip + "\n\n"
    message += "💡 <i>Stay smart, save more!</i>\n"
    message += f"━━━━━━━━━━━━━━━\n\n"
    message += "#ShoppingTips #SaveMoney #SmartShopping"
    
    try:
        send_to_telegram_message(config.TELEGRAM_CHANNEL_ID, message)
        logging.info("✅ Posted value-add content")
    except Exception as e:
        logging.error(f"Failed to post value-add content: {e}")

# ---------- Processing ----------
def process_deals_cycle(category_name: str, categories: dict, seen_urls_in_run: set):
    global deal_counter
    
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
        original_price_str = details.get("original_price")
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

        # Calculate discount
        deal_price_num = _clean_price(deal_price_str)
        original_price_num = _clean_price(original_price_str)
        discount_percent = 0

        if deal_price_num and original_price_num and original_price_num > deal_price_num:
            discount_percent = round(((original_price_num - deal_price_num) / original_price_num) * 100)

        if discount_percent < config.MINIMUM_DISCOUNT:
            logging.info(f"Skipping (Real discount {discount_percent}% < {config.MINIMUM_DISCOUNT}%): {title} - {url}")
            continue

        # Create affiliate link
        aff_link = create_affiliate_link(asin)
        
        # NEW: Create enhanced caption
        caption = create_enhanced_caption(
            title, deal_price_str, original_price_str, 
            discount_percent, aff_link, category_name
        )
        
        # NEW: Create inline button
        inline_keyboard = [[
            {"text": "🛒 Buy Now on Amazon", "url": aff_link}
        ]]

        # Send to Telegram
        posted = False
        if details.get("image_url"):
            posted = send_to_telegram_photo(
                config.TELEGRAM_CHANNEL_ID, 
                details["image_url"], 
                caption,
                inline_keyboard
            )

        # Fallback to text message if photo fails
        if not posted:
            logging.warning(f"Failed to send with photo for {asin}, falling back to text message.")
            posted = send_to_telegram_message(config.TELEGRAM_CHANNEL_ID, caption, inline_keyboard)

        if posted:
            database.record_posted_deal(asin, title, url)
            logging.info(f"✅ Posted and recorded: {asin} - {title}")
            
            deal_counter += 1
            
            # NEW: Send value-add content periodically
            if deal_counter % config.VALUE_ADD_CONTENT_FREQUENCY == 0:
                time.sleep(random.uniform(3, 5))  # Small delay before tip
                send_value_add_content()
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
    seen_urls_in_this_run = set()
    try:
        run_high_traffic_cycle(seen_urls_in_this_run)
        run_standard_cycle(seen_urls_in_this_run)
    except Exception as e:
        logging.critical(f"An unexpected error occurred during the scheduled run: {e}", exc_info=True)
    logging.info("================== Finished Run ==================\n")

# NEW: Scheduled functions for specific times
def morning_post():
    logging.info("📅 Morning scheduled post starting...")
    run_all_cycles()

def afternoon_post():
    logging.info("📅 Afternoon scheduled post starting...")
    run_all_cycles()

def evening_post():
    logging.info("📅 Evening scheduled post starting...")
    run_all_cycles()

def main():
    logging.info("Starting bot with enhanced formatting and scheduling")
    database.initialize_database()
    cleanup_old_logs(days=7)

    # NEW: Schedule posts at specific times
    morning_time = f"{config.POSTING_SCHEDULE['morning']['hour']:02d}:{config.POSTING_SCHEDULE['morning']['minute']:02d}"
    afternoon_time = f"{config.POSTING_SCHEDULE['afternoon']['hour']:02d}:{config.POSTING_SCHEDULE['afternoon']['minute']:02d}"
    evening_time = f"{config.POSTING_SCHEDULE['evening']['hour']:02d}:{config.POSTING_SCHEDULE['evening']['minute']:02d}"
    
    schedule.every().day.at(morning_time).do(morning_post)
    schedule.every().day.at(afternoon_time).do(afternoon_post)
    schedule.every().day.at(evening_time).do(evening_post)
    
    logging.info(f"✅ Bot scheduled to post at: {morning_time}, {afternoon_time}, {evening_time}")

    # Run once immediately on start
    run_all_cycles()

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logging.critical(f"Scheduler failed: {e}", exc_info=True)
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()

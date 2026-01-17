import random
import time
import re
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import config

BASE_URL = "https://www.amazon.in"

def create_session():
    session = requests.Session()
    # Increased backoff factor to be gentler on Amazon
    retry_strategy = Retry(
        total=config.MAX_REQUEST_RETRIES,
        backoff_factor=2, 
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    return session

SESSION = create_session()

def fetch_page(url: str) -> str | None:
    # Rotate User-Agent per request
    headers = {
        "User-Agent": random.choice(config.USER_AGENTS),
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/"
    }
    try:
        r = SESSION.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        r.raise_for_status()
        
        # Check for Amazon's soft block (200 OK but captcha)
        if "enter the characters you see below" in r.text.lower():
            logging.warning(f"Captcha detected for {url}")
            return None
            
        return r.text
    except requests.RequestException as e:
        logging.error(f"Fetch failed {url}: {e}")
        return None

def find_deals(categories: dict, seen_urls: set) -> List[str]:
    results = []
    for cat_name, node_id in categories.items():
        # Added pct-off range to URL
        search_url = f"{BASE_URL}/s?rh=n%3A{node_id}&pct-off={config.MINIMUM_DISCOUNT}-100"
        logging.info(f"🔎 Scanning: {cat_name}")
        
        html = fetch_page(search_url)
        if not html:
            time.sleep(random.uniform(2, 5))
            continue

        soup = BeautifulSoup(html, "lxml")
        # Updated selectors for 2024/2025 layouts
        anchors = soup.select('a.a-link-normal.s-no-outline') or soup.select('a.a-link-normal.s-underline-text.s-underline-link-text.s-link-style.a-text-normal')
        
        count = 0
        for a in anchors:
            href = a.get("href")
            if not href or "/sspa/" in href: # Skip sponsored ads (sspa)
                continue
            
            url = f"{BASE_URL}{href}" if href.startswith("/") else href
            url = url.split("?")[0] # Clean URL
            
            if url in seen_urls: continue
            
            seen_urls.add(url)
            results.append(url)
            count += 1
            if count >= config.LIMIT_PER_CATEGORY: break
            
        time.sleep(random.uniform(2, 4))
    return results

def scrape_product_details(product_url: str) -> Dict[str, Any] | None:
    html = fetch_page(product_url)
    if not html: return None
    
    soup = BeautifulSoup(html, "lxml")
    
    # 1. Get Title
    title_el = soup.select_one("#productTitle")
    if not title_el: return None
    title = title_el.get_text(strip=True)
    
    # 2. Get Deal Price (Prioritize specific deal block)
    deal_price = None
    price_selectors = [
        ".apexPriceToPay .a-offscreen", # New layout
        "#corePriceDisplay_desktop_feature_div .a-price-whole", 
        ".a-price.a-text-price.a-size-medium .a-offscreen",
        "#priceblock_dealprice",
        ".a-price[data-a-size='xl'] .a-offscreen"
    ]
    
    for sel in price_selectors:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            # Remove currency symbol and commas
            clean_price = re.sub(r"[^\d.]", "", txt)
            if clean_price:
                deal_price = clean_price
                break
    
    # 3. Get MRP
    mrp = None
    mrp_selectors = [
        "span[data-a-strike='true'] span.a-offscreen",
        "#corePriceDisplay_desktop_feature_div .a-text-price span.a-offscreen"
    ]
    for sel in mrp_selectors:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            mrp = re.sub(r"[^\d.]", "", txt)
            break

    # 4. Get ASIN
    asin = None
    # Try URL first (fastest)
    m = re.search(r"/dp/([A-Z0-9]{10})", product_url)
    if m: asin = m.group(1)
    
    # 5. Get Image
    img_url = None
    img_el = soup.select_one("#landingImage")
    if img_el:
        img_url = img_el.get("src")
        # Try to get hi-res from data-old-hires if available
        if img_el.has_attr("data-old-hires") and img_el["data-old-hires"]:
            img_url = img_el["data-old-hires"]

    return {
        "title": title,
        "deal_price": deal_price,
        "original_price": mrp,
        "image_url": img_url,
        "asin": asin,
        "product_url": product_url
    }

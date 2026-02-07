import random
import time
import re
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from fake_useragent import UserAgent
import config

BASE_URL = "https://www.amazon.in"

# Initialize UserAgent rotator
ua = UserAgent()

def get_random_headers():
    """Generates realistic browser headers to bypass Amazon bot detection."""
    random_ua = ua.random
    return {
        "User-Agent": random_ua,
        "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "dnt": "1",
    }

def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=config.MAX_REQUEST_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# Initialize one session object
SESSION = create_session()

def fetch_page(url: str) -> str | None:
    """Fetches a page with robust error handling and header rotation."""
    
    # Try up to 3 times manually to handle 503s specifically
    for attempt in range(3):
        try:
            # Rotate headers for EVERY request
            headers = get_random_headers()
            
            # Random sleep to mimic human behavior
            time.sleep(random.uniform(1, 3))
            
            response = SESSION.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
            
            # Handle 503 (Service Unavailable) explicitly
            if response.status_code == 503:
                logging.warning(f"⚠️ 503 Detected. Sleeping... (Attempt {attempt+1}/3)")
                time.sleep(random.uniform(5, 10))
                continue # Try again with new headers
                
            response.raise_for_status()
            
            # Check for Captcha
            if "enter the characters you see below" in response.text.lower() or "api-services-support@amazon.com" in response.text:
                logging.warning(f"🤖 Captcha/Bot Block detected for {url}")
                return None
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Fetch failed {url}: {e}")
            return None
            
    return None

def find_deals(categories: dict, seen_urls: set) -> List[str]:
    results = []
    for cat_name, node_id in categories.items():
        # Clean search URL
        search_url = f"{BASE_URL}/s?rh=n%3A{node_id}&pct-off={config.MINIMUM_DISCOUNT}-100"
        logging.info(f"🔎 Scanning: {cat_name}")
        
        html = fetch_page(search_url)
        if not html:
            logging.warning(f"❌ Could not load category: {cat_name}")
            continue

        soup = BeautifulSoup(html, "lxml")
        
        # Selectors for search results
        anchors = soup.select('div[data-component-type="s-search-result"] h2 a')
        
        if not anchors:
            # Fallback for different layouts
            anchors = soup.select('a.a-link-normal.s-no-outline')

        count = 0
        for a in anchors:
            href = a.get("href")
            if not href or "/sspa/" in href or "/gp/video/" in href: # Skip ads and video
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
    if not title_el: 
        # Debugging: Save HTML if title missing to verify layout
        return None
        
    title = title_el.get_text(strip=True)
    
    # 2. Get Deal Price
    deal_price = None
    price_selectors = [
        ".apexPriceToPay .a-offscreen",
        "#corePriceDisplay_desktop_feature_div .a-price-whole", 
        ".a-price.a-text-price.a-size-medium .a-offscreen",
        "#priceblock_dealprice",
        ".a-price[data-a-size='xl'] .a-offscreen"
    ]
    
    for sel in price_selectors:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            clean_price = re.sub(r"[^\d.]", "", txt)
            if clean_price:
                deal_price = clean_price
                break
    
    # 3. Get MRP
    mrp = None
    mrp_selectors = [
        "span[data-a-strike='true'] span.a-offscreen",
        "#corePriceDisplay_desktop_feature_div .a-text-price span.a-offscreen",
        ".a-text-price span.a-offscreen"
    ]
    for sel in mrp_selectors:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            mrp = re.sub(r"[^\d.]", "", txt)
            break

    # 4. Get ASIN
    asin = None
    m = re.search(r"/dp/([A-Z0-9]{10})", product_url)
    if m: asin = m.group(1)
    
    # 5. Get Image
    img_url = None
    img_el = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
    if img_el:
        # Try dynamic JS data first
        if img_el.has_attr("data-old-hires") and img_el["data-old-hires"]:
            img_url = img_el["data-old-hires"]
        elif img_el.has_attr("data-a-dynamic-image"):
            # Extract first image from JSON object in attribute
            try:
                data = img_el["data-a-dynamic-image"]
                # Rough extract of first URL
                urls = re.findall(r'https?://[^"]+', data)
                if urls: img_url = urls[0]
            except:
                pass
        
        if not img_url:
            img_url = img_el.get("src")

    return {
        "title": title,
        "deal_price": deal_price,
        "original_price": mrp,
        "image_url": img_url,
        "asin": asin,
        "product_url": product_url
    }

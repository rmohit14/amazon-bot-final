# scraper.py
import random
import time
import re
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    USER_AGENTS,
    REQUEST_TIMEOUT,
    MAX_REQUEST_RETRIES,
    MINIMUM_DISCOUNT,
    LIMIT_PER_CATEGORY
)

BASE_URL = "https://www.amazon.in"

def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_REQUEST_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

SESSION = create_session()

HEADERS_TEMPLATE = {
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

def fetch_page(url: str) -> str | None:
    headers = HEADERS_TEMPLATE.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    try:
        r = SESSION.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def _text(el):
    return el.get_text(strip=True) if el else None

def _clean_text(s: str | None) -> str | None:
    if not s:
        return None
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()

def _price_to_number(price: str | None) -> float | None:
    if not price:
        return None
    try:
        num = re.sub(r"[^\d.]", "", price)
        return float(num)
    except (ValueError, TypeError):
        return None

def _first_regex_price(html: str) -> str | None:
    matches = re.findall(r"₹\s*[0-9]{1,3}(?:[0-9,]*)(?:\.\d+)?", html)
    if matches:
        return _clean_text(matches[0])
    return None

def find_deals(categories: dict, seen_urls: set, limit_per_category: int = LIMIT_PER_CATEGORY) -> List[str]:
    results = []
    
    for cat_name, node_id in categories.items():
        search_url = f"{BASE_URL}/s?rh=n%3A{node_id}&pct-off={MINIMUM_DISCOUNT}-100"
        logging.info(f"Searching for deals in category: {cat_name}")
        html = fetch_page(search_url)
        
        if not html:
            logging.warning(f"Could not fetch deals for category '{cat_name}'. It might be due to a network error or block. Skipping.")
            time.sleep(random.uniform(2, 5))
            continue

        soup = BeautifulSoup(html, "lxml")
        anchors = soup.select('a.a-link-normal.s-no-outline')
        count = 0
        for a in anchors:
            href = a.get("href")
            if not href:
                continue
            if any(keyword in href for keyword in ["/gp/slredirect/", "/gallery/", "/live/", "/stores/"]):
                continue

            url = href if href.startswith("http") else BASE_URL + href
            url = url.split("?")[0].split("#")[0]

            if not ("/dp/" in url or "/gp/product/" in url):
                continue
            if url in seen_urls:
                continue

            seen_urls.add(url)
            results.append(url)
            count += 1
            if count >= limit_per_category:
                break

        time.sleep(random.uniform(3, 7))
    return results

def scrape_product_details(product_url: str) -> Dict[str, Any] | None:
    html = fetch_page(product_url)
    if not html:
        return None

    lower_html = html.lower()
    for ph in ["unusual traffic", "enter the characters you see below", "to discuss automated access"]:
        if ph in lower_html:
            logging.warning(f"Bot-check page detected for {product_url}. Skipping.")
            return None

    soup = BeautifulSoup(html, "lxml")
    try:
        # --- Book format skip ---
        format_element = soup.select_one("#tmmSwatches .a-button-selected .a-button-text")
        if format_element:
            format_text = _text(format_element)
            if format_text and "paperback" not in format_text.lower():
                logging.info(f"Skipping non-paperback book format: '{format_text}' - {product_url}")
                return None

        # --- Title ---
        title = None
        for sel in ["#productTitle", "span#productTitle", "h1 span#title"]:
            el = soup.select_one(sel)
            if el and _text(el):
                title = _clean_text(_text(el))
                break
        if not title:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.has_attr("content"):
                title = _clean_text(og_title["content"])

        # --- Deal price ---
        deal_price = None
        # **FIXED**: Removed the selector that was incorrectly matching the MRP.
        # The list is now more specific to the actual selling price.
        for sel in [
            "#corePrice_feature_div span.a-offscreen",
            "#priceblock_dealprice",
            "#priceblock_ourprice",
            "#priceblock_saleprice",
            "div#tp_price_block_total_price .a-offscreen",
            ".a-price[data-a-size='xl'] .a-offscreen"
        ]:
            el = soup.select_one(sel)
            if el and _text(el):
                cand = _clean_text(_text(el))
                if cand:
                    deal_price = cand
                    break
        
        # --- Original price (MRP) ---
        original_price = None
        for sel in [
            "span[data-a-strike='true'] span.a-offscreen", # Most reliable selector for MRP
            ".a-price.a-text-price .a-offscreen", # This selector correctly finds MRP here
            "#corePrice_feature_div span.a-text-price span.a-offscreen",
            "#price span.a-text-price span.a-offscreen",
            ".priceBlockStrikePriceString"
        ]:
            el = soup.select_one(sel)
            if el and _text(el):
                cand = _clean_text(_text(el))
                # Reject unit prices (contain '/' or 'per') and ensure it's not the same as deal price
                if not re.search(r"/|per", cand.lower()):
                    if cand and cand != deal_price:
                        original_price = cand
                        break

        # --- Fallback checks ---
        if not deal_price:
            cand = _first_regex_price(html)
            if cand:
                deal_price = cand

        # If original < deal, discard it (likely a unit price error)
        if deal_price and original_price:
            dpn = _price_to_number(deal_price)
            opn = _price_to_number(original_price)
            if opn and dpn and opn < dpn:
                logging.info(f"Discarding invalid original_price '{original_price}' which is less than deal_price '{deal_price}' for {product_url}")
                original_price = None

        # --- Image ---
        image_url = None
        for sel in ["#landingImage", "#imgTagWrapperId img", "#main-image-container img"]:
            el = soup.select_one(sel)
            if el:
                # Prioritize high-res images
                src = el.get("data-old-hires") or el.get("src") or el.get("data-a-dynamic-image")
                if src and not src.startswith("data:image"):
                    # data-a-dynamic-image can be a JSON string, extract first URL
                    if src.startswith("{"): 
                        match = re.search(r'https://[^\s"]+', src)
                        if match:
                           image_url = match.group(0)
                    else:
                        image_url = src
                    break
        # Fallback to OG image meta tag
        if not image_url:
            og = soup.select_one("meta[property='og:image']")
            if og and og.has_attr("content"):
                image_url = og["content"]

        # --- ASIN ---
        asin = None
        asin_input = soup.select_one("input#ASIN")
        if asin_input and asin_input.has_attr("value"):
            asin = asin_input["value"]
        else:
            m = re.search(r"/dp/([A-Z0-9]{10})", product_url) or re.search(r"/gp/product/([A-Z0-9]{10})", product_url)
            if m:
                asin = m.group(1)

        return {
            "title": title,
            "deal_price": deal_price,
            "original_price": original_price,
            "image_url": image_url,
            "asin": asin,
            "product_url": product_url
        }
    except Exception as e:
        logging.error(f"Error scraping {product_url}: {e}", exc_info=True)
        return None
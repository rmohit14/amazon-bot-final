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

HEADERS_TEMPLATE = {
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def fetch_page(url: str) -> str | None:
    headers = HEADERS_TEMPLATE.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)
    try:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def _extract_discount_percent(text: str | None) -> int | None:
    if not text:
        return None
    candidates = []
    patterns = [
        r"-\s*(\d{1,3})\s*%",
        r"(\d{1,3})\s*%\s*off",
        r"save\s*(\d{1,3})\s*%",
        r"\((\d{1,3})\s*%\)"
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            try:
                val = int(m.group(1))
            except Exception:
                continue
            if 0 <= val <= 100:
                candidates.append(val)
    return max(candidates) if candidates else None

def find_deals(categories: dict, seen_urls: set, limit_per_category: int = LIMIT_PER_CATEGORY) -> List[str]:
    results = []
    for cat_name, node_id in categories.items():
        search_url = f"{BASE_URL}/s?rh=n%3A{node_id}&pct-off={MINIMUM_DISCOUNT}-"
        logging.info(f"Searching for deals in category: {cat_name}")
        html = fetch_page(search_url)
        
        if not html:
            logging.warning(f"Could not fetch deals for category '{cat_name}'. Skipping.")
            time.sleep(random.uniform(2, 5))
            continue

        soup = BeautifulSoup(html, "lxml")
        items = soup.select("div.s-result-item[data-asin]")
        count = 0
        for item in items:
            asin = item.get("data-asin")
            if not asin:
                continue
            # Skip sponsored results
            if "sp-sponsored" in item.get("data-component-type", "").lower():
                continue

            item_text = item.get_text(" ", strip=True)
            discount = _extract_discount_percent(item_text)
            if discount is None or discount < MINIMUM_DISCOUNT:
                continue
            
            url = f"{BASE_URL}/dp/{asin}"
            if url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(url)
            count += 1
            if count >= limit_per_category:
                break
        time.sleep(random.uniform(3, 7))
    return results

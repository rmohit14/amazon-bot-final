from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)


# -----------------------------
# HTTP
# -----------------------------

_SESSION: requests.Session | None = None


def _make_session() -> requests.Session:
    session = requests.Session()

    retry_strategy = Retry(
        total=config.MAX_REQUEST_RETRIES,
        connect=config.MAX_REQUEST_RETRIES,
        read=config.MAX_REQUEST_RETRIES,
        status=config.MAX_REQUEST_RETRIES,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = _make_session()
    return _SESSION


def _random_headers() -> dict[str, str]:
    # Keep headers simple + stable; aggressive header spoofing often increases blocks.
    return {
        "User-Agent": random.choice(config.USER_AGENTS),
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": config.BASE_URL,
    }


_CAPTCHA_MARKERS = (
    "enter the characters you see below",
    "api-services-support@amazon.com",
    "/errors/validatecaptcha",
)


def _is_captcha_page(html: str) -> bool:
    hay = (html or "").lower()
    return any(m in hay for m in _CAPTCHA_MARKERS)


def fetch_html(url: str) -> tuple[str | None, str | None]:
    """Fetch a URL and return (html, error_reason).

    error_reason is one of: "captcha", "http", "network", or None.
    """
    session = get_session()

    # Manual loop so we can:
    # 1) jitter sleep politely
    # 2) detect CAPTCHA pages and stop early
    for attempt in range(1, config.MAX_REQUEST_RETRIES + 1):
        time.sleep(random.uniform(config.MIN_SLEEP_SECONDS, config.MAX_SLEEP_SECONDS))

        try:
            resp = session.get(
                url,
                headers=_random_headers(),
                timeout=(5, config.REQUEST_TIMEOUT_SECONDS),
                allow_redirects=True,
            )
        except requests.RequestException as e:
            # IMPORTANT FIX: don't return immediately (your old code did). Keep retrying.
            wait = min(30.0, (2 ** (attempt - 1)) + random.uniform(0.2, 1.2))
            logger.warning(
                "Network error (attempt %s/%s) for %s: %s | sleeping %.1fs",
                attempt,
                config.MAX_REQUEST_RETRIES,
                url,
                e,
                wait,
            )
            time.sleep(wait)
            continue

        html = resp.text or ""

        if _is_captcha_page(html):
            logger.warning("Captcha/bot wall detected (status=%s) for %s", resp.status_code, url)
            return None, "captcha"

        if resp.status_code >= 400:
            # Adapter retries already happened; we still add a small backoff here.
            wait = min(45.0, (2 ** (attempt - 1)) + random.uniform(0.5, 2.0))
            logger.warning(
                "HTTP %s (attempt %s/%s) for %s | sleeping %.1fs",
                resp.status_code,
                attempt,
                config.MAX_REQUEST_RETRIES,
                url,
                wait,
            )
            time.sleep(wait)
            continue

        return html, None

    return None, "network"


# -----------------------------
# Parsing helpers
# -----------------------------

_PRICE_RE = re.compile(r"(\d[\d,]*\.?\d*)")


def parse_inr_price(text: str | None) -> float | None:
    if not text:
        return None

    # Handle ranges like "₹999 - ₹1,499" by taking the first number.
    m = _PRICE_RE.search(text)
    if not m:
        return None

    raw = m.group(1).replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def compute_discount(original_price: float | None, deal_price: float | None) -> int | None:
    if not original_price or not deal_price:
        return None
    if original_price <= 0 or deal_price <= 0:
        return None
    if deal_price >= original_price:
        return None
    return int(round(((original_price - deal_price) / original_price) * 100))


def extract_asin_from_url(url: str) -> str | None:
    m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
    return m.group(1) if m else None


def canonical_product_url(asin: str) -> str:
    return f"{config.BASE_URL}/dp/{asin}"


def build_category_search_url(node_id: str, page: int) -> str:
    params = {
        "rh": f"n:{node_id}",
        "s": config.AMAZON_SORT,
        "page": str(page),
    }
    return f"{config.BASE_URL}/s?{urlencode(params)}"


def _is_sponsored(result_div: Any) -> bool:
    # Amazon keeps changing sponsored markup; combine a couple heuristics.
    if result_div.select_one("span.s-sponsored-label-text, span.puis-sponsored-label-text"):
        return True
    if result_div.select_one("a[href*='sspa'], a[href*='/sspa/']"):
        return True
    if result_div.find(string=re.compile(r"\bSponsored\b", re.IGNORECASE)):
        return True
    return False


def _extract_search_title(result_div: Any) -> str | None:
    link = result_div.select_one("h2 a.a-link-normal") or result_div.select_one("a.a-link-normal.s-no-outline")
    if not link:
        return None
    title = link.get_text(" ", strip=True)
    return title or None


def _extract_search_image(result_div: Any) -> str | None:
    img = result_div.select_one("img.s-image")
    if not img:
        return None
    return (img.get("src") or img.get("data-src") or "").strip() or None


def _extract_search_prices(result_div: Any) -> tuple[float | None, float | None]:
    """Return (deal_price, original_price) from a search-result card."""
    deal_price: float | None = None
    original_price: float | None = None

    for offscreen in result_div.select("span.a-price span.a-offscreen"):
        parent_price = offscreen.find_parent("span", class_="a-price")
        parent_classes = parent_price.get("class", []) if parent_price else []
        txt = offscreen.get_text(strip=True)
        if not txt:
            continue
        if "a-text-price" in parent_classes:
            continue
        if "₹" not in txt and "Rs" not in txt:
            continue
        deal_price = parse_inr_price(txt)
        if deal_price is not None:
            break

    for offscreen in result_div.select("span.a-price.a-text-price span.a-offscreen, span.a-text-price span.a-offscreen"):
        txt = offscreen.get_text(strip=True)
        if not txt:
            continue
        if "₹" not in txt and "Rs" not in txt:
            continue
        original_price = parse_inr_price(txt)
        if original_price is not None:
            break

    return deal_price, original_price


def parse_search_page(html: str, category: str) -> list[dict[str, Any]]:
    """Parse Amazon search results page into lightweight deal dicts."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, Any]] = []

    for div in soup.select("div[data-component-type='s-search-result']"):
        asin = (div.get("data-asin") or "").strip()
        if not asin or len(asin) != 10:
            continue
        if _is_sponsored(div):
            continue

        title = _extract_search_title(div)
        if not title:
            continue

        image_url = _extract_search_image(div)
        deal_price, original_price = _extract_search_prices(div)
        discount = compute_discount(original_price, deal_price)

        is_limited_time = bool(div.find(string=re.compile(r"limited time deal", re.IGNORECASE)))

        results.append(
            {
                "asin": asin,
                "title": title,
                "product_url": canonical_product_url(asin),
                "image_url": image_url,
                "deal_price": deal_price,
                "original_price": original_price,
                "discount": discount,
                "category": category,
                "limited_time": is_limited_time,
            }
        )

    return results


# -----------------------------
# Product-page fallback (only for missing data)
# -----------------------------

def scrape_product_page(product_url: str) -> dict[str, Any] | None:
    html, err = fetch_html(product_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    asin = extract_asin_from_url(product_url)

    title_el = soup.select_one("#productTitle") or soup.select_one("h1#title")
    title = title_el.get_text(" ", strip=True) if title_el else None
    if not title:
        meta_title = soup.select_one("meta[name='title']")
        if meta_title and meta_title.get("content"):
            title = meta_title.get("content").strip()

    deal_price = None
    price_selectors = [
        "#corePriceDisplay_desktop_feature_div span.a-price span.a-offscreen",
        "#corePrice_feature_div span.a-price span.a-offscreen",
        ".apexPriceToPay span.a-offscreen",
        "#priceblock_dealprice",
        "#priceblock_ourprice",
        "#priceblock_saleprice",
    ]
    for sel in price_selectors:
        el = soup.select_one(sel)
        if el:
            deal_price = parse_inr_price(el.get_text(strip=True))
            if deal_price is not None:
                break

    original_price = None
    mrp_selectors = [
        "#corePriceDisplay_desktop_feature_div span.a-price.a-text-price span.a-offscreen",
        "#corePriceDisplay_desktop_feature_div span[data-a-strike='true'] span.a-offscreen",
        "span[data-a-strike='true'] span.a-offscreen",
        "span.a-text-price span.a-offscreen",
    ]
    for sel in mrp_selectors:
        el = soup.select_one(sel)
        if el:
            original_price = parse_inr_price(el.get_text(strip=True))
            if original_price is not None:
                break

    image_url = None
    img_el = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
    if img_el:
        image_url = (img_el.get("data-old-hires") or "").strip() or None
        if not image_url:
            dyn = img_el.get("data-a-dynamic-image")
            if dyn:
                try:
                    data = json.loads(dyn)
                    if isinstance(data, dict) and data:
                        image_url = next(iter(data.keys()))
                except Exception:
                    pass
        if not image_url:
            image_url = (img_el.get("src") or "").strip() or None

    discount = compute_discount(original_price, deal_price)

    if not asin or not title:
        return None

    return {
        "asin": asin,
        "title": title,
        "product_url": canonical_product_url(asin),
        "image_url": image_url,
        "deal_price": deal_price,
        "original_price": original_price,
        "discount": discount,
    }


def enrich_missing_fields(deals: list[dict[str, Any]], max_lookups: int = 10) -> None:
    """Fill missing prices/title/image by hitting product pages for a few items."""
    lookups = 0
    for deal in deals:
        if lookups >= max_lookups:
            return

        if deal.get("discount") is not None and deal.get("deal_price") and deal.get("original_price"):
            continue

        details = scrape_product_page(deal["product_url"])
        if not details:
            continue

        for k in ("title", "image_url", "deal_price", "original_price", "discount"):
            if deal.get(k) in (None, "") and details.get(k) not in (None, ""):
                deal[k] = details[k]

        lookups += 1


# -----------------------------
# Public API used by run_once.py
# -----------------------------

def discover_deals() -> tuple[list[dict[str, Any]], bool]:
    """Discover deal candidates across configured categories.

    Returns (deals, captcha_hit).
    """
    seen_asins: set[str] = set()
    all_deals: list[dict[str, Any]] = []

    def _scan_category(cat_name: str, node_id: str, pages: int) -> None:
        kept_for_cat = 0
        for page in range(1, pages + 1):
            url = build_category_search_url(node_id=node_id, page=page)
            html, err = fetch_html(url)
            if not html:
                if err == "captcha" and config.STOP_ON_CAPTCHA:
                    raise RuntimeError("CAPTCHA")
                continue

            items = parse_search_page(html, category=cat_name)
            if not items:
                continue

            for item in items:
                asin = item["asin"]
                if asin in seen_asins:
                    continue
                seen_asins.add(asin)
                all_deals.append(item)
                kept_for_cat += 1
                if kept_for_cat >= config.MAX_CANDIDATES_PER_CATEGORY:
                    return

    try:
        for cat, node in config.HIGH_TRAFFIC_CATEGORIES.items():
            logger.info("Scanning category=%s pages=%s", cat, config.PAGES_PER_HIGH_TRAFFIC_CATEGORY)
            _scan_category(cat, node, config.PAGES_PER_HIGH_TRAFFIC_CATEGORY)

        for cat, node in config.STANDARD_CATEGORIES.items():
            logger.info("Scanning category=%s pages=%s", cat, config.PAGES_PER_STANDARD_CATEGORY)
            _scan_category(cat, node, config.PAGES_PER_STANDARD_CATEGORY)
    except RuntimeError as e:
        if str(e) == "CAPTCHA":
            return all_deals, True
        raise

    enrich_missing_fields(all_deals, max_lookups=10)
    return all_deals, False

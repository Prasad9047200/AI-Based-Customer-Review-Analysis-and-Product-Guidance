"""
scraper.py — Live product & review fetcher
Supports:
  • Amazon India  (amazon.in)
  • Flipkart      (flipkart.com)

Uses only requests + BeautifulSoup (no Selenium, no paid API).
Rotates User-Agent headers to reduce blocking.
Returns data in the same schema as reviews_dataset.csv so the
rest of the app works identically for live and cached data.
"""

import re
import time
import random
from datetime import datetime
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

# ── HTTP helpers ──────────────────────────────────────────────────────────────

_HEADERS_LIST = [
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
            "Gecko/20100101 Firefox/125.0"
        ),
        "Accept-Language": "en-US,en;q=0.5",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.4 Safari/605.1.15"
        ),
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    },
]

_SESSION = requests.Session()


def _get(url: str, timeout: int = 12) -> BeautifulSoup | None:
    """GET a URL, return BeautifulSoup or None on failure."""
    headers = random.choice(_HEADERS_LIST)
    try:
        resp = _SESSION.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
        return None
    except Exception:
        return None


def _sleep():
    time.sleep(random.uniform(0.8, 1.8))


# ─────────────────────────────────────────────────────────────────────────────
# AMAZON INDIA
# ─────────────────────────────────────────────────────────────────────────────

AMAZON_BASE = "https://www.amazon.in"


def amazon_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search Amazon India for products.
    Returns list of dicts: {product_id, product_name, category, url, image, price}
    """
    url = f"{AMAZON_BASE}/s?k={quote_plus(query)}&i=aps"
    soup = _get(url)
    if soup is None:
        return []

    products = []
    cards = soup.select('div[data-component-type="s-search-result"]')

    for card in cards[:max_results]:
        try:
            asin = card.get("data-asin", "")
            if not asin:
                continue

            # Name
            name_el = card.select_one("h2 a span")
            name = name_el.get_text(strip=True) if name_el else "Unknown"

            # Price
            price_el = card.select_one("span.a-price span.a-offscreen")
            price = price_el.get_text(strip=True) if price_el else "N/A"

            # Image
            img_el = card.select_one("img.s-image")
            image = img_el["src"] if img_el else ""

            # Category guess from breadcrumb / name
            category = _guess_category(name)

            products.append({
                "product_id":   f"AMZ_{asin}",
                "product_name": name,
                "category":     category,
                "url":          f"{AMAZON_BASE}/dp/{asin}",
                "image":        image,
                "price":        price,
                "source":       "Amazon",
            })
        except Exception:
            continue

    return products


def amazon_reviews(product: dict, max_reviews: int = 15) -> list[dict]:
    """
    Scrape reviews for an Amazon product dict (must have 'url').
    Returns list of review dicts matching reviews_dataset.csv schema.
    """
    asin = product["product_id"].replace("AMZ_", "")
    reviews_url = f"{AMAZON_BASE}/product-reviews/{asin}?pageNumber=1&sortBy=recent"
    soup = _get(reviews_url)
    if soup is None:
        return []

    _sleep()
    reviews = []
    cards = soup.select("div[data-hook='review']")

    for card in cards[:max_reviews]:
        try:
            reviewer_el = card.select_one("span.a-profile-name")
            reviewer = reviewer_el.get_text(strip=True) if reviewer_el else "Anonymous"

            rating_el = card.select_one("i[data-hook='review-star-rating'] span, i[data-hook='cmps-review-star-rating'] span")
            rating_text = rating_el.get_text(strip=True) if rating_el else "3.0"
            rating = int(float(re.search(r"[\d.]+", rating_text).group()))

            title_el = card.select_one("a[data-hook='review-title'] span:last-child, span[data-hook='review-title']")
            title = title_el.get_text(strip=True) if title_el else ""

            body_el = card.select_one("span[data-hook='review-body'] span")
            body = body_el.get_text(strip=True) if body_el else ""

            date_el = card.select_one("span[data-hook='review-date']")
            date_str = date_el.get_text(strip=True) if date_el else ""
            date = _parse_amazon_date(date_str)

            if body:
                reviews.append({
                    "product_id":   product["product_id"],
                    "product_name": product["product_name"],
                    "category":     product["category"],
                    "reviewer":     reviewer,
                    "rating":       max(1, min(5, rating)),
                    "title":        title,
                    "review_text":  body,
                    "date":         date,
                })
        except Exception:
            continue

    return reviews


def _parse_amazon_date(text: str) -> str:
    """Try to extract a YYYY-MM-DD date from Amazon's date string."""
    months = {
        "january":"01","february":"02","march":"03","april":"04",
        "may":"05","june":"06","july":"07","august":"08",
        "september":"09","october":"10","november":"11","december":"12",
    }
    text = text.lower()
    for m, num in months.items():
        if m in text:
            year_m = re.search(r"\d{4}", text)
            day_m  = re.search(r"\b(\d{1,2})\b", text)
            year = year_m.group() if year_m else str(datetime.now().year)
            day  = day_m.group().zfill(2) if day_m else "01"
            return f"{year}-{num}-{day}"
    return datetime.now().strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# FLIPKART
# ─────────────────────────────────────────────────────────────────────────────

FLIPKART_BASE = "https://www.flipkart.com"


def flipkart_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search Flipkart for products.
    Returns list of dicts: {product_id, product_name, category, url, image, price}
    """
    url = f"{FLIPKART_BASE}/search?q={quote_plus(query)}"
    soup = _get(url)
    if soup is None:
        return []

    products = []

    # Flipkart uses different card classes — try both grid and list layouts
    cards = (
        soup.select("div._1AtVbE div._13oc-S")
        or soup.select("div._2kHMtA")
        or soup.select("div._1YokD2 div._1AtVbE")
    )

    # Fallback: find all product links
    if not cards:
        links = soup.select("a._1fQZEK, a.s1Q9rs, a._2rpwqI, a.IRpwTa")
        for link in links[:max_results]:
            try:
                name_el = link.select_one("div._4rR01T, div.IRpwTa, div._2WkVRV")
                name = name_el.get_text(strip=True) if name_el else link.get_text(strip=True)[:80]
                if not name or len(name) < 5:
                    continue
                href = link.get("href", "")
                full_url = urljoin(FLIPKART_BASE, href)
                pid = re.search(r"pid=([A-Z0-9]+)", href)
                product_id = f"FLK_{pid.group(1)}" if pid else f"FLK_{abs(hash(name)) % 100000}"
                price_el = link.select_one("div._30jeq3")
                price = price_el.get_text(strip=True) if price_el else "N/A"
                img_el = link.select_one("img._396cs4, img._2r_T1I")
                image = img_el.get("src", "") if img_el else ""
                products.append({
                    "product_id":   product_id,
                    "product_name": name,
                    "category":     _guess_category(name),
                    "url":          full_url,
                    "image":        image,
                    "price":        price,
                    "source":       "Flipkart",
                })
                if len(products) >= max_results:
                    break
            except Exception:
                continue
        return products

    for card in cards[:max_results]:
        try:
            name_el = card.select_one("div._4rR01T, a.s1Q9rs, div._2WkVRV, div.KzDlHZ")
            name = name_el.get_text(strip=True) if name_el else ""
            if not name:
                continue
            link_el = card.select_one("a._1fQZEK, a.s1Q9rs, a._2rpwqI")
            href = link_el["href"] if link_el and link_el.get("href") else ""
            full_url = urljoin(FLIPKART_BASE, href)
            pid = re.search(r"pid=([A-Z0-9]+)", href)
            product_id = f"FLK_{pid.group(1)}" if pid else f"FLK_{abs(hash(name)) % 100000}"
            price_el = card.select_one("div._30jeq3, div._25b18c")
            price = price_el.get_text(strip=True) if price_el else "N/A"
            img_el = card.select_one("img._396cs4, img._2r_T1I")
            image = img_el.get("src", "") if img_el else ""
            products.append({
                "product_id":   product_id,
                "product_name": name,
                "category":     _guess_category(name),
                "url":          full_url,
                "image":        image,
                "price":        price,
                "source":       "Flipkart",
            })
        except Exception:
            continue

    return products


def flipkart_reviews(product: dict, max_reviews: int = 15) -> list[dict]:
    """
    Scrape reviews from a Flipkart product page.
    Navigates to the reviews section of the product URL.
    """
    url = product.get("url", "")
    if not url:
        return []

    soup = _get(url)
    if soup is None:
        return []

    _sleep()

    # Find the "All reviews" link
    review_link = soup.select_one("a._2_R_DZ, a[href*='reviews']")
    if review_link and review_link.get("href"):
        reviews_url = urljoin(FLIPKART_BASE, review_link["href"])
        soup = _get(reviews_url) or soup
        _sleep()

    reviews = []
    cards = soup.select("div._27M-vq, div.col._2wzgFH, div.RcXBOT")

    for card in cards[:max_reviews]:
        try:
            rating_el = card.select_one("div._3LWZlK")
            rating = int(rating_el.get_text(strip=True)) if rating_el else 3

            reviewer_el = card.select_one("p._2sc7ZR, p._2NsDsF")
            reviewer = reviewer_el.get_text(strip=True) if reviewer_el else "Anonymous"

            title_el = card.select_one("p._2-N8zT, p.z9E0IG")
            title = title_el.get_text(strip=True) if title_el else ""

            body_el = card.select_one("div.t-ZTKy div, div._6K-7Co")
            body = body_el.get_text(strip=True) if body_el else ""
            if not body:
                body_el = card.select_one("div.qwjRop")
                body = body_el.get_text(strip=True) if body_el else ""

            date_el = card.select_one("p._2sc7ZR + p, p._2NsDsF")
            date_text = date_el.get_text(strip=True) if date_el else ""
            date = _parse_flipkart_date(date_text)

            if body and len(body) > 10:
                reviews.append({
                    "product_id":   product["product_id"],
                    "product_name": product["product_name"],
                    "category":     product["category"],
                    "reviewer":     reviewer,
                    "rating":       max(1, min(5, rating)),
                    "title":        title,
                    "review_text":  body[:500],
                    "date":         date,
                })
        except Exception:
            continue

    return reviews


def _parse_flipkart_date(text: str) -> str:
    months = {
        "jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06",
        "jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12",
    }
    text = text.lower()
    for m, num in months.items():
        if m in text:
            year_m = re.search(r"\d{4}", text)
            day_m  = re.search(r"\b(\d{1,2})\b", text)
            year = year_m.group() if year_m else str(datetime.now().year)
            day  = day_m.group().zfill(2) if day_m else "01"
            return f"{year}-{num}-{day}"
    return datetime.now().strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# Unified search
# ─────────────────────────────────────────────────────────────────────────────

def search_all(query: str, max_per_source: int = 5) -> list[dict]:
    """Search both Amazon and Flipkart, return combined product list."""
    results = []
    try:
        results += amazon_search(query, max_per_source)
    except Exception:
        pass
    _sleep()
    try:
        results += flipkart_search(query, max_per_source)
    except Exception:
        pass
    return results


def fetch_reviews(product: dict, max_reviews: int = 15) -> list[dict]:
    """Fetch reviews for a product dict (detects source from product_id prefix)."""
    if product["product_id"].startswith("AMZ_"):
        return amazon_reviews(product, max_reviews)
    elif product["product_id"].startswith("FLK_"):
        return flipkart_reviews(product, max_reviews)
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_CATEGORY_KEYWORDS = {
    "Smartphones":         ["phone", "mobile", "smartphone", "iphone", "samsung", "redmi", "realme", "oneplus", "vivo", "oppo", "poco", "motorola", "nokia"],
    "Laptops":             ["laptop", "notebook", "macbook", "chromebook", "thinkpad"],
    "Audio":               ["earphone", "headphone", "earbuds", "speaker", "tws", "headset", "boat", "neckband", "soundbar"],
    "Televisions":         ["tv", "television", "smart tv", "oled", "qled", "led tv"],
    "Kitchen Appliances":  ["mixer", "grinder", "juicer", "microwave", "oven", "induction", "cooker", "pressure cooker", "toaster", "blender", "air fryer"],
    "Cameras":             ["camera", "dslr", "mirrorless", "action cam", "gopro"],
    "Tablets":             ["tablet", "ipad", "tab"],
    "Wearables":           ["smartwatch", "watch", "fitness band", "band", "fitbit"],
    "Home Appliances":     ["washing machine", "refrigerator", "fridge", "ac", "air conditioner", "vacuum", "fan", "iron"],
    "Personal Care":       ["trimmer", "shaver", "dryer", "epilator", "straightener"],
}


def _guess_category(name: str) -> str:
    name_lower = name.lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return cat
    return "Electronics"

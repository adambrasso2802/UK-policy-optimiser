"""
Scraper for henryfudge.com — extracts blog posts, policy positions, and key claims.

Strategy:
1. Try requests + BeautifulSoup first.
2. If the page body appears JS-rendered (very low word count), fall back to Playwright.
"""

import json
import re
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://henryfudge.com"
SUBPAGES = [
    "/blog",
    "/policy",
    "/economics",
    "/ideas",
    "/about",
]
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "henry_fudge"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

POLICY_TOPICS = {
    "gdp_growth": ["gdp", "growth", "economic growth", "productivity", "output"],
    "inequality": ["inequality", "gini", "income gap", "wealth gap", "redistribution"],
    "poverty": ["poverty", "deprivation", "low income", "food bank", "universal credit"],
    "taxation": ["tax", "taxation", "vat", "income tax", "corporation tax", "fiscal"],
    "housing": ["housing", "house price", "rent", "planning", "housebuilding", "affordability"],
    "education": ["education", "school", "university", "tuition", "skills", "training"],
    "infrastructure": ["infrastructure", "investment", "transport", "broadband", "roads", "rail"],
    "trade": ["trade", "export", "import", "tariff", "customs", "wto", "brexit"],
    "public_spending": ["spending", "austerity", "public services", "nhs", "welfare", "budget"],
}

STAT_PATTERN = re.compile(
    r"""
    (?:
        \d+(?:\.\d+)?\s*(?:per\s*cent|%|billion|trillion|million|percentage\s+points?)
        | (?:per\s*cent|%|billion|trillion|million)\s+\d+(?:\.\d+)?
        | £\s*\d+(?:[,.]\d+)*(?:\s*(?:billion|trillion|million|bn|tn|m))?
        | \$\s*\d+(?:[,.]\d+)*(?:\s*(?:billion|trillion|million|bn|tn|m))?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# Fetching helpers
# ---------------------------------------------------------------------------


def fetch_with_requests(url: str) -> tuple[int, str]:
    resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    return resp.status_code, resp.text


def fetch_with_playwright(url: str) -> tuple[int, str]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        status = response.status if response else 0
        html = page.content()
        browser.close()
    return status, html


def fetch_page(url: str, slug: str) -> tuple[int, str] | None:
    """Fetch a page, falling back to Playwright if JS-rendered. Returns (status, html)."""
    log.info("Fetching %s", url)
    try:
        status, html = fetch_with_requests(url)
    except Exception as exc:
        log.warning("requests failed for %s: %s — trying Playwright", url, exc)
        try:
            status, html = fetch_with_playwright(url)
        except Exception as exc2:
            log.error("Playwright also failed for %s: %s", url, exc2)
            return None

    if status != 200:
        log.warning("Non-200 status %d for %s", status, url)
        return status, html

    # Heuristic: if parsed text is < 50 words, assume JS rendering needed
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    word_count = len(text.split())
    if word_count < 50:
        log.info("Page appears JS-rendered (%d words) — switching to Playwright", word_count)
        try:
            status, html = fetch_with_playwright(url)
        except Exception as exc:
            log.warning("Playwright fallback failed: %s", exc)

    # Save raw HTML
    html_path = OUTPUT_DIR / f"{slug}.html"
    html_path.write_text(html, encoding="utf-8")
    log.info("Saved raw HTML → %s", html_path)
    return status, html


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def word_count(text: str) -> int:
    return len(text.split())


def extract_policy_mentions(text: str) -> list[str]:
    """Return sentences that mention policy-like language."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    keywords = re.compile(
        r"\b(?:policy|reform|proposal|recommend|should|must|government|plan|measure|initiative|"
        r"legislation|regulation|bill|act|budget|spending|investment|cut|raise|reduce|increase)\b",
        re.IGNORECASE,
    )
    return [s.strip() for s in sentences if keywords.search(s)][:20]


def extract_key_claims(text: str) -> list[str]:
    """Return sentences containing statistical claims."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if STAT_PATTERN.search(s)][:20]


def classify_policy_positions(text: str, positions: dict) -> dict:
    """Add sentences to the appropriate topic bucket."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        lower = sentence.lower()
        for topic, keywords in POLICY_TOPICS.items():
            if any(kw in lower for kw in keywords):
                entry = sentence.strip()
                if entry and entry not in positions[topic]:
                    positions[topic].append(entry)
    return positions


def parse_posts(soup: BeautifulSoup, page_url: str) -> list[dict]:
    """Try to extract blog-post-like structures from a page."""
    posts = []

    # Common patterns: article tags, divs with class containing "post"/"entry"/"article"
    candidates = (
        soup.find_all("article")
        or soup.find_all(class_=re.compile(r"post|entry|article|blog", re.I))
    )

    for el in candidates:
        title_el = el.find(re.compile(r"h[1-4]"))
        title = title_el.get_text(strip=True) if title_el else ""

        # Date
        date_el = el.find(["time"]) or el.find(class_=re.compile(r"date|time|published", re.I))
        date = ""
        if date_el:
            date = date_el.get("datetime", "") or date_el.get_text(strip=True)

        # URL
        link_el = el.find("a", href=True)
        url = ""
        if link_el:
            href = link_el["href"]
            url = href if href.startswith("http") else BASE_URL.rstrip("/") + "/" + href.lstrip("/")

        # Body
        # Remove nav/header/footer noise
        for tag in el.find_all(["nav", "header", "footer", "script", "style"]):
            tag.decompose()
        body = el.get_text(" ", strip=True)

        if not title and not body:
            continue

        posts.append(
            {
                "title": title,
                "date": date,
                "url": url or page_url,
                "body": body,
                "policy_mentions": extract_policy_mentions(body),
                "key_claims": extract_key_claims(body),
            }
        )

    return posts


def parse_page_as_single_post(soup: BeautifulSoup, page_url: str, slug: str) -> dict | None:
    """Treat the whole page as one post when no article structure is found."""
    for tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
        tag.decompose()

    title_el = soup.find(re.compile(r"h[1-3]"))
    title = title_el.get_text(strip=True) if title_el else slug

    body = soup.get_text(" ", strip=True)
    body = re.sub(r"\s{2,}", " ", body).strip()

    if word_count(body) < 20:
        return None

    return {
        "title": title,
        "date": "",
        "url": page_url,
        "body": body,
        "policy_mentions": extract_policy_mentions(body),
        "key_claims": extract_key_claims(body),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    scraped_at = datetime.now(timezone.utc).isoformat()
    all_posts: list[dict] = []
    policy_positions: dict[str, list] = {topic: [] for topic in POLICY_TOPICS}

    urls_to_scrape = [(BASE_URL, "index")] + [
        (BASE_URL + sub, sub.lstrip("/")) for sub in SUBPAGES
    ]

    seen_bodies: set[str] = set()
    total_words = 0

    for url, slug in urls_to_scrape:
        result = fetch_page(url, slug)
        if result is None:
            log.warning("Skipping %s (fetch failed)", url)
            continue

        status, html = result

        if status == 404:
            log.info("Skipping %s (404)", url)
            continue

        if status != 200:
            print(f"\n*** ALERT: {url} returned HTTP {status} — stopping. ***\n", file=sys.stderr)
            sys.exit(1)

        soup = BeautifulSoup(html, "lxml")

        posts = parse_posts(soup, url)
        if not posts:
            single = parse_page_as_single_post(soup, url, slug)
            if single:
                posts = [single]

        for post in posts:
            body_key = post["body"][:200]
            if body_key in seen_bodies:
                continue
            seen_bodies.add(body_key)
            all_posts.append(post)
            total_words += word_count(post["body"])
            classify_policy_positions(post["body"], policy_positions)

    # --- Alert checks ---
    if total_words < 100:
        print(
            f"\n*** ALERT: Only {total_words} words extracted in total — "
            "this is likely a scrape failure. Check the saved HTML files. ***\n",
            file=sys.stderr,
        )
        sys.exit(2)

    result_data = {
        "scraped_at": scraped_at,
        "source": BASE_URL,
        "posts": all_posts,
        "policy_positions": policy_positions,
    }

    json_path = OUTPUT_DIR / "extracted.json"
    try:
        json_path.write_text(json.dumps(result_data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        print(f"\n*** ALERT: Could not save JSON: {exc} ***\n", file=sys.stderr)
        sys.exit(3)

    log.info("Saved extraction → %s", json_path)

    # --- Summary ---
    total_policy = sum(len(v) for v in policy_positions.values())
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Posts / pages extracted : {len(all_posts)}")
    print(f"Total words extracted   : {total_words:,}")
    print(f"Policy sentences total  : {total_policy}")
    print()
    print("Policy positions by topic:")
    for topic, items in policy_positions.items():
        print(f"  {topic:<20} {len(items)} sentence(s)")
    print()
    print(f"Output → {json_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()

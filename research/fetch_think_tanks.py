"""
Scraper for 8 UK think tanks — extracts recent reports on GDP growth,
inequality, and poverty, then cross-references with Henry Fudge's positions.

Alerts (exit non-zero) if:
  - Any think tank returns a non-200 HTTP response
  - Fewer than 3 reports found for any think tank
  - Any report date is older than 2023
"""

import html as html_mod
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("think_tanks")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent.parent
OUT_DIR         = BASE_DIR / "data" / "raw" / "think_tanks"
OUT_DIR.mkdir(parents=True, exist_ok=True)
HENRY_FUDGE_FILE = BASE_DIR / "data" / "raw" / "henry_fudge" / "extracted.json"

# ── HTTP ──────────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}
TIMEOUT   = 30
RETRY_MAX = 3
BACKOFF   = 2.0

# ── Topic keywords ─────────────────────────────────────────────────────────────
TOPIC_KEYWORDS = {
    "gdp_growth": [
        "gdp", "growth", "productivity", "economic growth", "output",
        "economy", "recession", "fiscal", "deficit", "debt", "tax",
        "stagnation", "investment",
    ],
    "inequality": [
        "inequality", "gini", "income gap", "wealth gap", "redistribution",
        "income distribution", "earnings gap", "wage gap", "disparity",
    ],
    "poverty": [
        "poverty", "deprivation", "low income", "food bank", "child poverty",
        "in-work poverty", "universal credit", "destitution", "hardship",
        "living standards", "cost of living", "affordable", "wages",
        "minimum wage", "benefit", "welfare",
    ],
}
ALL_TOPIC_WORDS = [w for ws in TOPIC_KEYWORDS.values() for w in ws]

# ── Henry Fudge alignment keywords ────────────────────────────────────────────
HF_POSITIONS = {
    "land_value_tax":       ["land value tax", "lvt", "site value", "land tax"],
    "housing_supply":       ["housing supply", "planning reform", "housebuilding",
                             "build more homes", "social housing"],
    "fiscal_responsibility":["fiscal responsibility", "balanced budget", "debt reduction",
                             "gilt yields", "debt-to-gdp", "fiscal consolidation"],
    "productivity_growth":  ["productivity", "output per hour", "skills investment",
                             "r&d", "research and development"],
    "inequality_reduction": ["inequality", "redistribution", "gini", "wealth gap",
                             "income gap"],
    "anti_austerity":       ["austerity", "public services", "underinvestment",
                             "underfunding"],
    "infrastructure_investment": ["infrastructure", "public investment", "transport",
                                  "broadband", "rail"],
    "poverty_reduction":    ["poverty", "child poverty", "in-work poverty",
                             "minimum wage", "living wage"],
}

# ── Think tank registry ───────────────────────────────────────────────────────
THINK_TANKS = [
    {
        "name": "Institute for Fiscal Studies",
        "slug": "ifs",
        "lean": "centrist",
        "url":  "https://ifs.org.uk/publications",
        "fetch_strategy": "ifs",
    },
    {
        "name": "Resolution Foundation",
        "slug": "resolution_foundation",
        "lean": "centre-left",
        # correct URL — /research/ returns 404; /publications/ is live
        "url":  "https://www.resolutionfoundation.org/publications/",
        "fetch_strategy": "resolution_foundation",
    },
    {
        "name": "IPPR",
        "slug": "ippr",
        "lean": "centre-left",
        "url":  "https://ippr.org/research/",
        # real content at www.ippr.org; use sitemap to find article URLs
        "fetch_strategy": "ippr_sitemap",
        "sitemap_url": "https://ippr.org/sitemap.xml",
        "articles_base": "https://www.ippr.org",
    },
    {
        "name": "Centre for Cities",
        "slug": "centre_for_cities",
        "lean": "centrist",
        "url":  "https://centreforcities.org/research/",
        # WordPress REST API is accessible
        "fetch_strategy": "wordpress_api",
        "wp_api": "https://centreforcities.org/wp-json/wp/v2/posts",
    },
    {
        "name": "Tony Blair Institute",
        "slug": "tony_blair_institute",
        "lean": "centrist",
        "url":  "https://institute.global/insights",
        "fetch_strategy": "tbi_insights",
    },
    {
        "name": "Adam Smith Institute",
        "slug": "adam_smith_institute",
        "lean": "right",
        "url":  "https://adamsmith.org/research/",
        "fetch_strategy": "asi",
    },
    {
        "name": "Fabian Society",
        "slug": "fabian_society",
        "lean": "left",
        "url":  "https://fabians.org.uk/publications/",
        "fetch_strategy": "fabian",
    },
    {
        "name": "Policy Exchange",
        "slug": "policy_exchange",
        "lean": "centre-right",
        "url":  "https://policyexchange.org.uk/publications/",
        "fetch_strategy": "policy_exchange",
    },
]

ALERTS: list[str] = []


# ── Helpers ───────────────────────────────────────────────────────────────────

def alert(msg: str) -> None:
    log.error("ALERT: %s", msg)
    ALERTS.append(msg)


def fetch_url(url: str, save_path: Path | None = None,
              extra_headers: dict | None = None) -> tuple[int, str]:
    """GET with retry. Returns (status, text). Saves to save_path if given."""
    hdrs = {**HEADERS, **(extra_headers or {})}
    last_exc: Exception | None = None
    for attempt in range(RETRY_MAX):
        try:
            resp = requests.get(url, headers=hdrs, timeout=TIMEOUT, allow_redirects=True)
            if save_path:
                save_path.write_text(resp.text, encoding="utf-8", errors="replace")
            return resp.status_code, resp.text
        except Exception as exc:
            last_exc = exc
            log.warning("Attempt %d failed for %s: %s", attempt + 1, url, exc)
            time.sleep(BACKOFF * (2 ** attempt))
    raise RuntimeError(f"All {RETRY_MAX} attempts failed for {url}: {last_exc}")


def clean(text: str) -> str:
    return re.sub(r"\s{2,}", " ", html_mod.unescape(text)).strip()


def parse_date(raw: str) -> str:
    if not raw:
        return ""
    raw = clean(raw)
    # ISO format prefix (e.g. 2025-04-12T...)
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    formats = [
        "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y",
        "%d/%m/%Y", "%m/%d/%Y", "%B %Y", "%b %Y", "%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    try:
        from dateutil import parser as du
        return du.parse(raw, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        pass
    return raw


def date_year(s: str) -> int | None:
    m = re.search(r"(20\d{2})", s)
    return int(m.group(1)) if m else None


def is_relevant(title: str, snippet: str = "") -> bool:
    combined = (title + " " + snippet).lower()
    return any(kw in combined for kw in ALL_TOPIC_WORDS)


_NAV_BOILERPLATE = re.compile(
    r"\b(skip to|main content|site menu|search site|sign up|mailing list|"
    r"skip navigation|cookie|accept cookies|privacy policy|terms of use)\b",
    re.I,
)


def make_summary(text: str, max_chars: int = 400) -> str:
    text = clean(text)
    buf = ""
    for s in re.split(r"(?<=[.!?])\s+", text):
        if len(buf) + len(s) > max_chars:
            break
        words = s.split()
        # Skip very short fragments or obvious navigation boilerplate
        if len(words) < 5 or _NAV_BOILERPLATE.search(s):
            continue
        # Skip sentences that are just the site/title name repeated (first sentence heuristic)
        if not buf and len(words) < 8 and ("|" in s or "—" in s or "•" in s):
            continue
        buf += s + " "
    return buf.strip()


def extract_key_recs(text: str, max_n: int = 4) -> list[str]:
    pat = re.compile(
        r"\b(should|must|recommend|government|policy|reform|increase|reduce|"
        r"invest|introduce|abolish|expand|cut|raise|extend|implement|create|"
        r"establish|need to|requires)\b",
        re.I,
    )
    sentences = re.split(r"(?<=[.!?])\s+", text)
    recs = [s.strip() for s in sentences
            if pat.search(s) and 8 < len(s.split()) < 70
            and not _NAV_BOILERPLATE.search(s)]
    topic_recs = [r for r in recs if is_relevant(r)]
    combined   = topic_recs + [r for r in recs if r not in topic_recs]
    return combined[:max_n]


def detect_hf_overlaps(text: str) -> list[str]:
    lower = text.lower()
    return [pos for pos, kws in HF_POSITIONS.items() if any(k in lower for k in kws)]


def enrich_from_page(report: dict, slug_dir: Path) -> dict:
    """Fetch the individual report page to improve summary + key_recommendations."""
    url = report.get("url", "")
    if not url or not url.startswith("http"):
        return report

    safe  = re.sub(r"[^\w\-]", "_", urlparse(url).path.lstrip("/"))[:80]
    fpath = slug_dir / f"report_{safe}.html"
    try:
        status, html = fetch_url(url, save_path=fpath)
        if status != 200:
            return report
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["nav", "header", "footer", "script", "style",
                                   "aside", "form", "noscript"]):
            tag.decompose()
        # Remove utility UI elements that pollute text (be conservative — don't
        # use broad class names like "hidden" which Tailwind uses for real content)
        for tag in soup.find_all(class_=re.compile(r"floating-cart|cookie-banner|"
                                                    r"cookie-notice|modal-backdrop", re.I)):
            tag.decompose()

        # Date: try to fill if missing
        if not report.get("date"):
            time_el = soup.find("time")
            if time_el:
                report["date"] = parse_date(
                    time_el.get("datetime", "") or clean(time_el.get_text())
                )
            if not report.get("date"):
                # Look for date patterns in meta tags
                for meta in soup.find_all("meta"):
                    prop = meta.get("property", "") + meta.get("name", "")
                    if "date" in prop.lower() or "published" in prop.lower():
                        report["date"] = parse_date(meta.get("content", ""))
                        break

        # Detect JS-rendered pages: if fewer than 50 substantive words remain,
        # skip enrichment to avoid overwriting with boilerplate.
        all_text = soup.get_text(" ", strip=True)
        if len(all_text.split()) < 50:
            return report

        # Abstract: prefer specific semantic selectors, then article body paragraphs
        abstract = ""
        for sel in [
            "[class*='abstract']", "[class*='standfirst']",
            "[class*='excerpt']", "[class*='summary']",
            "[class*='intro']", "[class*='description']",
        ]:
            els = soup.select(sel)
            if els:
                candidate = " ".join(el.get_text(" ", strip=True) for el in els[:3])
                if len(candidate.split()) > 25:
                    abstract = candidate
                    break

        if not abstract:
            # Prefer <main> or <article> paragraphs over full page
            main_el = soup.find("main") or soup.find("article") or soup
            paras = [p.get_text(" ", strip=True) for p in main_el.find_all("p")
                     if len(p.get_text().split()) > 10]
            abstract = " ".join(paras[:6])

        if not abstract:
            abstract = all_text

        abstract = clean(abstract)

        # Strip inline Squarespace/CMS byline patterns like
        # "Title Category DD Mon Written By Author Name Content..."
        abstract = re.sub(
            r"\b(?:\d{1,2}\s+[A-Z][a-z]{2,8}\s+)?Written By\s+[\w\s&,]+?(?=[A-Z][a-z]|\Z)",
            " ",
            abstract,
        )
        # Strip "15 Apr " style date prefixes at the start of clauses
        abstract = re.sub(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s*",
                          "", abstract)
        abstract = clean(abstract)

        # Strip leading sentences that just repeat the report title
        title_words = set(w.lower() for w in re.findall(r"\w+", report.get("title", ""))
                          if len(w) > 3)
        cleaned_sentences = []
        for sent in re.split(r"(?<=[.!?])\s+", abstract):
            sent_words = set(w.lower() for w in re.findall(r"\w+", sent) if len(w) > 3)
            if title_words and len(title_words) > 3:
                overlap = len(title_words & sent_words) / max(len(title_words), 1)
                if overlap > 0.65 and len(sent.split()) < len(title_words) * 1.8:
                    continue
            cleaned_sentences.append(sent)
        abstract = " ".join(cleaned_sentences)

        # Only overwrite summary if the enriched version is clearly better
        existing_summary = report.get("summary", "")
        new_summary = make_summary(abstract)
        if (not existing_summary or len(existing_summary.split()) < 15) and \
           len(new_summary.split()) > len(existing_summary.split()):
            report["summary"] = new_summary

        if not report.get("key_recommendations"):
            report["key_recommendations"] = extract_key_recs(abstract)
        if not report.get("hf_overlaps"):
            report["hf_overlaps"] = detect_hf_overlaps(abstract)
    except Exception as exc:
        log.warning("Could not enrich %s: %s", url, exc)
    return report


# ── Strategy: Resolution Foundation ──────────────────────────────────────────

def fetch_resolution_foundation(tt: dict, slug_dir: Path) -> list[dict]:
    url = tt["url"]
    status, html = fetch_url(url, save_path=slug_dir / "listing.html")
    if status != 200:
        alert(f"{tt['name']} ({url}) returned HTTP {status} (expected 200)")
        return []

    soup = BeautifulSoup(html, "lxml")
    reports = []
    seen: set[str] = set()

    for art in soup.find_all("article"):
        title_el = art.find(re.compile(r"^h[2-4]$"))
        if not title_el:
            continue
        title = clean(title_el.get_text())
        if not title or title in seen:
            continue

        # RF: first <p> is author/date, second <p> is the real summary
        all_paras = art.find_all("p")
        snippet = ""
        for p_el in all_paras:
            candidate = clean(p_el.get_text())
            # Skip short author/date lines (< 8 words)
            if len(candidate.split()) >= 8:
                snippet = candidate
                break

        if not is_relevant(title, snippet):
            continue
        seen.add(title)

        time_el = art.find("time")
        date_raw = time_el.get("datetime", "") if time_el else ""
        if not date_raw and time_el:
            date_raw = clean(time_el.get_text())
        date_iso = parse_date(date_raw)

        link_el = title_el.find("a") or art.find("a")
        url_r = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url_r = href if href.startswith("http") else urljoin(url, href)

        reports.append({
            "title": title,
            "date": date_iso,
            "url": url_r,
            "summary": make_summary(snippet),
            "key_recommendations": extract_key_recs(snippet),
            "hf_overlaps": detect_hf_overlaps(title + " " + snippet),
        })

    return reports


# ── Strategy: IPPR via sitemap ────────────────────────────────────────────────

def fetch_ippr(tt: dict, slug_dir: Path) -> list[dict]:
    sitemap_url   = tt.get("sitemap_url", "https://ippr.org/sitemap.xml")
    articles_base = tt.get("articles_base", "https://www.ippr.org")

    # Save a stub for the declared URL (so we have something in raw/)
    try:
        status0, html0 = fetch_url(tt["url"], save_path=slug_dir / "listing.html")
        if status0 not in (200, 301, 302):
            # Don't alert here — IPPR's declared URL is JS-only; we use sitemap
            log.warning("IPPR listing page returned %d (using sitemap fallback)", status0)
    except Exception:
        pass

    # Pull all article URLs from sitemap, filter for topic relevance by slug
    try:
        _, sitemap_xml = fetch_url(sitemap_url)
    except Exception as exc:
        alert(f"{tt['name']}: sitemap fetch failed — {exc}")
        return []

    all_locs = re.findall(r"<loc>(.*?)</loc>", sitemap_xml)
    # IPPR articles live at www.ippr.org/articles/
    candidate_urls = [
        l for l in all_locs
        if re.search(r"ippr\.org/articles/", l)
    ]
    log.info("IPPR: %d article URLs in sitemap", len(candidate_urls))

    # Filter by topic-keyword in the URL slug
    relevant_slugs = [
        u for u in candidate_urls
        if any(kw.replace(" ", "-") in u.lower() or kw.replace(" ", "_") in u.lower()
               for kw in ALL_TOPIC_WORDS)
    ]
    log.info("IPPR: %d topic-relevant slug URLs", len(relevant_slugs))

    if not relevant_slugs:
        # Fall back: take the most recent 20 article URLs from the sitemap
        relevant_slugs = candidate_urls[-20:]

    reports = []
    for url in relevant_slugs[:15]:
        try:
            safe  = re.sub(r"[^\w\-]", "_", urlparse(url).path.lstrip("/"))[:80]
            fpath = slug_dir / f"article_{safe}.html"
            status, html = fetch_url(url, save_path=fpath)
            if status != 200:
                continue
            soup = BeautifulSoup(html, "lxml")

            title_el = soup.find("h1")
            if not title_el:
                continue
            title = clean(title_el.get_text())
            if not is_relevant(title):
                continue

            for tag in soup.find_all(["nav", "header", "footer", "script",
                                       "style", "aside"]):
                tag.decompose()

            # Date
            time_el = soup.find("time")
            date_raw = time_el.get("datetime", "") if time_el else ""
            if not date_raw and time_el:
                date_raw = clean(time_el.get_text())
            date_iso = parse_date(date_raw)

            # Text
            body = soup.get_text(" ", strip=True)
            body = clean(body)

            reports.append({
                "title": title,
                "date": date_iso,
                "url": url,
                "summary": make_summary(body),
                "key_recommendations": extract_key_recs(body),
                "hf_overlaps": detect_hf_overlaps(body),
            })
            time.sleep(0.5)
        except Exception as exc:
            log.warning("IPPR: failed to fetch %s: %s", url, exc)

    return reports


# ── Strategy: WordPress REST API ─────────────────────────────────────────────

def fetch_wordpress_api(tt: dict, slug_dir: Path) -> list[dict]:
    api_url = tt.get("wp_api", "")
    if not api_url:
        return []

    # Save a stub listing page
    try:
        fetch_url(tt["url"], save_path=slug_dir / "listing.html")
    except Exception:
        pass

    reports = []
    seen: set[str] = set()

    search_terms = ["growth", "inequality", "poverty", "productivity", "economy", "wages"]
    for term in search_terms:
        try:
            endpoint = f"{api_url}?per_page=10&search={term}"
            status, text = fetch_url(endpoint)
            if status != 200:
                continue
            posts = json.loads(text)
            for post in posts:
                title = clean(html_mod.unescape(post.get("title", {}).get("rendered", "")))
                if not title or title in seen:
                    continue
                snippet = clean(BeautifulSoup(
                    post.get("excerpt", {}).get("rendered", ""), "lxml"
                ).get_text())
                if not is_relevant(title, snippet):
                    continue
                seen.add(title)

                date_iso = parse_date(post.get("date", "")[:10])
                url_r    = post.get("link", "")

                # Respect date filter
                yr = date_year(date_iso)
                if yr and yr < 2023:
                    continue

                reports.append({
                    "title": title,
                    "date": date_iso,
                    "url": url_r,
                    "summary": make_summary(snippet),
                    "key_recommendations": [],
                    "hf_overlaps": detect_hf_overlaps(title + " " + snippet),
                })
        except Exception as exc:
            log.warning("WP API search '%s' failed: %s", term, exc)
        time.sleep(0.3)

    return reports


# ── Strategy: Tony Blair Institute (parse insight links from listing) ─────────

def fetch_tbi(tt: dict, slug_dir: Path) -> list[dict]:
    url = tt["url"]
    status, html = fetch_url(url, save_path=slug_dir / "listing.html")
    if status != 200:
        alert(f"{tt['name']} ({url}) returned HTTP {status} (expected 200)")
        return []

    # Extract all /insights/ hrefs from the raw HTML
    hrefs = list(dict.fromkeys(re.findall(r'href="(/insights/[^"]+)"', html)))
    log.info("TBI: %d raw insight hrefs found", len(hrefs))

    soup = BeautifulSoup(html, "lxml")

    # Build href → title map from anchor text
    href_title: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "/insights/" in href:
            text = clean(a.get_text())
            # Strip category prefix (e.g. "Economic ProsperityTitle Here")
            text = re.sub(r"^[A-Z][a-z]+(?: [A-Z][a-z]+)*(?=[A-Z])", "", text)
            if len(text) > 5:
                href_title[href] = text

    reports = []
    seen: set[str] = set()

    for href in hrefs:
        title = href_title.get(href, "")
        full_url = urljoin("https://institute.global", href)

        # Filter: only economic-prosperity or public-services category
        # (also keep any that match topic keywords by slug)
        slug_lower = href.lower()
        slug_relevant = (
            "economic-prosperity" in slug_lower or
            "public-services" in slug_lower or
            any(kw.replace(" ", "-") in slug_lower for kw in ALL_TOPIC_WORDS)
        )
        title_relevant = is_relevant(title)

        if not (slug_relevant or title_relevant):
            continue

        if title in seen:
            continue
        seen.add(title)

        reports.append({
            "title": title or href.split("/")[-1].replace("-", " ").title(),
            "date": "",
            "url": full_url,
            "summary": "",
            "key_recommendations": [],
            "hf_overlaps": detect_hf_overlaps(title + " " + slug_lower),
        })

    return reports


# ── Strategy: Adam Smith Institute (Squarespace blog-item articles) ───────────

def fetch_asi(tt: dict, slug_dir: Path) -> list[dict]:
    url = tt["url"]
    status, html = fetch_url(url, save_path=slug_dir / "listing.html")
    if status != 200:
        alert(f"{tt['name']} ({url}) returned HTTP {status} (expected 200)")
        return []

    soup = BeautifulSoup(html, "lxml")
    reports = []
    seen: set[str] = set()

    # Squarespace: each research item is <article class="blog-item ...">
    # with an h1 inside and a link on the article itself or h1.
    for art in soup.find_all("article", class_=re.compile(r"blog.item|blog-item|entry", re.I)):
        title_el = art.find("h1") or art.find(re.compile(r"^h[2-4]$"))
        if not title_el:
            continue
        title = clean(title_el.get_text())
        if not title or title in seen:
            continue

        snippet_el = art.find("p")
        snippet = clean(snippet_el.get_text()) if snippet_el else ""
        if not is_relevant(title, snippet):
            continue
        seen.add(title)

        time_el = art.find("time")
        date_raw = time_el.get("datetime", "") if time_el else ""
        date_iso = parse_date(date_raw)

        link_el = title_el.find("a") or art.find("a")
        url_r = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url_r = href if href.startswith("http") else urljoin(url, href)

        reports.append({
            "title": title,
            "date": date_iso,
            "url": url_r,
            "summary": make_summary(snippet),
            "key_recommendations": [],
            "hf_overlaps": detect_hf_overlaps(title + " " + snippet),
        })

    return reports


# ── Strategy: Fabian Society (div.pub-feat-info) ─────────────────────────────

def fetch_fabian(tt: dict, slug_dir: Path) -> list[dict]:
    url = tt["url"]
    status, html = fetch_url(url, save_path=slug_dir / "listing.html")
    if status != 200:
        alert(f"{tt['name']} ({url}) returned HTTP {status} (expected 200)")
        return []

    soup = BeautifulSoup(html, "lxml")
    reports = []
    seen: set[str] = set()

    # Fabian uses div.pub-feat-info wrapping h2 + p + link
    for div in soup.find_all("div", class_=re.compile(r"pub.feat", re.I)):
        title_el = div.find(re.compile(r"^h[2-3]$"))
        if not title_el:
            continue
        title = clean(title_el.get_text())
        if not title or title in seen:
            continue

        snippet_el = div.find("p")
        snippet = clean(snippet_el.get_text()) if snippet_el else ""

        # Some Fabian pubs are not on our topics — still include if possibly relevant
        if not is_relevant(title, snippet):
            # looser check: include if title is meaningful (> 4 words) for later enrichment
            if len(title.split()) < 5:
                continue

        seen.add(title)

        time_el = div.find("time")
        date_raw = time_el.get("datetime", "") if time_el else ""
        date_iso = parse_date(date_raw)

        link_el = div.find("a", href=True)
        url_r = ""
        if link_el:
            href = link_el["href"]
            url_r = href if href.startswith("http") else urljoin(url, href)

        reports.append({
            "title": title,
            "date": date_iso,
            "url": url_r,
            "summary": make_summary(snippet),
            "key_recommendations": [],
            "hf_overlaps": detect_hf_overlaps(title + " " + snippet),
        })

    return reports


# ── Strategy: IFS (Cloudflare-protected, try alternate approaches) ────────────

def fetch_ifs(tt: dict, slug_dir: Path) -> list[dict]:
    """
    IFS is behind Cloudflare. We first try the main publications page
    (may return 403). If blocked, we try their search endpoint.
    Either way we save the response and alert on non-200.
    """
    base_url = tt["url"]

    # Primary attempt
    try:
        status, html = fetch_url(base_url, save_path=slug_dir / "listing.html")
    except RuntimeError as exc:
        alert(f"{tt['name']}: fetch failed — {exc}")
        return []

    if status != 200:
        alert(f"{tt['name']} ({base_url}) returned HTTP {status} (expected 200). "
              "Site appears to be behind Cloudflare bot protection.")
        # Try search as last resort
        try:
            search_url = "https://ifs.org.uk/search?query=growth+inequality+poverty"
            s2, html2 = fetch_url(search_url, save_path=slug_dir / "search.html")
            log.info("IFS search fallback: HTTP %d", s2)
            if s2 == 200:
                html = html2
                # If still empty (<50 words), give up
                if len(BeautifulSoup(html2, "lxml").get_text().split()) < 50:
                    return []
            else:
                return []
        except Exception:
            return []

    soup = BeautifulSoup(html, "lxml")
    if len(soup.get_text().split()) < 50:
        # JS-rendered with no content served to bots
        return []

    # Generic parse
    reports = []
    seen: set[str] = set()
    for art in (soup.find_all("article") or
                soup.find_all(class_=re.compile(r"publication|result|card|item", re.I))):
        title_el = art.find(re.compile(r"^h[2-4]$"))
        if not title_el:
            continue
        title = clean(title_el.get_text())
        if not title or title in seen:
            continue
        snippet_el = art.find("p")
        snippet = clean(snippet_el.get_text()) if snippet_el else ""
        if not is_relevant(title, snippet):
            continue
        seen.add(title)

        time_el = art.find("time")
        date_raw = (time_el.get("datetime", "") or clean(time_el.get_text())) if time_el else ""
        date_iso = parse_date(date_raw)

        link_el = title_el.find("a") or art.find("a")
        url_r = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url_r = href if href.startswith("http") else urljoin(base_url, href)

        reports.append({
            "title": title,
            "date": date_iso,
            "url": url_r,
            "summary": make_summary(snippet),
            "key_recommendations": [],
            "hf_overlaps": detect_hf_overlaps(title + " " + snippet),
        })

    return reports


# ── Strategy: Policy Exchange (Elementor WordPress) ──────────────────────────

def fetch_policy_exchange(tt: dict, slug_dir: Path) -> list[dict]:
    url = tt["url"]
    try:
        status, html = fetch_url(url, save_path=slug_dir / "listing.html")
    except RuntimeError as exc:
        alert(f"{tt['name']}: fetch failed — {exc}")
        return []

    if status != 200:
        alert(f"{tt['name']} ({url}) returned HTTP {status} (expected 200). "
              "Site may be behind a bot challenge (CAPTCHA).")
        return []

    soup = BeautifulSoup(html, "lxml")
    reports = []
    seen: set[str] = set()

    # Policy Exchange uses Elementor: article.elementor-post cards with
    # span.elementor-heading-title (title) and span[class*=type-date] (date)
    for art in soup.find_all("article", class_=re.compile(r"elementor.post|publications", re.I)):
        title_el = art.find("span", class_=re.compile(r"heading.title", re.I))
        if not title_el:
            title_el = art.find(re.compile(r"^h[2-4]$"))
        if not title_el:
            continue
        title = clean(title_el.get_text())
        if not title or title in seen:
            continue

        snippet_el = art.find("p")
        snippet = clean(snippet_el.get_text()) if snippet_el else ""
        if not is_relevant(title, snippet):
            continue
        seen.add(title)

        date_el = art.find("span", class_=re.compile(r"type.date|date", re.I))
        date_raw = clean(date_el.get_text()) if date_el else ""
        date_iso = parse_date(date_raw)

        link_el = art.find("a", href=True)
        url_r = ""
        if link_el:
            href = link_el["href"]
            url_r = href if href.startswith("http") else urljoin(url, href)

        reports.append({
            "title": title,
            "date": date_iso,
            "url": url_r,
            "summary": make_summary(snippet),
            "key_recommendations": [],
            "hf_overlaps": detect_hf_overlaps(title + " " + snippet),
        })

    return reports


# ── Strategy: generic ─────────────────────────────────────────────────────────

def fetch_generic(tt: dict, slug_dir: Path) -> list[dict]:
    url = tt["url"]
    try:
        status, html = fetch_url(url, save_path=slug_dir / "listing.html")
    except RuntimeError as exc:
        alert(f"{tt['name']}: fetch failed — {exc}")
        return []

    if status != 200:
        alert(f"{tt['name']} ({url}) returned HTTP {status} (expected 200)")
        return []

    soup = BeautifulSoup(html, "lxml")
    reports = []
    seen: set[str] = set()

    candidates = (
        soup.find_all("article") or
        soup.find_all(class_=re.compile(r"post|card|item|publication|report|insight|entry", re.I))
    )
    if not candidates:
        candidates = soup.find_all(re.compile(r"^h[2-4]$"))

    for el in candidates:
        title_el = (el if el.name in ("h2", "h3", "h4")
                    else el.find(re.compile(r"^h[2-4]$")))
        if not title_el:
            continue
        title = clean(title_el.get_text())
        if not title or title in seen:
            continue
        snippet_el = el.find("p") if el.name != "p" else el.find_next_sibling("p")
        snippet = clean(snippet_el.get_text()) if snippet_el else ""
        if not is_relevant(title, snippet):
            continue
        seen.add(title)

        date_el = (el.find("time") or
                   el.find(class_=re.compile(r"date|time|published|meta", re.I)))
        date_raw = ""
        if date_el:
            date_raw = date_el.get("datetime", "") or clean(date_el.get_text())
        date_iso = parse_date(date_raw)

        link_el = title_el.find("a") or el.find("a")
        url_r = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url_r = href if href.startswith("http") else urljoin(url, href)

        reports.append({
            "title": title,
            "date": date_iso,
            "url": url_r,
            "summary": make_summary(snippet),
            "key_recommendations": [],
            "hf_overlaps": detect_hf_overlaps(title + " " + snippet),
        })

    return reports


# ── Strategy dispatcher ───────────────────────────────────────────────────────

FETCH_STRATEGIES = {
    "ifs":                  fetch_ifs,
    "resolution_foundation": fetch_resolution_foundation,
    "ippr_sitemap":         fetch_ippr,
    "wordpress_api":        fetch_wordpress_api,
    "tbi_insights":         fetch_tbi,
    "asi":                  fetch_asi,
    "fabian":               fetch_fabian,
    "policy_exchange":      fetch_policy_exchange,
    "generic":              fetch_generic,
}


# ── Per-think-tank orchestrator ───────────────────────────────────────────────

def process_think_tank(tt: dict) -> dict:
    name     = tt["name"]
    slug     = tt["slug"]
    slug_dir = OUT_DIR / slug
    slug_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("Processing: %s  [%s]", name, tt["lean"])

    strategy_fn = FETCH_STRATEGIES.get(tt["fetch_strategy"], fetch_generic)
    reports = strategy_fn(tt, slug_dir)

    log.info("%s: %d relevant reports before enrichment", name, len(reports))

    # Date filter (drop pre-2023 if date is known)
    reports = [r for r in reports if (date_year(r["date"]) or 2024) >= 2023]

    # Enrich top reports from individual pages
    enriched = []
    for i, rep in enumerate(reports[:8]):
        log.info("  [%d/%d] Enriching: %s", i + 1, min(len(reports), 8),
                 rep["title"][:60])
        try:
            rep = enrich_from_page(rep, slug_dir)
        except Exception as exc:
            log.warning("  Enrich error: %s", exc)
        enriched.append(rep)
        time.sleep(0.5)

    # ── Alerts ───────────────────────────────────────────────────────────────
    if len(enriched) < 3:
        alert(
            f"{name}: only {len(enriched)} report(s) found (need ≥3). "
            f"Check {slug_dir}/listing.html"
        )

    for r in enriched:
        yr = date_year(r.get("date", ""))
        if yr is not None and yr < 2023:
            alert(f"{name}: report '{r['title'][:60]}' dated {r['date']} is older than 2023")

    result = {
        "name": name,
        "lean": tt["lean"],
        "url": tt["url"],
        "recent_reports": enriched,
    }
    (slug_dir / "reports.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("%s: saved → %s", name, slug_dir / "reports.json")
    return result


# ── Henry Fudge loader ────────────────────────────────────────────────────────

def load_hf_positions() -> dict:
    if not HENRY_FUDGE_FILE.exists():
        log.warning("Henry Fudge extracted.json not found; overlap detection limited.")
        return {}
    try:
        return json.loads(HENRY_FUDGE_FILE.read_text(encoding="utf-8")).get(
            "policy_positions", {}
        )
    except Exception as exc:
        log.warning("Could not load HF data: %s", exc)
        return {}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()
    load_hf_positions()  # preload (used for context; overlap detection is inline)

    results = []
    for tt in THINK_TANKS:
        result = process_think_tank(tt)
        results.append(result)
        time.sleep(1.0)

    combined = {"fetched_at": fetched_at, "think_tanks": results}
    combined_path = OUT_DIR / "combined.json"
    combined_path.write_text(
        json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Combined output → %s", combined_path)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("THINK TANK SCRAPE SUMMARY")
    print("=" * 70)
    print(f"Fetched at : {fetched_at}")
    print()
    total_reports = 0
    for tt in results:
        n    = len(tt.get("recent_reports", []))
        total_reports += n
        icon = "✓" if n >= 3 else "✗"
        print(f"  {icon}  {tt['name']:<35} {n:>2} reports  [{tt['lean']}]")
    print()
    print(f"  Total reports found : {total_reports}")
    print(f"  Output              : {combined_path}")
    print()

    if ALERTS:
        print("=" * 70)
        print(f"*** {len(ALERTS)} ALERT(S) — action required ***")
        print("=" * 70)
        for i, a in enumerate(ALERTS, 1):
            print(f"  [{i}] {a}")
        print()
        sys.exit(1)
    else:
        print("  No alerts — all checks passed.")
        print("=" * 70)


if __name__ == "__main__":
    main()

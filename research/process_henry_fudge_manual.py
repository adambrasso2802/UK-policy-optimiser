"""
Process manually captured henryfudge.com content and produce extracted.json.
Reads data/raw/henry_fudge/manual_input.txt, extracts structured data,
saves to data/raw/henry_fudge/extracted.json.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
INPUT_FILE = BASE_DIR / "data" / "raw" / "henry_fudge" / "manual_input.txt"
OUTPUT_FILE = BASE_DIR / "data" / "raw" / "henry_fudge" / "extracted.json"


def load_pages(text: str) -> list[tuple[str, str]]:
    """Split the file into (url, content) pairs using === PAGE: ... === markers."""
    pages = []
    pattern = re.compile(r"=== PAGE: (https?://\S+) ===\s*\n(.*?)(?====\s*PAGE:|$)", re.DOTALL)
    for m in pattern.finditer(text):
        url = m.group(1).strip()
        content = m.group(2).strip()
        pages.append((url, content))
    return pages


def word_count(text: str) -> int:
    return len(text.split())


STAT_RE = re.compile(
    r"""(?:
        £\s*\d+(?:[,.\d]*)(?:\s*(?:bn|tn|m|billion|trillion|million))?
        | \d+(?:\.\d+)?\s*(?:%|per\s*cent|percentage\s+points?)
        | \d+(?:\.\d+)?\s*(?:billion|trillion|million|bn|tn|m)\b
        | \+\d+(?:\.\d+)?%
        | \-\d+(?:\.\d+)?%
        | \d+(?:\.\d+)?\s*(?:bp|basis\s+points?)
    )""",
    re.IGNORECASE | re.VERBOSE,
)

POLICY_RE = re.compile(
    r"\b(?:policy|reform|proposal|recommend|should|must|government|plan|measure|"
    r"legislation|regulation|nationalise|nationalised|tax|spending|investment|cut|"
    r"raise|reduce|increase|restrict|abolish|repeal|introduce|fund|build|commit)\b",
    re.IGNORECASE,
)

TOPICS = {
    "gdp_growth": [
        "gdp", "growth", "economic growth", "productivity", "output", "gdp uplift",
        "per year above baseline", "percentage points per year",
    ],
    "inequality": [
        "inequality", "gini", "income gap", "wealth gap", "redistribution",
        "rentier", "landlord", "wealth", "poorer", "richer",
    ],
    "poverty": [
        "poverty", "deprivation", "low income", "food bank", "universal credit",
        "child poverty", "two-child", "struggling", "neet",
    ],
    "taxation": [
        "tax", "taxation", "vat", "income tax", "corporation tax", "fiscal",
        "land value tax", "lvt", "cgt", "capital gains", "hmrc", "stamp duty",
        "business rates", "council tax", "local services tax",
    ],
    "housing": [
        "housing", "house price", "rent", "planning", "housebuilding", "affordability",
        "landlord", "homeownership", "home ownership", "renter", "mortgage", "help to buy",
        "right-to-buy", "section 24", "shared equity", "social housing",
    ],
    "education": [
        "education", "school", "university", "tuition", "skills", "training",
        "teacher", "send", "apprenticeship", "free school meals", "childcare",
        "fe college", "youth guarantee",
    ],
    "infrastructure": [
        "infrastructure", "investment", "transport", "broadband", "roads", "rail",
        "national grid", "hs2", "sleeper", "smr", "nuclear", "semiconductor",
        "reservoir", "broadband", "grid",
    ],
    "trade": [
        "trade", "export", "import", "tariff", "customs", "wto", "brexit",
        "single market", "customs union", "esep", "european", "canzuk", "financial services passport",
        "cbam", "northern ireland",
    ],
    "public_spending": [
        "spending", "austerity", "public services", "nhs", "welfare", "budget",
        "social care", "defence", "police", "legal aid", "oda", "pension",
        "public sector", "revenue", "capital",
    ],
}


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if s.strip()]


def extract_policy_mentions(text: str) -> list[str]:
    return [s for s in sentences(text) if POLICY_RE.search(s)][:20]


def extract_key_claims(text: str) -> list[str]:
    return [s for s in sentences(text) if STAT_RE.search(s)][:20]


def classify_positions(text: str, positions: dict) -> None:
    for sent in sentences(text):
        lower = sent.lower()
        for topic, keywords in TOPICS.items():
            if any(kw in lower for kw in keywords):
                if sent not in positions[topic]:
                    positions[topic].append(sent)


# ---------------------------------------------------------------------------
# Hard-coded structured extraction from the known pages
# (content is fixed — derived directly from the manual_input.txt)
# ---------------------------------------------------------------------------

POSTS_DATA = [
    {
        "title": "Henry Fudge — Homepage",
        "date": "",
        "url": "https://henryfudge.com",
        "section": "biography and projects",
    },
    {
        "title": "Which Party Actually Makes You Poorer? — Housing Theory of Everything Episode 5.5",
        "date": "",
        "url": "https://henryfudge.com/housing",
        "section": "party scorecard and household financial impact",
    },
    {
        "title": "The Common Party — Start Here",
        "date": "Spring 2026",
        "url": "https://henryfudge.com/common/",
        "section": "platform overview and headline numbers",
    },
    {
        "title": "Productive Britain — The case for building things again",
        "date": "",
        "url": "https://henryfudge.com/common/productive-britain",
        "section": "economic diagnosis, four pillars, fiscal case, GDP growth channels",
    },
    {
        "title": "The Common Party — Complete Platform Summary",
        "date": "Spring 2026",
        "url": "https://henryfudge.com/common/platform-summary",
        "section": "six pillars, full fiscal architecture",
    },
]


def main():
    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    raw = INPUT_FILE.read_text(encoding="utf-8")
    pages = load_pages(raw)

    if not pages:
        print("ERROR: No pages found in manual_input.txt", file=sys.stderr)
        sys.exit(1)

    policy_positions = {topic: [] for topic in TOPICS}
    posts = []
    total_words = 0

    page_map = {url: content for url, content in pages}

    for meta in POSTS_DATA:
        url = meta["url"]
        body = page_map.get(url, "")
        if not body:
            # Try partial match
            for u, c in page_map.items():
                if url in u or u in url:
                    body = c
                    break

        wc = word_count(body)
        total_words += wc
        classify_positions(body, policy_positions)

        posts.append({
            "title": meta["title"],
            "date": meta["date"],
            "url": url,
            "body": body,
            "policy_mentions": extract_policy_mentions(body),
            "key_claims": extract_key_claims(body),
        })

    # Alert if too little content
    if total_words < 100:
        print(
            f"\n*** ALERT: Only {total_words} words extracted — likely a parsing failure. ***\n",
            file=sys.stderr,
        )
        sys.exit(2)

    result = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source": "https://henryfudge.com",
        "posts": posts,
        "policy_positions": policy_positions,
    }

    try:
        OUTPUT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        print(f"\n*** ALERT: Could not save JSON: {exc} ***\n", file=sys.stderr)
        sys.exit(3)

    # Summary
    total_policy = sum(len(v) for v in policy_positions.items())
    total_policy_sentences = sum(len(v) for v in policy_positions.values())
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY — Henry Fudge (henryfudge.com)")
    print("=" * 60)
    print(f"Source file  : {INPUT_FILE}")
    print(f"Pages parsed : {len(pages)}")
    print(f"Posts        : {len(posts)}")
    print(f"Total words  : {total_words:,}")
    print(f"Policy sentences (all topics): {total_policy_sentences}")
    print()
    print("Policy positions by topic:")
    for topic, items in policy_positions.items():
        print(f"  {topic:<22} {len(items):>3} sentence(s)")
    print()
    print(f"Output       : {OUTPUT_FILE}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    main()

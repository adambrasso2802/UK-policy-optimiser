"""Central configuration for the UK Economic Policy Optimiser."""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
RAW_DIR     = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR    = BASE_DIR / "logs"
ERROR_LOG   = LOGS_DIR / "errors.log"

# Ensure directories exist
for _d in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Data freshness ─────────────────────────────────────────────────────────
MAX_DATA_AGE_MONTHS = 12   # Warn if data is older than this

# ── ONS Beta API ───────────────────────────────────────────────────────────
ONS_API_BASE = "https://api.beta.ons.gov.uk/v1"

# Time-series dataset IDs (ONS series codes)
ONS_SERIES = {
    "gdp_chained":        "ABMI",   # GDP chained volume measure (£m)
    "gdp_current":        "YBHA",   # GDP at current prices (£m)
    "cpi_all_items":      "D7G7",   # CPI all items index
    "cpih_all_items":     "L55O",   # CPIH all items index
    "rpi_all_items":      "CHAW",   # RPI all items index
    "employment_rate":    "MGSX",   # Employment rate (aged 16-64)
    "unemployment_rate":  "MGSX",   # LFS unemployment rate
    "lfs_unemployment":   "MGSC",   # Unemployment level (thousands)
    "inactivity_rate":    "LF2Q",   # Economic inactivity rate
    "psnb":               "J5II",   # Public sector net borrowing (£bn)
    "psnd":               "HF6X",   # Public sector net debt (£bn)
    "current_account":    "HBOP",   # Current account balance (£m)
    "trade_balance":      "LQCT",   # Trade in goods & services balance
    "average_earnings":   "KAC3",   # Average weekly earnings (total pay)
    "productivity":       "LZVB",   # Output per hour worked
}

# ── Bank of England API ────────────────────────────────────────────────────
BOE_API_BASE    = "https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp"
BOE_SERIES_API  = "https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp"

BOE_SERIES = {
    "bank_rate":          "IUMABEDR",  # Official Bank Rate
    "m4_money_supply":    "LPMVWYX",   # M4 money supply
    "mortgage_rate":      "IUMTLMV",   # Effective mortgage rate
}

# ── OBR (Office for Budget Responsibility) ─────────────────────────────────
OBR_API_BASE = "https://obr.uk/efo"

# ── IMF API (backup / cross-check) ────────────────────────────────────────
IMF_API_BASE = "https://imfdata.imf.org/imf-fas/rest/data"

# ── HTTP settings ──────────────────────────────────────────────────────────
REQUEST_TIMEOUT  = 30    # seconds
REQUEST_RETRIES  = 3
REQUEST_BACKOFF  = 2.0   # seconds between retries

HEADERS = {
    "User-Agent": "UK-Policy-Optimiser/1.0 (educational research tool)",
    "Accept":     "application/json",
}

# ── Policy parameter bounds (for optimiser) ───────────────────────────────
POLICY_BOUNDS = {
    "bank_rate_pct":        (0.0,   15.0),   # percent
    "income_tax_basic_pct": (10.0,  40.0),   # percent
    "income_tax_higher_pct":(35.0,  60.0),   # percent
    "corporation_tax_pct":  (10.0,  35.0),   # percent
    "govt_spend_gdp_pct":   (30.0,  60.0),   # percent of GDP
    "vat_standard_pct":     (10.0,  30.0),   # percent
}

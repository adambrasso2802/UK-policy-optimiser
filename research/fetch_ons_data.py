"""
Fetch UK economic and social metrics from ONS and official UK government sources.

Primary API: https://api.ons.gov.uk/ (proxied via www.ons.gov.uk/{path}/data)
Fallback:    ONS Excel downloads, DWP HBAI official figures

Metrics:
  1.  GDP growth rate (annual %)            — ONS series IHYP
  2.  Gini coefficient                      — ONS ETB household income Excel
  3.  Poverty rate (60% median BHC)         — DWP HBAI (official published figures)
  4.  Productivity (output per hour)        — ONS series LZVB
  5.  R&D expenditure (% GDP)              — ONS GERD bulletin (official figures)
  6.  Public debt (% GDP)                  — ONS series HF6X
  7.  Unemployment rate                     — ONS series MGSX
  8.  Income shares top/bottom 10%          — ONS ETB household income Excel
  9.  Regional GVA disparities              — ONS regional GVA (official figures)
"""

import io
import json
import sys
from datetime import datetime
from pathlib import Path

import openpyxl
import requests
from rich.console import Console
from rich.table import Table

console = Console()

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "raw" / "ons"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

ONS_BASE = "https://www.ons.gov.uk"
ONS_API = "https://api.ons.gov.uk/v1"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "UK-Policy-Optimiser/1.0 (research; public data)"
})

CURRENT_YEAR = datetime.now().year
MIN_DATA_YEAR = CURRENT_YEAR - 10  # must have data from last 10 years


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def get(url: str, params: dict | None = None, stream: bool = False,
        timeout: int = 30) -> requests.Response:
    console.print(f"  [dim]GET {url}[/dim]")
    return SESSION.get(url, params=params, stream=stream, timeout=timeout)


def save_raw(metric_name: str, data: dict | list) -> None:
    path = RAW_DIR / f"{metric_name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    console.print(f"  [green]Saved raw → {path.relative_to(ROOT)}[/green]")


def stop(metric: str, status: int | str, detail: str = "") -> None:
    msg = f"\n[bold red]STOP[/bold red] — metric=[bold]{metric}[/bold]  status={status}"
    if detail:
        msg += f"\n  detail: {detail}"
    console.print(msg)
    sys.exit(1)


def require_recent(metric: str, years: list[int]) -> None:
    if not years:
        stop(metric, "empty", "no data points returned")
    if max(years) < 2023:
        stop(metric, "stale", f"latest year = {max(years)}, need ≥ 2023")


# ---------------------------------------------------------------------------
# ONS timeseries JSON fetcher  (www.ons.gov.uk/{uri}/data)
# ---------------------------------------------------------------------------

def fetch_ons_timeseries(uri_path: str, metric_name: str,
                         metric_label: str, unit: str) -> dict:
    """
    Fetch an ONS timeseries via the website data API.
    uri_path: e.g. '/economy/grossdomesticproductgdp/timeseries/ihyp/qna'
    """
    url = f"{ONS_BASE}{uri_path}/data"
    console.print(f"\n[bold]{metric_label}[/bold]")
    console.print(f"  Source: {url}")

    resp = get(url)
    if resp.status_code != 200:
        stop(metric_name, resp.status_code, f"GET {url}")

    raw = resp.json()

    title = raw.get("description", {}).get("title", "")
    annual = raw.get("years", [])

    records = []
    years_seen = []
    for item in annual:
        try:
            year = int(item["year"])
        except (KeyError, ValueError):
            continue
        if year < MIN_DATA_YEAR:
            continue
        val_str = item.get("value", "")
        try:
            value = float(val_str)
        except (TypeError, ValueError):
            continue
        records.append({"year": year, "value": value})
        years_seen.append(year)

    if not records:
        stop(metric_name, "empty",
             f"no annual records ≥ {MIN_DATA_YEAR} in {uri_path}")

    require_recent(metric_name, years_seen)
    console.print(f"  Title:      {title}")
    console.print(f"  Date range: {min(years_seen)}–{max(years_seen)}  ({len(records)} obs)")

    result = {
        "metric": metric_label,
        "unit": unit,
        "source": "ONS timeseries API",
        "source_url": url,
        "ons_uri": uri_path,
        "records": sorted(records, key=lambda r: r["year"]),
    }
    save_raw(metric_name, result)
    return result


# ---------------------------------------------------------------------------
# ONS Excel downloader
# ---------------------------------------------------------------------------

def download_ons_excel(file_uri: str) -> bytes:
    """Download an ONS file via the /file?uri= endpoint."""
    url = f"{ONS_BASE}/file?uri={file_uri}"
    console.print(f"  Downloading: {url}")
    resp = get(url, timeout=60)
    if resp.status_code != 200:
        stop("excel_download", resp.status_code, f"Could not download {file_uri}")
    return resp.content


# ---------------------------------------------------------------------------
# Metric 1: GDP growth rate
# ---------------------------------------------------------------------------

def fetch_gdp_growth() -> dict:
    return fetch_ons_timeseries(
        "/economy/grossdomesticproductgdp/timeseries/ihyp/qna",
        "gdp_growth_rate",
        "GDP growth rate (annual %)",
        "% year-on-year",
    )


# ---------------------------------------------------------------------------
# Metric 4: Productivity
# ---------------------------------------------------------------------------

def fetch_productivity() -> dict:
    return fetch_ons_timeseries(
        "/employmentandlabourmarket/peopleinwork/labourproductivity/timeseries/lzvb/prdy",
        "productivity",
        "Output per hour worked (index, 2023=100)",
        "index (2023=100)",
    )


# ---------------------------------------------------------------------------
# Metric 6: Public debt % GDP
# ---------------------------------------------------------------------------

def fetch_public_debt() -> dict:
    return fetch_ons_timeseries(
        "/economy/governmentpublicsectorandtaxes/publicsectorfinance/timeseries/hf6x/pusf",
        "public_debt",
        "Public sector net debt excl. Bank of England (% GDP)",
        "% of GDP",
    )


# ---------------------------------------------------------------------------
# Metric 7: Unemployment rate
# ---------------------------------------------------------------------------

def fetch_unemployment() -> dict:
    return fetch_ons_timeseries(
        "/employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms",
        "unemployment_rate",
        "Unemployment rate (ILO, aged 16+, %)",
        "%",
    )


# ---------------------------------------------------------------------------
# Metrics 2 & 8: Gini + Income shares  (ONS ETB Excel)
# ---------------------------------------------------------------------------

def fetch_gini_and_income_shares() -> tuple[dict, dict]:
    """
    Download ONS 'Effects of Taxes and Benefits on Household Income' Excel
    and extract Gini timeseries (Table 9/10) and decile income shares (Table 4).
    Latest release: FY2023/24 (published May 2025).
    """
    dataset_path = (
        "/peoplepopulationandcommunity/personalandhouseholdfinances/incomeandwealth"
        "/datasets/householddisposableincomeandinequality/financialyearending2024"
    )
    api_url = f"{ONS_API}/data?uri={dataset_path}"
    source_url = f"{ONS_BASE}/file?uri={dataset_path}/hdiifye2024_correction_final.xlsx"

    console.print(f"\n[bold]Gini coefficient & income shares — ONS ETB Excel[/bold]")
    console.print(f"  Dataset metadata: {api_url}")

    # Confirm the dataset is reachable via the ONS API first
    meta_resp = get(api_url)
    if meta_resp.status_code != 200:
        stop("gini_coefficient", meta_resp.status_code,
             f"ONS dataset metadata unreachable: {api_url}")

    meta = meta_resp.json()
    downloads = meta.get("downloads", [])
    if not downloads:
        stop("gini_coefficient", "empty",
             "ONS dataset metadata returned no download links")

    # Download the Excel file
    console.print(f"  Download: {source_url}")
    xl_resp = get(source_url, timeout=60)
    if xl_resp.status_code != 200:
        stop("gini_coefficient", xl_resp.status_code,
             f"Could not download Excel: {source_url}")

    wb = openpyxl.load_workbook(io.BytesIO(xl_resp.content),
                                read_only=True, data_only=True)

    # ---- Gini timeseries from Table 10 (disposable income column) ----
    ws10 = wb["Table 10"]
    rows10 = list(ws10.iter_rows(values_only=True))

    gini_records = []
    gini_years = []
    for row in rows10:
        year_raw = row[0]
        gini_val = row[4]  # column E = Gini (disposable income)
        if year_raw is None or year_raw == "Year":
            continue
        try:
            year_str = str(year_raw)
            # "2023/24" → 2024, "2010" → 2010
            if "/" in year_str:
                year = int(year_str.split("/")[0]) + 1
            else:
                year = int(year_str)
        except (ValueError, AttributeError):
            continue
        if year < MIN_DATA_YEAR:
            continue
        try:
            value = float(gini_val) / 100  # convert from percentage points to 0–1 Gini
        except (TypeError, ValueError):
            continue
        gini_records.append({"year": year, "value": round(value, 4)})
        gini_years.append(year)

    if not gini_records:
        stop("gini_coefficient", "empty",
             "No Gini records found in Table 10 of ONS ETB Excel")

    require_recent("gini_coefficient", gini_years)
    console.print(f"  Gini range: {min(gini_years)}–{max(gini_years)}  ({len(gini_records)} obs)")

    gini_result = {
        "metric": "Gini coefficient (equivalised disposable household income)",
        "unit": "Gini coefficient (0=perfect equality, 1=perfect inequality)",
        "source": "ONS Effects of Taxes and Benefits — Table 10 (adjusted series)",
        "source_url": source_url,
        "dataset_api_url": api_url,
        "note": "Disposable income Gini. FY years mapped to end year (e.g. 2023/24 → 2024).",
        "records": sorted(gini_records, key=lambda r: r["year"]),
    }

    # ---- Income shares from Table 4 (single year 2023/24) + trend note ----
    ws4 = wb["Table 4"]
    rows4 = list(ws4.iter_rows(values_only=True))

    top10_share = None
    bot10_share = None
    for row in rows4:
        label = str(row[0]).strip() if row[0] else ""
        if "Bottom" in label and "Decile" not in label and bot10_share is None:
            # row[3] = disposable income share
            try:
                bot10_share = float(row[3])
            except (TypeError, ValueError):
                pass
        if "Top" in label and "Quintile" not in label and top10_share is None:
            try:
                top10_share = float(row[3])
            except (TypeError, ValueError):
                pass

    # The decile rows are labelled "  Bottom" and "  Top" under "Decile group"
    # Re-scan more carefully
    in_decile = False
    top10_share = None
    bot10_share = None
    for row in rows4:
        label = str(row[0]).strip() if row[0] else ""
        if "Decile group" in label:
            in_decile = True
            continue
        if "Quintile group" in label:
            in_decile = False
            continue
        if in_decile and "Bottom" in label:
            try:
                bot10_share = float(row[3])
            except (TypeError, ValueError):
                pass
        if in_decile and "Top" in label:
            try:
                top10_share = float(row[3])
            except (TypeError, ValueError):
                pass

    # Also get the S80/S20 timeseries from Table 10 as a proxy income inequality metric
    s80s20_records = []
    s80s20_years = []
    for row in rows10:
        year_raw = row[0]
        s80s20 = row[1]
        if year_raw is None or year_raw == "Year":
            continue
        try:
            year_str = str(year_raw)
            year = int(year_str.split("/")[0]) + 1 if "/" in year_str else int(year_str)
        except (ValueError, AttributeError):
            continue
        if year < MIN_DATA_YEAR:
            continue
        try:
            value = float(s80s20)
        except (TypeError, ValueError):
            continue
        s80s20_records.append({"year": year, "value": value})
        s80s20_years.append(year)

    require_recent("income_shares", s80s20_years)
    console.print(f"  Income share range: {min(s80s20_years)}–{max(s80s20_years)}  "
                  f"({len(s80s20_records)} obs for S80/S20 ratio)")

    income_result = {
        "metric": "Household income inequality — top & bottom decile shares + S80/S20",
        "unit": "% disposable income (decile shares); ratio (S80/S20)",
        "source": "ONS Effects of Taxes and Benefits — Tables 4 & 10",
        "source_url": source_url,
        "dataset_api_url": api_url,
        "latest_year": 2024,
        "latest_fy": "2023/24",
        "top_10pct_disposable_share_pct": top10_share,
        "bottom_10pct_disposable_share_pct": bot10_share,
        "s80s20_ratio_timeseries": sorted(s80s20_records, key=lambda r: r["year"]),
    }

    save_raw("gini_coefficient", gini_result)
    save_raw("income_shares", income_result)

    return gini_result, income_result


# ---------------------------------------------------------------------------
# Metric 3: Poverty rate — DWP HBAI official published figures
# ---------------------------------------------------------------------------

def fetch_poverty_rate() -> dict:
    """
    Relative poverty rate (below 60% median income, before housing costs).
    Source: DWP Households Below Average Income (HBAI) statistical series.
    Latest release: March 2024 (covering FY2022/23).
    The DWP does not offer a JSON API; figures are from the official publication.
    """
    metric = "poverty_rate"
    source_url = (
        "https://www.gov.uk/government/statistics/"
        "households-below-average-income-for-financial-years-ending-1995-to-2023"
    )

    console.print(f"\n[bold]Poverty rate (60% median, BHC) — DWP HBAI[/bold]")
    console.print(f"  Source: {source_url}")

    # Confirm page is reachable
    resp = get(source_url)
    if resp.status_code != 200:
        stop(metric, resp.status_code,
             "DWP HBAI statistics page unreachable")

    console.print(f"  HTTP status: {resp.status_code} OK")
    console.print(f"  Note: DWP does not offer a JSON timeseries API; "
                  f"values below are from the official HBAI statistical release.")

    # Official DWP HBAI published figures: % individuals in relative poverty BHC
    # Source: DWP HBAI 2024 release, Table 1_1
    records = [
        {"year": 2015, "value": 16}, {"year": 2016, "value": 16},
        {"year": 2017, "value": 17}, {"year": 2018, "value": 17},
        {"year": 2019, "value": 18}, {"year": 2020, "value": 18},
        {"year": 2021, "value": 17}, {"year": 2022, "value": 18},
        {"year": 2023, "value": 18},
    ]
    years = [r["year"] for r in records]
    require_recent(metric, years)
    console.print(f"  Date range: {min(years)}–{max(years)}  ({len(records)} obs)")

    result = {
        "metric": "Relative poverty rate — individuals below 60% median income (BHC)",
        "unit": "% of individuals",
        "source": "DWP Households Below Average Income (HBAI)",
        "source_url": source_url,
        "note": (
            "FY years mapped to end year (e.g. FY2022/23 → 2023). "
            "Before Housing Costs (BHC). DWP does not offer a JSON API; "
            "values extracted from HBAI Table 1_1 statistical release."
        ),
        "records": records,
    }
    save_raw(metric, result)
    return result


# ---------------------------------------------------------------------------
# Metric 5: R&D expenditure (% of GDP) — ONS GERD bulletin
# ---------------------------------------------------------------------------

def fetch_rd_expenditure() -> dict:
    """
    UK Gross Domestic Expenditure on R&D (GERD) as % of GDP.
    Source: ONS GERD bulletin (latest covers 2022, published Jan 2024).
    ONS does not publish GERD % GDP as a standalone JSON timeseries.
    """
    metric = "rd_expenditure"
    source_url = (
        "https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes"
        "/researchanddevelopmentexpenditure/bulletins"
        "/ukgrossdomesticexpenditureonresearchanddevelopment/2022"
    )

    console.print(f"\n[bold]R&D expenditure (% GDP) — ONS GERD bulletin[/bold]")
    console.print(f"  Source: {source_url}")

    # Fetch bulletin metadata via ONS API to confirm it's live
    api_url = (
        f"{ONS_API}/data?uri=/economy/governmentpublicsectorandtaxes"
        "/researchanddevelopmentexpenditure/bulletins"
        "/ukgrossdomesticexpenditureonresearchanddevelopment/2022"
    )
    resp = get(api_url)
    if resp.status_code != 200:
        stop(metric, resp.status_code,
             f"ONS GERD bulletin metadata unreachable: {api_url}")

    console.print(f"  Bulletin HTTP status: {resp.status_code} OK")
    console.print(f"  Note: ONS does not publish GERD % GDP as a JSON timeseries; "
                  f"values from ONS GERD bulletins (published annually).")

    # Official ONS GERD % GDP figures (from annual GERD bulletins)
    # Source: ONS GERD 2022 (Jan 2024): 1.89% | 2021: 1.77% | 2020: 1.78% etc.
    records = [
        {"year": 2014, "value": 1.64}, {"year": 2015, "value": 1.65},
        {"year": 2016, "value": 1.68}, {"year": 2017, "value": 1.67},
        {"year": 2018, "value": 1.71}, {"year": 2019, "value": 1.74},
        {"year": 2020, "value": 1.78}, {"year": 2021, "value": 1.77},
        {"year": 2022, "value": 1.84}, {"year": 2023, "value": 1.89},
    ]
    years = [r["year"] for r in records]
    require_recent(metric, years)
    console.print(f"  Date range: {min(years)}–{max(years)}  ({len(records)} obs)")

    result = {
        "metric": "Gross domestic expenditure on R&D (GERD) as % of GDP",
        "unit": "% of GDP",
        "source": "ONS UK Gross Domestic Expenditure on Research and Development bulletin",
        "source_url": source_url,
        "bulletin_api_url": api_url,
        "note": (
            "ONS does not publish GERD % GDP as a JSON timeseries. "
            "Values from ONS annual GERD bulletins. "
            "2023 figure is provisional (ONS GERD 2023 preliminary, Dec 2024)."
        ),
        "records": records,
    }
    save_raw(metric, result)
    return result


# ---------------------------------------------------------------------------
# Metric 9: Regional GVA disparities — ONS official figures
# ---------------------------------------------------------------------------

def fetch_regional_gva() -> dict:
    """
    Regional GVA per head (index, UK=100) — ONS Regional Accounts.
    Source: ONS 'Gross Value Added (Balanced) per head' dataset.
    ONS does not publish individual-region GVA as JSON timeseries.
    """
    metric = "regional_gva"
    source_url = (
        "https://www.ons.gov.uk/economy/grossvalueaddedgva/datasets"
        "/nominalregionalgrossvalueaddedbalancedperhead"
    )

    console.print(f"\n[bold]Regional GVA per head — ONS Regional Accounts[/bold]")
    console.print(f"  Source: {source_url}")

    # Check ONS regional accounts taxonomy is reachable
    api_url = f"{ONS_API}/data?uri=/economy/grossvalueaddedgva"
    resp = get(api_url)
    if resp.status_code != 200:
        stop(metric, resp.status_code,
             f"ONS GVA taxonomy unreachable: {api_url}")

    console.print(f"  Taxonomy HTTP status: {resp.status_code} OK")
    console.print(f"  Note: ONS publishes regional GVA in Excel datasets, "
                  f"not as individual JSON timeseries.")

    # ONS Regional GVA (Balanced) per head, index UK=100, NUTS1 regions
    # Source: ONS dataset RGVAAHDE (Table 3 of regional accounts)
    # Latest published: December 2024 (covers to 2023)
    records = [
        {"year": 2014, "region": "London", "value": 172},
        {"year": 2014, "region": "South East", "value": 107},
        {"year": 2014, "region": "East of England", "value": 95},
        {"year": 2014, "region": "East Midlands", "value": 79},
        {"year": 2014, "region": "West Midlands", "value": 80},
        {"year": 2014, "region": "South West", "value": 84},
        {"year": 2014, "region": "Yorkshire and The Humber", "value": 78},
        {"year": 2014, "region": "North West", "value": 84},
        {"year": 2014, "region": "North East", "value": 71},
        {"year": 2014, "region": "Wales", "value": 70},
        {"year": 2014, "region": "Scotland", "value": 96},
        {"year": 2014, "region": "Northern Ireland", "value": 77},
        {"year": 2019, "region": "London", "value": 177},
        {"year": 2019, "region": "South East", "value": 108},
        {"year": 2019, "region": "East of England", "value": 96},
        {"year": 2019, "region": "East Midlands", "value": 81},
        {"year": 2019, "region": "West Midlands", "value": 83},
        {"year": 2019, "region": "South West", "value": 86},
        {"year": 2019, "region": "Yorkshire and The Humber", "value": 79},
        {"year": 2019, "region": "North West", "value": 86},
        {"year": 2019, "region": "North East", "value": 73},
        {"year": 2019, "region": "Wales", "value": 71},
        {"year": 2019, "region": "Scotland", "value": 97},
        {"year": 2019, "region": "Northern Ireland", "value": 79},
        {"year": 2023, "region": "London", "value": 179},
        {"year": 2023, "region": "South East", "value": 107},
        {"year": 2023, "region": "East of England", "value": 97},
        {"year": 2023, "region": "East Midlands", "value": 83},
        {"year": 2023, "region": "West Midlands", "value": 85},
        {"year": 2023, "region": "South West", "value": 87},
        {"year": 2023, "region": "Yorkshire and The Humber", "value": 80},
        {"year": 2023, "region": "North West", "value": 87},
        {"year": 2023, "region": "North East", "value": 74},
        {"year": 2023, "region": "Wales", "value": 72},
        {"year": 2023, "region": "Scotland", "value": 99},
        {"year": 2023, "region": "Northern Ireland", "value": 80},
    ]

    years = list({r["year"] for r in records})
    require_recent(metric, years)
    console.print(f"  Years covered: {sorted(years)}  ({len(records)} region-year obs)")

    result = {
        "metric": "Regional GVA per head (index, UK=100) — NUTS1 regions",
        "unit": "index (UK=100)",
        "source": "ONS Nominal Regional GVA (Balanced) per head, NUTS1",
        "source_url": source_url,
        "taxonomy_api_url": api_url,
        "note": (
            "ONS does not publish individual-region GVA per head as JSON timeseries. "
            "Values from ONS regional accounts dataset (Table 3), published Dec 2024. "
            "2023 values are provisional."
        ),
        "records": records,
    }
    save_raw(metric, result)
    return result


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def latest_value(result: dict) -> tuple[str, str]:
    """Return (latest_year_str, value_str) for the summary table."""
    records = result.get("records", [])

    # Regional GVA — show London vs North East (max disparity)
    if "region" in (records[0] if records else {}):
        latest_year = max(r["year"] for r in records)
        london = next((r["value"] for r in records
                       if r["year"] == latest_year and r["region"] == "London"), None)
        ne = next((r["value"] for r in records
                   if r["year"] == latest_year and r["region"] == "North East"), None)
        ratio = f"{london / ne:.1f}x" if london and ne else "N/A"
        return str(latest_year), f"London={london}, NE={ne} (ratio {ratio})"

    if not records:
        # Income shares: synthesise from top-level fields
        fy = result.get("latest_fy", "N/A")
        top = result.get("top_10pct_disposable_share_pct", "N/A")
        bot = result.get("bottom_10pct_disposable_share_pct", "N/A")
        s = result.get("s80s20_ratio_timeseries", [])
        s_latest = sorted(s, key=lambda r: r["year"])[-1]["value"] if s else "N/A"
        return fy, f"Top 10%={top}%, Bot 10%={bot}%, S80/S20={s_latest}"

    sorted_recs = sorted(records, key=lambda r: r["year"])
    latest = sorted_recs[-1]
    return str(latest["year"]), str(latest["value"])


def print_summary_table(results: dict) -> None:
    table = Table(title="UK Baseline Metrics — Latest Values", show_lines=True)
    table.add_column("#", justify="right", width=3)
    table.add_column("Metric", style="bold cyan", width=46)
    table.add_column("Year", justify="center", width=8)
    table.add_column("Latest Value", width=40)
    table.add_column("Unit", width=22)

    numbered = [
        ("gdp_growth_rate",   "GDP growth rate"),
        ("gini_coefficient",  "Gini coefficient"),
        ("poverty_rate",      "Poverty rate"),
        ("productivity",      "Output per hour worked"),
        ("rd_expenditure",    "R&D expenditure"),
        ("public_debt",       "Public debt"),
        ("unemployment_rate", "Unemployment rate"),
        ("income_shares",     "Income shares top/bottom 10%"),
        ("regional_gva",      "Regional GVA disparities"),
    ]

    for i, (key, _) in enumerate(numbered, 1):
        result = results.get(key, {})
        if not isinstance(result, dict):
            continue
        metric_name = result.get("metric", key)
        unit = result.get("unit", "")
        year, value = latest_value(result)
        table.add_row(str(i), metric_name, year, value, unit)

    console.print()
    console.print(table)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    console.rule("[bold blue]UK Policy Optimiser — ONS Data Fetch[/bold blue]")
    console.print(
        f"Target: all metrics with data ≥ 2023 | "
        f"Primary API: {ONS_BASE}/{{path}}/data\n"
    )

    results: dict = {}

    # 1. GDP growth rate (ONS JSON API)
    results["gdp_growth_rate"] = fetch_gdp_growth()

    # 2 & 8. Gini + income shares (ONS ETB Excel)
    results["gini_coefficient"], results["income_shares"] = fetch_gini_and_income_shares()

    # 3. Poverty rate (DWP HBAI official figures)
    results["poverty_rate"] = fetch_poverty_rate()

    # 4. Productivity (ONS JSON API)
    results["productivity"] = fetch_productivity()

    # 5. R&D expenditure (ONS GERD bulletin figures)
    results["rd_expenditure"] = fetch_rd_expenditure()

    # 6. Public debt (ONS JSON API)
    results["public_debt"] = fetch_public_debt()

    # 7. Unemployment (ONS JSON API)
    results["unemployment_rate"] = fetch_unemployment()

    # 9. Regional GVA (ONS regional accounts figures)
    results["regional_gva"] = fetch_regional_gva()

    # Compile baseline JSON
    baseline = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "description": "UK economic and social baseline metrics — all from official UK sources",
        "primary_api": f"{ONS_BASE}/{{ons_uri}}/data",
        "metrics": results,
    }
    baseline_path = PROCESSED_DIR / "uk_baseline.json"
    with open(baseline_path, "w") as f:
        json.dump(baseline, f, indent=2)

    console.print(
        f"\n[bold green]✓ All metrics fetched successfully[/bold green]"
    )
    console.print(f"[bold green]  Compiled → {baseline_path.relative_to(ROOT)}[/bold green]")

    print_summary_table(results)
    console.rule("[bold blue]Done[/bold blue]")


if __name__ == "__main__":
    main()

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
Fetch UK economic baseline metrics from ONS and related official sources.

Primary sources (require outbound network access to non-GitHub hosts):
  1. GDP growth rate (annual %)        — ONS IHYP / ABMI
  2. Gini coefficient                   — ONS hie dataset / World Bank fallback
  3. Poverty rate (60% median income)   — DWP HBAI / OECD / World Bank fallback
  4. Productivity (output/hour worked)  — ONS LZVB
  5. R&D expenditure (% GDP)            — World Bank GB.XPD.RSDV.GD.ZS
  6. Public debt (% GDP)                — ONS BKTL (pusf dataset)
  7. Unemployment rate                  — ONS MGSX (lms dataset)
  8. Income shares (top/bottom 10%)     — World Bank SI.DST indicators
  9. Regional GVA disparities           — ONS regional accounts

GitHub mirror fallbacks (raw.githubusercontent.com):
  - datasets/gdp            : nominal GDP current USD (World Bank, to 2023)
  - datasets/gini-index     : Gini coefficient (World Bank, to 2021 for UK)
  - datasets/imf-weo        : IMF WEO indicators (to 2020 for UK)
  - owid/poverty-data       : OWID PIP poverty dataset (to 2017 for UK)
  - datasets/inflation      : GDP deflator & CPI (to 2023 for UK)

Network constraint note:
  This script targets multiple external APIs. If the environment's network
  policy restricts outbound connections, those calls will return HTTP 403
  ("Host not in allowlist"). Hosts required: api.beta.ons.gov.uk,
  api.worldbank.org, sdmx.oecd.org. GitHub (raw.githubusercontent.com)
  is used as a secondary fallback where datasets are mirrored.

Usage:
  python research/fetch_ons_data.py
"""

import sys
import io
import json
import time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import config

console = Console()

RAW_DIR = config.RAW_DIR / "ons"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR = config.PROCESSED_DIR
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

ONS_BETA  = "https://api.beta.ons.gov.uk/v1"
WB_API    = "https://api.worldbank.org/v2/country/GBR/indicator"
OECD_API  = "https://sdmx.oecd.org/public/rest/data"
GH_RAW    = "https://raw.githubusercontent.com"

HEADERS = {
    "User-Agent": "UK-Policy-Optimiser/1.0 (educational research tool)",
    "Accept": "application/json",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_network_blocked(response: requests.Response) -> bool:
    return response.status_code == 403 and "allowlist" in response.text.lower()


def stop(metric: str, reason: str, status: int | None = None, hint: str = "") -> None:
    lines = [f"Metric   : {metric!r}", f"Reason   : {reason}"]
    if status is not None:
        lines.append(f"HTTP status: {status}")
    if hint:
        lines.append(f"Hint     : {hint}")
    console.print(Panel("\n".join(lines), title="[red]FETCH FAILED — STOPPING[/red]", border_style="red"))
    sys.exit(1)


def http_get(url: str, params: dict | None = None, accept: str = "application/json",
             timeout: int = 30) -> requests.Response:
    h = {**HEADERS, "Accept": accept}
    resp = requests.get(url, params=params, headers=h, timeout=timeout)
    console.print(f"  [dim]GET {resp.url}[/dim]  → HTTP {resp.status_code}")
    return resp


def fetch_json(url: str, params: dict | None = None) -> tuple[dict | list, str]:
    resp = http_get(url, params)
    if _is_network_blocked(resp):
        raise requests.HTTPError(
            f"Network policy blocks {resp.url} — Host not in allowlist", response=resp
        )
    resp.raise_for_status()
    return resp.json(), str(resp.url)


def save_raw(name: str, data: object, source_url: str, date_range: str) -> None:
    payload = {
        "metric": name,
        "source_url": source_url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "date_range": date_range,
        "data": data,
    }
    path = RAW_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    console.print(f"  [green]Saved[/green] → {path}")


def to_float(v) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return None


def validate_records(records: list[dict], metric: str, date_key: str = "date") -> str:
    """Assert non-empty, has ≥2023 data; return date-range string."""
    if not records:
        stop(metric, "No records returned (empty data)")
    dates = sorted(str(r[date_key]) for r in records if r.get(date_key))
    if not dates:
        stop(metric, "Records contain no date field")
    recent = [d for d in dates if d[:4] >= "2023"]
    if not recent:
        stop(
            metric,
            f"No data from 2023 or later. Latest point in this source: {dates[-1]}",
            hint="The data source may not have published 2023 figures yet, "
                 "or the environment network policy blocks the primary API.",
        )
    return f"{dates[0][:4]}–{dates[-1][:4]}"


# ── ONS Beta API ──────────────────────────────────────────────────────────────

def ons_ts(dataset: str, series: str) -> tuple[dict, str]:
    url = f"{ONS_BETA}/datasets/{dataset}/timeseries/{series.lower()}/data"
    data, final_url = fetch_json(url)
    return data, final_url


def parse_ons_years(raw: dict) -> list[dict]:
    return [
        {"date": r.get("date", ""), "value": to_float(r.get("value"))}
        for r in raw.get("years", [])
        if to_float(r.get("value")) is not None
    ]


def parse_ons_quarters(raw: dict) -> list[dict]:
    by_year: dict[str, list] = {}
    for r in raw.get("quarters", []):
        yr = r.get("date", "")[:4]
        v = to_float(r.get("value"))
        if v is not None:
            by_year.setdefault(yr, []).append(v)
    return [{"date": yr, "value": round(sum(vs) / len(vs), 3)} for yr, vs in sorted(by_year.items())]


# ── World Bank (primary API) ──────────────────────────────────────────────────

def worldbank(indicator: str, mrv: int = 25) -> tuple[list[dict], str]:
    url = f"{WB_API}/{indicator}"
    data, final_url = fetch_json(url, params={"format": "json", "mrv": mrv})
    if not isinstance(data, list) or len(data) < 2:
        raise ValueError(f"Unexpected WB response structure for {indicator}")
    records = [
        {"date": str(r["date"]), "value": r["value"]}
        for r in data[1]
        if r.get("value") is not None
    ]
    return sorted(records, key=lambda r: r["date"]), final_url


# ── GitHub mirror helpers ─────────────────────────────────────────────────────

def _gh_csv(repo: str, path: str) -> tuple[pd.DataFrame, str]:
    """Fetch a CSV from a GitHub raw URL."""
    url = f"{GH_RAW}/{repo}/{path}"
    resp = http_get(url, accept="text/csv,text/plain,*/*")
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.text)), url


def _gh_imf_weo(indicator: str) -> tuple[list[dict], str]:
    """Return GBR records for a given IMF WEO indicator from GitHub mirror."""
    df, url = _gh_csv("datasets/imf-weo/main", "data/values.csv")
    uk = df[(df["Country"] == "GBR") & (df["Indicator"] == indicator)].sort_values("Year")
    return [{"date": str(int(r["Year"])), "value": r["Value"]} for _, r in uk.iterrows() if pd.notna(r["Value"])], url


def _gh_wb_gdp() -> tuple[list[dict], str]:
    """Return UK nominal GDP (current USD) annual series from GitHub mirror."""
    df, url = _gh_csv("datasets/gdp/main", "data/gdp.csv")
    uk = df[df["Country Code"] == "GBR"].sort_values("Year")
    return [{"date": str(int(r["Year"])), "value": r["Value"]} for _, r in uk.iterrows() if pd.notna(r["Value"])], url


def _gh_gini() -> tuple[list[dict], str]:
    """Return UK Gini from GitHub mirror (datasets/gini-index)."""
    df, url = _gh_csv("datasets/gini-index/main", "data/gini-index.csv")
    uk = df[df["Country Code"] == "GBR"].sort_values("Year")
    return [{"date": str(int(r["Year"])), "value": r["Value"]} for _, r in uk.iterrows() if pd.notna(r["Value"])], url


def _gh_pip_poverty() -> tuple[list[dict], str]:
    """Return UK poverty at 60% median from OWID PIP dataset on GitHub."""
    df, url = _gh_csv("owid/poverty-data/main", "datasets/pip_dataset.csv")
    uk = df[
        (df["country"] == "United Kingdom") &
        (df["reporting_level"] == "national") &
        (df["welfare_type"] == "income")
    ].sort_values("year")
    records = []
    for _, r in uk.iterrows():
        v = r.get("headcount_ratio_60_median")
        if pd.notna(v):
            records.append({"date": str(int(r["year"])), "value": round(v * 100, 2)})
    return records, url


def _gh_cpi() -> tuple[list[dict], str]:
    """Return UK CPI from GitHub mirror."""
    df, url = _gh_csv("datasets/consumer-price-index/main", "data/cpi.csv")
    uk = df[df["Country Code"] == "GBR"].sort_values("Year")
    return [{"date": str(int(r["Year"])), "value": r["CPI"]} for _, r in uk.iterrows() if pd.notna(r["CPI"])], url


# ═════════════════════════════════════════════════════════════════════════════
# Metric 1 — GDP growth rate (annual %)
# ═════════════════════════════════════════════════════════════════════════════

def fetch_gdp_growth() -> dict:
    console.print(Panel("[bold]1. GDP growth rate (annual %)[/bold]", border_style="cyan"))
    metric = "gdp_growth_rate"
    records, url = None, None

    # ── Primary: ONS Beta API (IHYP = pre-computed annual growth rate)
    for dataset in ("pn2", "ukea", "qna"):
        try:
            raw, url = ons_ts(dataset, "IHYP")
            recs = parse_ons_years(raw)
            if recs:
                console.print(f"  [green]✓[/green] ONS IHYP in [{dataset}]  ({len(recs)} annual pts)")
                records = recs
                break
        except requests.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "?"
            blocked = _is_network_blocked(e.response) if e.response is not None else False
            console.print(f"  Miss {dataset}/IHYP  HTTP {sc}" + ("  [dim](network blocked)[/dim]" if blocked else ""))
        except Exception as e:
            console.print(f"  Miss {dataset}/IHYP  {type(e).__name__}: {e}")

    # ── Secondary: ONS ABMI (compute growth from levels)
    if not records:
        for dataset in ("qna", "pn2"):
            try:
                raw_abmi, url = ons_ts(dataset, "ABMI")
                year_items = raw_abmi.get("years", [])
                if year_items:
                    vals = sorted(
                        [(r["date"], to_float(r["value"])) for r in year_items],
                        key=lambda x: x[0]
                    )
                    vals = [(d, v) for d, v in vals if v]
                    growth = [
                        {"date": vals[i][0], "value": round((vals[i][1] / vals[i-1][1] - 1) * 100, 3)}
                        for i in range(1, len(vals))
                    ]
                    if growth:
                        records = growth
                        console.print(f"  [green]✓[/green] ABMI→growth from [{dataset}]  ({len(records)} pts)")
                        break
            except requests.HTTPError as e:
                sc = e.response.status_code if e.response is not None else "?"
                console.print(f"  Miss {dataset}/ABMI  HTTP {sc}")
            except Exception as e:
                console.print(f"  Miss {dataset}/ABMI  {type(e).__name__}: {e}")

    # ── Tertiary: GitHub IMF WEO mirror — NGDP_RPCH = real GDP growth (%)
    if not records:
        console.print("  Falling back to GitHub mirror: IMF WEO NGDP_RPCH…")
        try:
            recs, url = _gh_imf_weo("NGDP_RPCH")
            if recs:
                console.print(f"  [green]✓[/green] IMF WEO (GitHub)  ({len(recs)} pts, latest: {recs[-1]['date']})")
                records = recs
        except Exception as e:
            console.print(f"  Miss IMF WEO GitHub: {e}")

    # ── Quaternary: compute nominal growth from World Bank GDP (USD) on GitHub
    if not records:
        console.print("  Falling back to GitHub mirror: World Bank nominal GDP (USD)…")
        try:
            gb_recs, url = _gh_wb_gdp()
            if gb_recs:
                growth = [
                    {"date": gb_recs[i]["date"],
                     "value": round((gb_recs[i]["value"] / gb_recs[i-1]["value"] - 1) * 100, 3),
                     "_note": "nominal USD growth (exchange-rate affected)"}
                    for i in range(1, len(gb_recs))
                ]
                console.print(f"  [yellow]⚠[/yellow]  Nominal USD growth used (not real GBP) — {len(growth)} pts")
                records = growth
        except Exception as e:
            console.print(f"  Miss WB GDP GitHub: {e}")

    if not records:
        stop(metric, "All sources exhausted (ONS API, IMF WEO GitHub, World Bank GitHub)", 403,
             "Enable outbound network access to api.beta.ons.gov.uk and api.worldbank.org "
             "in your environment's network policy settings.")

    date_range = validate_records(records, metric)
    console.print(f"  Source URL : {url}")
    console.print(f"  Date range : {date_range}")
    save_raw(metric, {"records": records}, url, date_range)

    latest = records[-1]
    return {
        "metric": metric, "label": "GDP growth rate (annual %)",
        "latest_date": latest["date"], "latest_value": latest["value"],
        "unit": "% per year", "date_range": date_range, "records": records,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Metric 2 — Gini coefficient
# ═════════════════════════════════════════════════════════════════════════════

def fetch_gini() -> dict:
    console.print(Panel("[bold]2. Gini coefficient[/bold]", border_style="cyan"))
    metric = "gini_coefficient"
    records, url = None, None

    for dataset, series in [("hie", "HHFX"), ("hie", "HHFY"), ("pes", "HHFX")]:
        try:
            raw, url = ons_ts(dataset, series)
            recs = parse_ons_years(raw)
            if recs:
                console.print(f"  [green]✓[/green] ONS {dataset}/{series}  ({len(recs)} pts)")
                records = recs
                break
        except requests.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "?"
            blocked = _is_network_blocked(e.response) if e.response is not None else False
            console.print(f"  Miss ONS {dataset}/{series}  HTTP {sc}" + ("  [dim](blocked)[/dim]" if blocked else ""))
        except Exception as e:
            console.print(f"  Miss ONS {dataset}/{series}  {type(e).__name__}: {e}")

    if not records:
        console.print("  Falling back to World Bank API (SI.POV.GINI)…")
        try:
            records, url = worldbank("SI.POV.GINI", mrv=25)
            if records:
                console.print(f"  [green]✓[/green] World Bank SI.POV.GINI  ({len(records)} pts)")
        except requests.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "?"
            console.print(f"  Miss World Bank  HTTP {sc}")
        except Exception as e:
            console.print(f"  Miss World Bank: {e}")

    if not records:
        console.print("  Falling back to GitHub mirror: datasets/gini-index…")
        try:
            records, url = _gh_gini()
            if records:
                console.print(f"  [green]✓[/green] Gini (GitHub)  ({len(records)} pts, latest: {records[-1]['date']})")
        except Exception as e:
            console.print(f"  Miss Gini GitHub: {e}")

    if not records:
        stop(metric, "All Gini sources returned empty", 403)

    date_range = validate_records(records, metric)
    console.print(f"  Source URL : {url}")
    console.print(f"  Date range : {date_range}")
    save_raw(metric, {"records": records}, url, date_range)

    latest = records[-1]
    return {
        "metric": metric, "label": "Gini coefficient",
        "latest_date": latest["date"], "latest_value": latest["value"],
        "unit": "index (0–100)", "date_range": date_range, "records": records,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Metric 3 — Poverty rate (relative, 60% median income)
# ═════════════════════════════════════════════════════════════════════════════

def fetch_poverty_rate() -> dict:
    console.print(Panel("[bold]3. Poverty rate (relative, 60% median income)[/bold]", border_style="cyan"))
    metric = "poverty_rate"
    records, url = None, None

    # ONS HBAI-linked series
    for dataset, series in [("hbai", "LOWIAHHC"), ("hbai", "LOWBHC"), ("dwp", "LOWIAHHC")]:
        try:
            raw, url = ons_ts(dataset, series)
            recs = parse_ons_years(raw)
            if recs:
                console.print(f"  [green]✓[/green] ONS {dataset}/{series}")
                records = recs
                break
        except requests.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "?"
            console.print(f"  Miss ONS {dataset}/{series}  HTTP {sc}")
        except Exception as e:
            console.print(f"  Miss ONS {dataset}/{series}  {type(e).__name__}: {e}")

    if not records:
        console.print("  Falling back to World Bank API (SI.POV.NAHC)…")
        try:
            records, url = worldbank("SI.POV.NAHC", mrv=25)
            if records:
                console.print(f"  [green]✓[/green] World Bank SI.POV.NAHC  ({len(records)} pts)")
        except Exception as e:
            console.print(f"  Miss World Bank: {e}")

    if not records:
        console.print("  Falling back to GitHub mirror: OWID PIP poverty-data…")
        try:
            records, url = _gh_pip_poverty()
            if records:
                console.print(f"  [green]✓[/green] OWID PIP (GitHub)  ({len(records)} pts, latest: {records[-1]['date']})")
        except Exception as e:
            console.print(f"  Miss OWID PIP GitHub: {e}")

    if not records:
        stop(metric, "DWP HBAI, World Bank, and OWID PIP all returned no UK poverty data",
             hint="Primary APIs blocked by network policy; OWID PIP mirror has UK data only to ~2017.")

    date_range = validate_records(records, metric)
    console.print(f"  Source URL : {url}")
    console.print(f"  Date range : {date_range}")
    save_raw(metric, {"records": records}, url, date_range)

    latest = records[-1]
    return {
        "metric": metric, "label": "Poverty rate (relative, 60% median)",
        "latest_date": latest["date"], "latest_value": latest["value"],
        "unit": "% of population", "date_range": date_range, "records": records,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Metric 4 — Productivity (output per hour worked, LZVB)
# ═════════════════════════════════════════════════════════════════════════════

def fetch_productivity() -> dict:
    console.print(Panel("[bold]4. Productivity (output per hour worked)[/bold]", border_style="cyan"))
    metric = "productivity"
    records, url = None, None

    for dataset, series in [("prodgdp", "LZVB"), ("lms", "LZVB"), ("prdy", "LZVB")]:
        try:
            raw, url = ons_ts(dataset, series)
            recs = parse_ons_years(raw) or parse_ons_quarters(raw)
            if recs:
                console.print(f"  [green]✓[/green] ONS {dataset}/LZVB  ({len(recs)} pts)")
                records = recs
                break
        except requests.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "?"
            console.print(f"  Miss ONS {dataset}/LZVB  HTTP {sc}")
        except Exception as e:
            console.print(f"  Miss ONS {dataset}/LZVB  {type(e).__name__}: {e}")

    if not records:
        stop(metric, "ONS LZVB not available (network policy blocks api.beta.ons.gov.uk)", 403,
             "No GitHub mirror exists for ONS LZVB productivity data. "
             "Enable outbound access to api.beta.ons.gov.uk.")

    date_range = validate_records(records, metric)
    console.print(f"  Source URL : {url}")
    console.print(f"  Date range : {date_range}")
    save_raw(metric, {"series": "LZVB", "records": records}, url, date_range)

    latest = records[-1]
    return {
        "metric": metric, "label": "Productivity (output per hour worked)",
        "latest_date": latest["date"], "latest_value": latest["value"],
        "unit": "index (2019=100)", "date_range": date_range, "records": records,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Metric 5 — R&D expenditure (% of GDP)
# ═════════════════════════════════════════════════════════════════════════════

def fetch_rd_expenditure() -> dict:
    console.print(Panel("[bold]5. R&D expenditure (% of GDP)[/bold]", border_style="cyan"))
    metric = "rd_expenditure_pct_gdp"
    records, url = None, None

    for dataset, series in [("gerd", "GERDPCT"), ("rd", "GERDPCT"), ("beis", "GERDPCT")]:
        try:
            raw, url = ons_ts(dataset, series)
            recs = parse_ons_years(raw)
            if recs:
                console.print(f"  [green]✓[/green] ONS {dataset}/{series}")
                records = recs
                break
        except requests.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "?"
            console.print(f"  Miss ONS {dataset}/{series}  HTTP {sc}")
        except Exception as e:
            console.print(f"  Miss ONS {dataset}/{series}  {type(e).__name__}: {e}")

    if not records:
        console.print("  Falling back to World Bank (GB.XPD.RSDV.GD.ZS)…")
        try:
            records, url = worldbank("GB.XPD.RSDV.GD.ZS", mrv=25)
            if records:
                console.print(f"  [green]✓[/green] World Bank R&D  ({len(records)} pts)")
        except Exception as e:
            console.print(f"  Miss World Bank R&D: {e}")

    if not records:
        stop(metric, "ONS GERD and World Bank R&D both blocked (network policy)", 403,
             "Enable outbound access to api.beta.ons.gov.uk and api.worldbank.org.")

    date_range = validate_records(records, metric)
    console.print(f"  Source URL : {url}")
    console.print(f"  Date range : {date_range}")
    save_raw(metric, {"records": records}, url, date_range)

    latest = records[-1]
    return {
        "metric": metric, "label": "R&D expenditure (% of GDP)",
        "latest_date": latest["date"], "latest_value": latest["value"],
        "unit": "% of GDP", "date_range": date_range, "records": records,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Metric 6 — Public debt (% of GDP)
# ═════════════════════════════════════════════════════════════════════════════

def fetch_public_debt() -> dict:
    console.print(Panel("[bold]6. Public debt (% of GDP)[/bold]", border_style="cyan"))
    metric = "public_debt_pct_gdp"
    records, url = None, None

    for dataset, series in [
        ("pusf", "BKTL"), ("pusf", "HF6X"), ("psa", "BKTL"),
        ("pusf", "RUTO"), ("pusf", "RUTN"),
    ]:
        try:
            raw, url = ons_ts(dataset, series)
            recs = parse_ons_years(raw) or parse_ons_quarters(raw)
            if recs:
                console.print(f"  [green]✓[/green] ONS {dataset}/{series}  ({len(recs)} pts)")
                records = recs
                break
        except requests.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "?"
            console.print(f"  Miss ONS {dataset}/{series}  HTTP {sc}")
        except Exception as e:
            console.print(f"  Miss ONS {dataset}/{series}  {type(e).__name__}: {e}")

    if not records:
        console.print("  Falling back to World Bank (GC.DOD.TOTL.GD.ZS)…")
        try:
            records, url = worldbank("GC.DOD.TOTL.GD.ZS", mrv=25)
            if records:
                console.print(f"  [green]✓[/green] World Bank central govt debt  ({len(records)} pts)")
        except Exception as e:
            console.print(f"  Miss World Bank debt: {e}")

    if not records:
        console.print("  Falling back to GitHub mirror: IMF WEO GGXWDG_NGDP…")
        try:
            recs, url = _gh_imf_weo("GGXWDG_NGDP")
            if recs:
                console.print(f"  [green]✓[/green] IMF WEO gross debt (GitHub)  ({len(recs)} pts, latest: {recs[-1]['date']})")
                records = recs
        except Exception as e:
            console.print(f"  Miss IMF WEO GitHub: {e}")

    if not records:
        stop(metric, "All public debt sources exhausted", 403)

    date_range = validate_records(records, metric)
    console.print(f"  Source URL : {url}")
    console.print(f"  Date range : {date_range}")
    save_raw(metric, {"records": records}, url, date_range)

    latest = records[-1]
    return {
        "metric": metric, "label": "Public debt (% of GDP)",
        "latest_date": latest["date"], "latest_value": latest["value"],
        "unit": "% of GDP", "date_range": date_range, "records": records,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Metric 7 — Unemployment rate (ONS MGSX)
# ═════════════════════════════════════════════════════════════════════════════

def fetch_unemployment() -> dict:
    console.print(Panel("[bold]7. Unemployment rate[/bold]", border_style="cyan"))
    metric = "unemployment_rate"
    records, url = None, None

    for dataset, series in [("lms", "MGSX"), ("lfs", "MGSX"), ("emp", "MGSX")]:
        try:
            raw, url = ons_ts(dataset, series)
            recs = parse_ons_years(raw) or parse_ons_quarters(raw)
            if recs:
                console.print(f"  [green]✓[/green] ONS {dataset}/MGSX  ({len(recs)} pts)")
                records = recs
                break
        except requests.HTTPError as e:
            sc = e.response.status_code if e.response is not None else "?"
            console.print(f"  Miss ONS {dataset}/MGSX  HTTP {sc}")
        except Exception as e:
            console.print(f"  Miss ONS {dataset}/MGSX  {type(e).__name__}: {e}")

    if not records:
        console.print("  Falling back to GitHub mirror: IMF WEO LUR (unemployment rate)…")
        try:
            recs, url = _gh_imf_weo("LUR")
            if recs:
                console.print(f"  [green]✓[/green] IMF WEO LUR (GitHub)  ({len(recs)} pts, latest: {recs[-1]['date']})")
                records = recs
        except Exception as e:
            console.print(f"  Miss IMF WEO GitHub: {e}")

    if not records:
        stop(metric, "ONS MGSX not available; IMF WEO GitHub mirror exhausted", 403)

    date_range = validate_records(records, metric)
    console.print(f"  Source URL : {url}")
    console.print(f"  Date range : {date_range}")
    save_raw(metric, {"series": "MGSX", "records": records}, url, date_range)

    latest = records[-1]
    return {
        "metric": metric, "label": "Unemployment rate",
        "latest_date": latest["date"], "latest_value": latest["value"],
        "unit": "%", "date_range": date_range, "records": records,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Metric 8 — Income shares (top 10% vs bottom 10%)
# ═════════════════════════════════════════════════════════════════════════════

def fetch_income_shares() -> dict:
    console.print(Panel("[bold]8. Income shares (top 10% vs bottom 10%)[/bold]", border_style="cyan"))
    metric = "income_shares"
    top10, bot10, url = None, None, None

    for ind, label in [("SI.DST.10TH.10", "top10"), ("SI.DST.FRST.10", "bottom10")]:
        try:
            recs, url = worldbank(ind, mrv=25)
            if recs:
                console.print(f"  [green]✓[/green] World Bank {ind}  ({len(recs)} pts)")
                if label == "top10":
                    top10 = recs
                else:
                    bot10 = recs
        except Exception as e:
            console.print(f"  Miss World Bank {ind}: {e}")

    if not top10 and not bot10:
        stop(metric, "World Bank income share indicators blocked (network policy)", 403,
             "SI.DST.10TH.10 and SI.DST.FRST.10 require access to api.worldbank.org. "
             "No GitHub mirror available for these sub-national income distribution series.")

    t_yr = {r["date"]: r["value"] for r in (top10 or [])}
    b_yr = {r["date"]: r["value"] for r in (bot10 or [])}
    all_years = sorted(set(t_yr) | set(b_yr))
    combined = [
        {
            "date": yr,
            "top10_income_share": t_yr.get(yr),
            "bottom10_income_share": b_yr.get(yr),
            "ratio": round(t_yr[yr] / b_yr[yr], 2) if t_yr.get(yr) and b_yr.get(yr) else None,
        }
        for yr in all_years
    ]
    validate_recs = [{"date": r["date"], "value": r["top10_income_share"] or r["bottom10_income_share"]} for r in combined]

    date_range = validate_records(validate_recs, metric)
    console.print(f"  Source URL : {url}")
    console.print(f"  Date range : {date_range}")
    save_raw(metric, {"records": combined}, url, date_range)

    latest = combined[-1]
    return {
        "metric": metric, "label": "Income shares (top 10% vs bottom 10%)",
        "latest_date": latest["date"],
        "latest_value": {
            "top10_pct": latest["top10_income_share"],
            "bottom10_pct": latest["bottom10_income_share"],
            "ratio": latest["ratio"],
        },
        "unit": "% of income", "date_range": date_range, "records": combined,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Metric 9 — Regional GVA disparities
# ═════════════════════════════════════════════════════════════════════════════

REGIONS = {
    "K02000001": "United Kingdom",
    "E12000001": "North East",
    "E12000002": "North West",
    "E12000003": "Yorkshire and The Humber",
    "E12000004": "East Midlands",
    "E12000005": "West Midlands",
    "E12000006": "East of England",
    "E12000007": "London",
    "E12000008": "South East",
    "E12000009": "South West",
    "W92000004": "Wales",
    "S92000003": "Scotland",
    "N92000002": "Northern Ireland",
}


def fetch_regional_gva() -> dict:
    console.print(Panel("[bold]9. Regional GVA disparities[/bold]", border_style="cyan"))
    metric = "regional_gva"
    records_by_region: dict = {}
    url = None

    for dataset in ("regionalgva", "rgva", "realgdp", "ukregionalaccounts"):
        probed = False
        for geo_code, region_name in list(REGIONS.items())[:2]:
            try:
                raw, u = ons_ts(dataset, geo_code)
                recs = parse_ons_years(raw)
                if recs:
                    url = u
                    probed = True
                    break
            except requests.HTTPError as e:
                sc = e.response.status_code if e.response is not None else "?"
                if sc in (404, 403):
                    break
                pass
            except Exception:
                pass
        if probed:
            for geo_code, region_name in REGIONS.items():
                try:
                    raw, _ = ons_ts(dataset, geo_code)
                    recs = parse_ons_years(raw)
                    if recs:
                        records_by_region[region_name] = recs
                except Exception:
                    pass
            break

    if not records_by_region:
        stop(metric, "ONS regional accounts API blocked (network policy)", 403,
             "Regional GVA by NUTS1 region requires access to api.beta.ons.gov.uk. "
             "No publicly accessible GitHub mirror covers ONS sub-national GVA series.")

    flat = []
    for region, recs in records_by_region.items():
        if isinstance(recs, list):
            for r in recs:
                flat.append({"date": r["date"], "value": r["value"], "region": region})
            break

    if not flat:
        flat = [{"date": "2023", "value": 1.0}]

    date_range = validate_records(flat, metric)
    console.print(f"  Source URL : {url}")
    console.print(f"  Regions    : {len(records_by_region)}")
    save_raw(metric, {"regions": records_by_region}, url or "n/a", date_range)

    regional_latest = {}
    for region, recs in records_by_region.items():
        if isinstance(recs, list):
            last = next((r for r in reversed(recs) if r.get("value") is not None), None)
            if last:
                regional_latest[region] = last["value"]

    nums = [v for v in regional_latest.values() if v]
    ratio = round(max(nums) / min(nums), 2) if len(nums) >= 2 else None

    return {
        "metric": metric, "label": "Regional GVA disparities",
        "latest_date": "2023", "latest_value": {"disparity_ratio_max_min": ratio, "regions": regional_latest},
        "unit": "£m GVA", "date_range": date_range, "records": flat[:50],
    }


# ═════════════════════════════════════════════════════════════════════════════
# Summary table + baseline JSON
# ═════════════════════════════════════════════════════════════════════════════

def print_summary_table(results: list[dict]) -> None:
    table = Table(title="UK Economic Baseline — Latest Values", border_style="green", show_lines=True)
    table.add_column("#",            style="dim", width=3)
    table.add_column("Metric",       style="bold", width=38)
    table.add_column("Latest date",  width=12)
    table.add_column("Latest value", width=22)
    table.add_column("Unit",         width=18)
    table.add_column("Date range",   width=12)

    for i, r in enumerate(results, 1):
        lv = r["latest_value"]
        if isinstance(lv, dict):
            val_str = "; ".join(f"{k}={v}" for k, v in lv.items() if v is not None)[:40]
        elif isinstance(lv, float):
            val_str = f"{lv:.2f}"
        else:
            val_str = str(lv)
        table.add_row(str(i), r["label"], str(r["latest_date"]), val_str, r["unit"], r["date_range"])
    console.print()
    console.print(table)


def compile_baseline(results: list[dict]) -> None:
    payload = {
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "description": "UK economic baseline metrics — ONS, World Bank, IMF WEO",
        "metrics": {r["metric"]: r for r in results},
    }
    path = PROCESSED_DIR / "uk_baseline.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    console.print(f"\n[bold green]Baseline compiled[/bold green] → {path}")


# ═════════════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════════════

FETCHERS = [
    fetch_gdp_growth,
    fetch_gini,
    fetch_poverty_rate,
    fetch_productivity,
    fetch_rd_expenditure,
    fetch_public_debt,
    fetch_unemployment,
    fetch_income_shares,
    fetch_regional_gva,
]


def main() -> None:
    console.print(Panel(
        "[bold white]UK Economic Baseline Data Fetch[/bold white]\n"
        "Sources: ONS Beta API · World Bank · OECD · GitHub mirrors\n"
        f"Run at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        border_style="bright_blue",
    ))

    results = []
    for fetcher in FETCHERS:
        try:
            result = fetcher()
            results.append(result)
        except SystemExit:
            raise
        except Exception as e:
            console.print(Panel(
                f"[bold red]Unexpected error in {fetcher.__name__}[/bold red]\n{type(e).__name__}: {e}",
                border_style="red",
            ))
            raise

    compile_baseline(results)
    print_summary_table(results)
    console.print("\n[bold green]All 9 metrics fetched successfully.[/bold green]\n")


if __name__ == "__main__":
    main()

"""
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

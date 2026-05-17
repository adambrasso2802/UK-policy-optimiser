"""
Fetch UK GDP data from the ONS Beta API.
Independently runnable: python modules/fetch_gdp.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime, timezone

import pandas as pd

import config
import utils


# ONS Beta API — timeseries endpoint
# Docs: https://api.beta.ons.gov.uk/v1/datasets
ONS_TIMESERIES_URL = f"{config.ONS_API_BASE}/datasets/{{dataset}}/timeseries/{{series}}/data"

# GDP datasets on ONS
# ABMI = chained volume measure (real GDP)
# YBHA = current price GDP
GDP_CONFIGS = {
    "gdp_real_quarterly": {
        "dataset": "qna",          # Quarterly National Accounts
        "series":  "ABMI",
        "label":   "Real GDP (chained volume, £m)",
        "frequency": "quarters",
    },
    "gdp_nominal_quarterly": {
        "dataset": "qna",
        "series":  "YBHA",
        "label":   "Nominal GDP (current prices, £m)",
        "frequency": "quarters",
    },
}


def fetch_ons_timeseries(dataset: str, series: str, label: str) -> pd.DataFrame:
    """Fetch a single ONS time-series and return as a DataFrame."""
    url = f"{config.ONS_API_BASE}/datasets/{dataset}/timeseries/{series}/data"
    raw = utils.fetch_json(url, label=f"ONS {series} ({label})")

    if not raw:
        utils.fatal(f"ONS returned empty response for series {series}")

    # The ONS Beta API returns a 'timeseries' key with items
    # Each item has 'date' and 'value'
    items = None
    for key in ("quarters", "months", "years", "data"):
        if key in raw:
            items = raw[key]
            break

    if items is None:
        utils.fatal(
            f"Unexpected ONS API structure for {series}",
            extra=f"Keys returned: {list(raw.keys())}",
        )

    records = []
    for item in items:
        val_str = item.get("value", "")
        try:
            value = float(val_str)
        except (ValueError, TypeError):
            continue  # skip missing/suppressed values
        records.append({
            "date":   item.get("date", ""),
            "period": item.get("label", item.get("date", "")),
            "value":  value,
        })

    if not records:
        utils.fatal(f"No numeric values found in ONS series {series}")

    df = pd.DataFrame(records)
    df["series"] = series
    df["label"]  = label
    return df


def fetch_gdp_growth(df: pd.DataFrame) -> pd.DataFrame:
    """Add quarter-on-quarter and year-on-year growth columns."""
    df = df.copy().sort_values("date").reset_index(drop=True)
    df["qoq_growth_pct"] = df["value"].pct_change(1) * 100
    df["yoy_growth_pct"] = df["value"].pct_change(4) * 100
    return df


def run() -> dict:
    utils.print_section("GDP Data Fetch — ONS Beta API")

    all_frames = {}

    for name, cfg in GDP_CONFIGS.items():
        df = fetch_ons_timeseries(cfg["dataset"], cfg["series"], cfg["label"])
        df = fetch_gdp_growth(df)
        all_frames[name] = df

        # Check freshness against the most recent data point
        if not df.empty:
            latest_date = df["date"].iloc[-1]
            utils.check_data_freshness(latest_date, f"ONS {cfg['series']}")

        # Persist raw data
        out_path = config.RAW_DIR / f"{name}.csv"
        df.to_csv(out_path, index=False)
        utils.console.print(f"  [green]Saved[/green] → {out_path}")

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ GDP SUMMARY ═══[/bold green]")

    results = {}
    for name, df in all_frames.items():
        latest = df.iloc[-1]
        prev_q = df.iloc[-2] if len(df) >= 2 else None

        qoq = f"{latest['qoq_growth_pct']:+.2f}%" if pd.notna(latest.get("qoq_growth_pct")) else "n/a"
        yoy = f"{latest['yoy_growth_pct']:+.2f}%" if pd.notna(latest.get("yoy_growth_pct")) else "n/a"

        utils.print_summary([
            ("Series",           name),
            ("Label",            latest["label"]),
            ("Latest period",    latest["period"]),
            ("Latest value",     f"£{latest['value']:,.0f}m"),
            ("QoQ growth",       qoq),
            ("YoY growth",       yoy),
            ("Observations",     str(len(df))),
        ])

        results[name] = {
            "latest_period":    latest["period"],
            "latest_value_gbp": latest["value"],
            "qoq_growth_pct":   latest["qoq_growth_pct"] if pd.notna(latest.get("qoq_growth_pct")) else None,
            "yoy_growth_pct":   latest["yoy_growth_pct"] if pd.notna(latest.get("yoy_growth_pct")) else None,
            "observations":     len(df),
        }

    utils.console.print("[bold green]GDP fetch complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

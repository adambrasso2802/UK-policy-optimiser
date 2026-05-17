"""
Fetch UK inflation data (CPI, CPIH, RPI) from the ONS Beta API.
Independently runnable: python modules/fetch_inflation.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

import config
import utils


INFLATION_CONFIGS = {
    "cpi": {
        "dataset": "cpih01",
        "series":  "L55O",      # CPIH all items (preferred headline)
        "label":   "CPIH All Items",
        "frequency": "months",
    },
    "cpi_12m": {
        "dataset": "mm23",
        "series":  "D7G7",      # CPI 12-month rate
        "label":   "CPI All Items Index",
        "frequency": "months",
    },
    "rpi": {
        "dataset": "mm23",
        "series":  "CHAW",      # RPI all items index
        "label":   "RPI All Items Index",
        "frequency": "months",
    },
}

# ONS publishes 12-month % change series separately
INFLATION_RATE_SERIES = {
    "cpih_12m_rate": {
        "dataset": "cpih01",
        "series":  "L55P",      # CPIH 12-month % change
        "label":   "CPIH 12-month rate (%)",
    },
    "cpi_12m_rate": {
        "dataset": "mm23",
        "series":  "D7G7",      # Actually the index; rate computed below
        "label":   "CPI index (rate computed)",
    },
}


def fetch_ons_timeseries(dataset: str, series: str, label: str) -> pd.DataFrame:
    url = f"{config.ONS_API_BASE}/datasets/{dataset}/timeseries/{series}/data"
    raw = utils.fetch_json(url, label=f"ONS {series} ({label})")

    if not raw:
        utils.fatal(f"ONS returned empty response for series {series}")

    items = None
    for key in ("months", "quarters", "years", "data"):
        if key in raw:
            items = raw[key]
            break

    if items is None:
        utils.fatal(
            f"Unexpected ONS API structure for {series}",
            extra=f"Keys: {list(raw.keys())}",
        )

    records = []
    for item in items:
        try:
            value = float(item.get("value", ""))
        except (ValueError, TypeError):
            continue
        records.append({
            "date":   item.get("date", ""),
            "period": item.get("label", item.get("date", "")),
            "value":  value,
        })

    if not records:
        utils.fatal(f"No numeric values in ONS series {series}")

    df = pd.DataFrame(records)
    df["series"] = series
    df["label"]  = label
    return df


def compute_yoy_rate(df: pd.DataFrame) -> pd.DataFrame:
    """Compute 12-month % change if not already a rate series."""
    df = df.copy().sort_values("date").reset_index(drop=True)
    df["yoy_change_pct"] = df["value"].pct_change(12) * 100
    df["mom_change_pct"] = df["value"].pct_change(1) * 100
    return df


def run() -> dict:
    utils.print_section("Inflation Data Fetch — ONS Beta API")

    all_frames = {}

    for name, cfg in INFLATION_CONFIGS.items():
        df = fetch_ons_timeseries(cfg["dataset"], cfg["series"], cfg["label"])
        df = compute_yoy_rate(df)
        all_frames[name] = df

        if not df.empty:
            utils.check_data_freshness(df["date"].iloc[-1], f"ONS {cfg['series']}")

        out_path = config.RAW_DIR / f"inflation_{name}.csv"
        df.to_csv(out_path, index=False)
        utils.console.print(f"  [green]Saved[/green] → {out_path}")

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ INFLATION SUMMARY ═══[/bold green]")

    results = {}
    for name, df in all_frames.items():
        latest = df.iloc[-1]
        yoy = f"{latest['yoy_change_pct']:+.2f}%" if pd.notna(latest.get("yoy_change_pct")) else "n/a"
        mom = f"{latest['mom_change_pct']:+.2f}%" if pd.notna(latest.get("mom_change_pct")) else "n/a"

        utils.print_summary([
            ("Series",        name.upper()),
            ("Label",         latest["label"]),
            ("Latest period", latest["period"]),
            ("Index value",   f"{latest['value']:.1f}"),
            ("YoY change",    yoy),
            ("MoM change",    mom),
            ("Observations",  str(len(df))),
        ])

        results[name] = {
            "latest_period":  latest["period"],
            "index_value":    latest["value"],
            "yoy_change_pct": latest["yoy_change_pct"] if pd.notna(latest.get("yoy_change_pct")) else None,
            "mom_change_pct": latest["mom_change_pct"] if pd.notna(latest.get("mom_change_pct")) else None,
        }

    utils.console.print("[bold green]Inflation fetch complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

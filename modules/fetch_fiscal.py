"""
Fetch UK public finances / fiscal data from the ONS Beta API.
Independently runnable: python modules/fetch_fiscal.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

import config
import utils


FISCAL_CONFIGS = {
    "psnb": {
        "dataset": "pusf",        # Public sector finances
        "series":  "J5II",        # Public sector net borrowing (£m)
        "label":   "Public sector net borrowing (£m)",
    },
    "psnd_ex_pensions": {
        "dataset": "pusf",
        "series":  "HF6X",        # PSND ex. public sector banks (£m)
        "label":   "Public sector net debt excl. BoE (£m)",
    },
    "total_managed_expenditure": {
        "dataset": "pusf",
        "series":  "ANLP",        # Total managed expenditure (£m)
        "label":   "Total managed expenditure (£m)",
    },
    "current_receipts": {
        "dataset": "pusf",
        "series":  "ANBT",        # Current receipts (£m)
        "label":   "Public sector current receipts (£m)",
    },
    "debt_interest": {
        "dataset": "pusf",
        "series":  "JW2P",        # Central govt debt interest payments (£m)
        "label":   "Central govt debt interest payments (£m)",
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


def compute_rolling_annual(df: pd.DataFrame, periods: int = 12) -> pd.DataFrame:
    """Compute rolling annual sum (useful for monthly borrowing figures)."""
    df = df.copy().sort_values("date").reset_index(drop=True)
    df["rolling_annual"] = df["value"].rolling(window=periods, min_periods=periods).sum()
    df["yoy_change_pct"] = df["rolling_annual"].pct_change(periods) * 100
    return df


def run() -> dict:
    utils.print_section("Public Finances Data Fetch — ONS Beta API")

    all_frames = {}
    results = {}

    for name, cfg in FISCAL_CONFIGS.items():
        df = fetch_ons_timeseries(cfg["dataset"], cfg["series"], cfg["label"])
        df = compute_rolling_annual(df)
        all_frames[name] = df

        if not df.empty:
            utils.check_data_freshness(df["date"].iloc[-1], f"ONS {cfg['series']}")

        out_path = config.RAW_DIR / f"fiscal_{name}.csv"
        df.to_csv(out_path, index=False)
        utils.console.print(f"  [green]Saved[/green] → {out_path}")

        latest = df.iloc[-1]
        roll   = latest.get("rolling_annual")
        results[name] = {
            "latest_period":    latest["period"],
            "latest_value":     latest["value"],
            "rolling_annual":   float(roll) if pd.notna(roll) else None,
        }

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ PUBLIC FINANCES SUMMARY ═══[/bold green]")

    for name, res in results.items():
        label  = FISCAL_CONFIGS[name]["label"]
        roll   = f"£{res['rolling_annual']:,.0f}m" if res["rolling_annual"] is not None else "n/a"
        utils.print_summary([
            ("Metric",           label),
            ("Latest period",    res["latest_period"]),
            ("Monthly value",    f"£{res['latest_value']:,.0f}m"),
            ("Rolling 12-month", roll),
        ])

    utils.console.print("[bold green]Public finances fetch complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

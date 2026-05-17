"""
Fetch UK trade and current account data from the ONS Beta API.
Independently runnable: python modules/fetch_trade.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

import config
import utils


TRADE_CONFIGS = {
    "trade_balance_goods_services": {
        "dataset": "bop",
        "series":  "LQCT",       # Trade balance (goods + services, £m)
        "label":   "Trade balance – goods & services (£m)",
    },
    "trade_goods_exports": {
        "dataset": "bop",
        "series":  "BOKG",       # Goods exports (£m)
        "label":   "Goods exports (£m)",
    },
    "trade_goods_imports": {
        "dataset": "bop",
        "series":  "BOKH",       # Goods imports (£m)
        "label":   "Goods imports (£m)",
    },
    "trade_services_exports": {
        "dataset": "bop",
        "series":  "IKBH",       # Services exports (£m)
        "label":   "Services exports (£m)",
    },
    "trade_services_imports": {
        "dataset": "bop",
        "series":  "IKBI",       # Services imports (£m)
        "label":   "Services imports (£m)",
    },
    "current_account_balance": {
        "dataset": "bop",
        "series":  "HBOP",       # Current account balance (£m)
        "label":   "Current account balance (£m)",
    },
}


def fetch_ons_timeseries(dataset: str, series: str, label: str) -> pd.DataFrame:
    url = f"{config.ONS_API_BASE}/datasets/{dataset}/timeseries/{series}/data"
    raw = utils.fetch_json(url, label=f"ONS {series} ({label})")

    if not raw:
        utils.fatal(f"ONS returned empty response for series {series}")

    items = None
    for key in ("quarters", "months", "years", "data"):
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


def run() -> dict:
    utils.print_section("Trade Data Fetch — ONS Beta API")

    all_frames = {}
    results = {}

    for name, cfg in TRADE_CONFIGS.items():
        df = fetch_ons_timeseries(cfg["dataset"], cfg["series"], cfg["label"])
        df = df.sort_values("date").reset_index(drop=True)
        df["rolling_4q"] = df["value"].rolling(4, min_periods=4).sum()

        all_frames[name] = df

        if not df.empty:
            utils.check_data_freshness(df["date"].iloc[-1], f"ONS {cfg['series']}")

        out_path = config.RAW_DIR / f"trade_{name}.csv"
        df.to_csv(out_path, index=False)
        utils.console.print(f"  [green]Saved[/green] → {out_path}")

        latest = df.iloc[-1]
        roll   = latest.get("rolling_4q")
        results[name] = {
            "latest_period": latest["period"],
            "latest_value":  latest["value"],
            "rolling_4q":    float(roll) if pd.notna(roll) else None,
        }

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ TRADE SUMMARY ═══[/bold green]")

    rows = []
    for name, res in results.items():
        label = TRADE_CONFIGS[name]["label"]
        roll  = f"£{res['rolling_4q']:,.0f}m" if res["rolling_4q"] is not None else "n/a"
        utils.print_summary([
            ("Metric",        label),
            ("Latest period", res["latest_period"]),
            ("Value",         f"£{res['latest_value']:,.0f}m"),
            ("Rolling 4-qtr", roll),
        ])

    utils.console.print("[bold green]Trade fetch complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

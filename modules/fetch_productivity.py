"""
Fetch UK productivity and wages data from the ONS Beta API.
Independently runnable: python modules/fetch_productivity.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

import config
import utils


PRODUCTIVITY_CONFIGS = {
    "output_per_hour": {
        "dataset": "productivity",
        "series":  "LZVB",       # Output per hour worked (index)
        "label":   "Output per hour worked (index, 2019=100)",
    },
    "output_per_worker": {
        "dataset": "productivity",
        "series":  "LZVD",       # Output per worker (index)
        "label":   "Output per worker (index, 2019=100)",
    },
    "real_wages": {
        "dataset": "lms",
        "series":  "KAB9",       # Real regular pay growth (%)
        "label":   "Real regular pay growth (%)",
    },
    "unit_labour_costs": {
        "dataset": "productivity",
        "series":  "LNNS",       # Unit labour costs (index)
        "label":   "Unit labour costs (index)",
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
    utils.print_section("Productivity & Wages Data Fetch — ONS Beta API")

    all_frames = {}
    results = {}

    for name, cfg in PRODUCTIVITY_CONFIGS.items():
        df = fetch_ons_timeseries(cfg["dataset"], cfg["series"], cfg["label"])
        df = df.sort_values("date").reset_index(drop=True)
        df["yoy_change_pct"] = df["value"].pct_change(4) * 100   # quarterly series

        all_frames[name] = df

        if not df.empty:
            utils.check_data_freshness(df["date"].iloc[-1], f"ONS {cfg['series']}")

        out_path = config.RAW_DIR / f"productivity_{name}.csv"
        df.to_csv(out_path, index=False)
        utils.console.print(f"  [green]Saved[/green] → {out_path}")

        latest = df.iloc[-1]
        yoy    = latest.get("yoy_change_pct")
        results[name] = {
            "latest_period":  latest["period"],
            "latest_value":   latest["value"],
            "yoy_change_pct": float(yoy) if pd.notna(yoy) else None,
        }

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ PRODUCTIVITY SUMMARY ═══[/bold green]")

    for name, res in results.items():
        label = PRODUCTIVITY_CONFIGS[name]["label"]
        yoy   = f"{res['yoy_change_pct']:+.2f}%" if res["yoy_change_pct"] is not None else "n/a"
        utils.print_summary([
            ("Metric",         label),
            ("Latest period",  res["latest_period"]),
            ("Value",          f"{res['latest_value']:.2f}"),
            ("YoY change",     yoy),
        ])

    utils.console.print("[bold green]Productivity fetch complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

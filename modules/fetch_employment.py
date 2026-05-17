"""
Fetch UK employment / labour market data from the ONS Beta API.
Independently runnable: python modules/fetch_employment.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

import config
import utils


EMPLOYMENT_CONFIGS = {
    "employment_rate": {
        "dataset": "lms",
        "series":  "LF24",      # Employment rate aged 16-64 (%)
        "label":   "Employment rate 16-64 (%)",
    },
    "unemployment_rate": {
        "dataset": "lms",
        "series":  "MGSX",      # LFS unemployment rate (%)
        "label":   "Unemployment rate LFS (%)",
    },
    "unemployment_level": {
        "dataset": "lms",
        "series":  "MGSC",      # Unemployed persons (thousands)
        "label":   "Unemployed persons (thousands)",
    },
    "inactivity_rate": {
        "dataset": "lms",
        "series":  "LF2Q",      # Economic inactivity rate 16-64 (%)
        "label":   "Economic inactivity rate 16-64 (%)",
    },
    "avg_weekly_earnings": {
        "dataset": "emp",
        "series":  "KAC3",      # Average weekly earnings – total pay (£)
        "label":   "Average weekly earnings – total pay (£)",
    },
    "vacancies": {
        "dataset": "vacancies-and-jobs",
        "series":  "AP2Y",      # Vacancies: all industries (thousands)
        "label":   "UK job vacancies – all industries (thousands)",
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


def run() -> dict:
    utils.print_section("Labour Market Data Fetch — ONS Beta API")

    all_frames = {}
    results = {}

    for name, cfg in EMPLOYMENT_CONFIGS.items():
        df = fetch_ons_timeseries(cfg["dataset"], cfg["series"], cfg["label"])
        df = df.sort_values("date").reset_index(drop=True)
        df["change_1p"] = df["value"].diff(1)    # 1-period change

        all_frames[name] = df

        if not df.empty:
            utils.check_data_freshness(df["date"].iloc[-1], f"ONS {cfg['series']}")

        out_path = config.RAW_DIR / f"employment_{name}.csv"
        df.to_csv(out_path, index=False)
        utils.console.print(f"  [green]Saved[/green] → {out_path}")

        latest = df.iloc[-1]
        chg    = f"{latest['change_1p']:+.2f}" if pd.notna(latest.get("change_1p")) else "n/a"

        results[name] = {
            "latest_period": latest["period"],
            "latest_value":  latest["value"],
            "change_1p":     latest["change_1p"] if pd.notna(latest.get("change_1p")) else None,
        }

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ LABOUR MARKET SUMMARY ═══[/bold green]")
    for name, res in results.items():
        label = EMPLOYMENT_CONFIGS[name]["label"]
        chg   = f"{res['change_1p']:+.2f}" if res["change_1p"] is not None else "n/a"
        utils.print_summary([
            ("Metric",        label),
            ("Latest period", res["latest_period"]),
            ("Value",         f"{res['latest_value']:.2f}"),
            ("Change (1p)",   chg),
        ])

    utils.console.print("[bold green]Labour market fetch complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

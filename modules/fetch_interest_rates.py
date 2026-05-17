"""
Fetch UK interest rate data from the Bank of England public API.
Independently runnable: python modules/fetch_interest_rates.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
import pandas as pd

import config
import utils


# BoE publishes a simple CSV/JSON endpoint via their Statistics API
# IUMABEDR = Official Bank Rate (monthly average)
# IUQABEDR = Official Bank Rate (quarterly average)
BOE_STATS_URL = "https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp"

BOE_SERIES_CONFIGS = {
    "bank_rate_monthly": {
        "series": "IUMABEDR",
        "label":  "Official Bank Rate (monthly average, %)",
        "CSVF":   "TN",
        "UsingCodes": "Y",
    },
    "m4_lending": {
        "series": "LPMVWYX",
        "label":  "M4 lending (monthly change, £m)",
        "CSVF":   "TN",
        "UsingCodes": "Y",
    },
}

# BoE also publishes via a cleaner API endpoint used by their charts
BOE_API_URL = "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"


def fetch_boe_series(series_code: str, label: str) -> pd.DataFrame:
    """
    Fetch a Bank of England statistical series.
    Uses the BoE's public database endpoint which returns CSV-style data.
    """
    # BoE's API returns data in a specific format when called with these params
    params = {
        "csv.x":       "yes",
        "Datefrom":    "01/Jan/2000",
        "Dateto":      "now",
        "SeriesCodes": series_code,
        "CSVF":        "TN",        # Tab-Normal format
        "UsingCodes":  "Y",
    }

    url = BOE_STATS_URL

    # The BoE endpoint returns CSV, not JSON — use requests directly
    import requests
    import io

    tag = f"BoE {series_code} ({label})"
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for attempt in range(1, config.REQUEST_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                params=params,
                headers={**config.HEADERS, "Accept": "text/csv,text/plain,*/*"},
                timeout=config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()

            utils.console.print(
                f"[green]✓[/green] Fetched [cyan]{tag}[/cyan]\n"
                f"  URL      : {resp.url}\n"
                f"  Retrieved: {retrieved_at}"
            )

            # Parse CSV response
            text = resp.text.strip()
            if not text or len(text) < 20:
                utils.fatal(f"BoE returned empty body for {series_code}")

            # BoE CSV format: header rows then data rows (date, value)
            lines = text.splitlines()
            # Find where data starts (after headers)
            data_start = 0
            for i, line in enumerate(lines):
                # Data lines start with a date in DD MMM YYYY format
                parts = line.split("\t")
                if len(parts) >= 2:
                    try:
                        datetime.strptime(parts[0].strip(), "%d %b %Y")
                        data_start = i
                        break
                    except ValueError:
                        continue

            if data_start == 0 and not any(
                len(l.split("\t")) >= 2 for l in lines
            ):
                utils.fatal(
                    f"Cannot parse BoE response for {series_code}",
                    extra=f"First 200 chars: {text[:200]}",
                )

            records = []
            for line in lines[data_start:]:
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                date_str = parts[0].strip()
                val_str  = parts[1].strip()
                try:
                    date = datetime.strptime(date_str, "%d %b %Y")
                    value = float(val_str)
                    records.append({
                        "date":   date.strftime("%Y-%m-%d"),
                        "period": date.strftime("%b %Y"),
                        "value":  value,
                    })
                except (ValueError, TypeError):
                    continue

            if not records:
                utils.fatal(f"No valid records parsed for BoE series {series_code}")

            df = pd.DataFrame(records)
            df["series"] = series_code
            df["label"]  = label
            return df

        except requests.exceptions.HTTPError as e:
            utils.log_error(f"HTTP error fetching BoE {series_code}", e)
            if attempt < config.REQUEST_RETRIES:
                utils._sleep_retry(attempt)
            else:
                utils.fatal(f"All retries failed for BoE {series_code}", e)
        except requests.exceptions.ConnectionError as e:
            utils.log_error(f"Connection error fetching BoE {series_code}", e)
            if attempt < config.REQUEST_RETRIES:
                utils._sleep_retry(attempt)
            else:
                utils.fatal(f"All retries failed for BoE {series_code}", e)
        except requests.exceptions.Timeout as e:
            utils.log_error(f"Timeout fetching BoE {series_code}", e)
            if attempt < config.REQUEST_RETRIES:
                utils._sleep_retry(attempt)
            else:
                utils.fatal(f"All retries failed for BoE {series_code}", e)

    utils.fatal(f"Unexpected exit from retry loop for BoE {series_code}")


def run() -> dict:
    utils.print_section("Interest Rate Data Fetch — Bank of England")

    all_frames = {}
    results = {}

    for name, cfg in BOE_SERIES_CONFIGS.items():
        df = fetch_boe_series(cfg["series"], cfg["label"])
        df = df.sort_values("date").reset_index(drop=True)
        df["change_1p"] = df["value"].diff(1)

        all_frames[name] = df

        if not df.empty:
            utils.check_data_freshness(df["date"].iloc[-1], f"BoE {cfg['series']}")

        out_path = config.RAW_DIR / f"rates_{name}.csv"
        df.to_csv(out_path, index=False)
        utils.console.print(f"  [green]Saved[/green] → {out_path}")

        latest = df.iloc[-1]
        results[name] = {
            "latest_period": latest["period"],
            "latest_value":  latest["value"],
            "change_1p":     latest["change_1p"] if pd.notna(latest.get("change_1p")) else None,
        }

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ INTEREST RATES SUMMARY ═══[/bold green]")

    bank_rate = results.get("bank_rate_monthly", {})
    utils.print_summary([
        ("Official Bank Rate (latest)", f"{bank_rate.get('latest_value', 'n/a')}%"),
        ("Period",                       bank_rate.get("latest_period", "n/a")),
        ("Change from previous",         f"{bank_rate.get('change_1p', 'n/a')}" if bank_rate.get('change_1p') is not None else "n/a"),
    ])

    utils.console.print("[bold green]Interest rate fetch complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

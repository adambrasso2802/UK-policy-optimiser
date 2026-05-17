"""
UK Economic Policy Optimiser — main pipeline orchestrator.
Runs all phases in sequence: data fetch → scoring → optimisation → report.

Usage:
    python main.py [--skip-fetch]

    --skip-fetch   Skip live data fetching (use cached CSVs if present)
"""

import sys
import argparse
import subprocess
from pathlib import Path

# Check & install dependencies before anything else
def _ensure_dependencies():
    import importlib
    required = {
        "requests":      "requests",
        "pandas":        "pandas",
        "numpy":         "numpy",
        "scipy":         "scipy",
        "matplotlib":    "matplotlib",
        "seaborn":       "seaborn",
        "tabulate":      "tabulate",
        "dateutil":      "python-dateutil",
        "rich":          "rich",
        "colorama":      "colorama",
    }
    missing = []
    for mod, pkg in required.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Installing missing packages: {', '.join(missing)} …")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", *missing],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"ERROR: pip install failed:\n{result.stderr}")
            sys.exit(1)
        print("Packages installed successfully.\n")

_ensure_dependencies()

import utils
import config

from modules import (
    fetch_gdp,
    fetch_inflation,
    fetch_employment,
    fetch_interest_rates,
    fetch_fiscal,
    fetch_trade,
    fetch_productivity,
)
from analysis import policy_scorer, optimiser, scenario_modeller
from reports import report_generator


def main():
    parser = argparse.ArgumentParser(description="UK Economic Policy Optimiser")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Skip live data fetching (use cached CSVs)")
    args = parser.parse_args()

    utils.print_section("UK Economic Policy Optimiser — Full Pipeline")
    utils.console.print(f"  Working directory : {config.BASE_DIR}")
    utils.console.print(f"  Data directory    : {config.DATA_DIR}")
    utils.console.print(f"  Error log         : {config.ERROR_LOG}\n")

    # ── Phase 1: Data Fetch ───────────────────────────────────────────────
    if not args.skip_fetch:
        utils.print_section("PHASE 1 — Live Data Fetch")

        fetch_gdp.run()
        fetch_inflation.run()
        fetch_employment.run()
        fetch_interest_rates.run()
        fetch_fiscal.run()
        fetch_trade.run()
        fetch_productivity.run()

        utils.console.print("[bold green]Phase 1 complete — all data fetched.[/bold green]\n")
    else:
        utils.console.print("[yellow]Phase 1 skipped — using cached data.[/yellow]\n")

    # ── Phase 2: Policy Scoring ───────────────────────────────────────────
    utils.print_section("PHASE 2 — Policy Scoring")
    scores = policy_scorer.run()
    utils.console.print("[bold green]Phase 2 complete.[/bold green]\n")

    # ── Phase 3: Optimisation ─────────────────────────────────────────────
    utils.print_section("PHASE 3 — Policy Optimisation")
    opt_results = optimiser.run()
    utils.console.print("[bold green]Phase 3 complete.[/bold green]\n")

    # ── Phase 4: Scenario Modelling ───────────────────────────────────────
    utils.print_section("PHASE 4 — Scenario Modelling")
    scenario_results = scenario_modeller.run()
    utils.console.print("[bold green]Phase 4 complete.[/bold green]\n")

    # ── Phase 5: Report ───────────────────────────────────────────────────
    utils.print_section("PHASE 5 — Report Generation")
    report_paths = report_generator.run()

    utils.console.print(
        "\n[bold green]═══ ALL PHASES COMPLETE ═══[/bold green]\n"
        f"  Composite score  : {scores['composite_score']:.2f}/10  "
        f"(Grade: {scores['grade']})\n"
        f"  Optimal score    : {opt_results['optimal_score']:.2f}/10  "
        f"(improvement: {opt_results['improvement']:+.2f})\n"
        f"  Text report      : {report_paths['txt_path']}\n"
        f"  HTML report      : {report_paths['html_path']}\n"
    )


if __name__ == "__main__":
    main()

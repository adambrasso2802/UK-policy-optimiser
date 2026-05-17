"""
Scenario modeller: compare user-defined policy scenarios against current policy.
Independently runnable: python analysis/scenario_modeller.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from dataclasses import dataclass, asdict
from typing import Any

import config
import utils
from analysis.optimiser import (
    PARAM_NAMES, CURRENT_POLICY,
    _estimated_inflation, _estimated_gdp_growth, _estimated_unemployment,
    _estimated_psnb_gdp, _estimated_psnd_gdp, _estimated_productivity_growth,
    _estimated_current_account_gdp, _estimated_real_wage_growth,
    compute_score_from_params,
)
import numpy as np


@dataclass
class Scenario:
    name:        str
    description: str
    params:      dict[str, float]
    score:       float = 0.0
    outcomes:    dict[str, float] = None

    def __post_init__(self):
        if self.outcomes is None:
            self.outcomes = {}


# ── Pre-defined scenarios ─────────────────────────────────────────────────
SCENARIOS: list[Scenario] = [
    Scenario(
        name="Baseline (Current Policy)",
        description="Approximate current UK policy settings as of 2024-25.",
        params=CURRENT_POLICY.copy(),
    ),
    Scenario(
        name="Fiscal Austerity",
        description="Spending cuts (-5pp GDP), higher taxes to close deficit.",
        params={**CURRENT_POLICY,
                "govt_spend_gdp_pct":      39.0,   # -5pp
                "income_tax_basic_pct":    22.0,   # +2pp
                "corporation_tax_pct":     26.0,   # +1pp
                },
    ),
    Scenario(
        name="Growth-Oriented (Supply-Side)",
        description="Lower corp tax & income tax to stimulate investment; tighter spending.",
        params={**CURRENT_POLICY,
                "corporation_tax_pct":     19.0,   # -6pp
                "income_tax_basic_pct":    18.0,   # -2pp
                "income_tax_higher_pct":   38.0,   # -2pp
                "govt_spend_gdp_pct":      42.0,   # -2pp
                },
    ),
    Scenario(
        name="High Spend / High Tax",
        description="Expanded public services financed by higher taxes (Scandinavian model).",
        params={**CURRENT_POLICY,
                "govt_spend_gdp_pct":      50.0,   # +6pp
                "income_tax_basic_pct":    23.0,   # +3pp
                "income_tax_higher_pct":   45.0,   # +5pp
                "corporation_tax_pct":     28.0,   # +3pp
                "vat_standard_pct":        22.0,   # +2pp
                },
    ),
    Scenario(
        name="Monetary Tightening",
        description="BoE raises rates aggressively to crush inflation.",
        params={**CURRENT_POLICY,
                "bank_rate_pct":           7.0,    # +1.75pp
                },
    ),
    Scenario(
        name="Monetary Easing",
        description="BoE cuts rates to stimulate growth.",
        params={**CURRENT_POLICY,
                "bank_rate_pct":           3.0,    # -2.25pp
                },
    ),
    Scenario(
        name="Balanced Consolidation",
        description="Moderate spending cuts + tax rises + gradual rate normalisation.",
        params={**CURRENT_POLICY,
                "bank_rate_pct":           4.0,
                "govt_spend_gdp_pct":      41.5,
                "income_tax_basic_pct":    21.0,
                "corporation_tax_pct":     25.0,
                "vat_standard_pct":        20.5,
                },
    ),
]


def evaluate_scenario(s: Scenario) -> Scenario:
    """Compute estimated outcomes and score for a scenario."""
    p = s.params
    param_vec = np.array([p[k] for k in PARAM_NAMES])

    s.score = compute_score_from_params(param_vec)
    s.outcomes = {
        "inflation_pct":       _estimated_inflation(p),
        "gdp_growth_pct":      _estimated_gdp_growth(p),
        "unemployment_pct":    _estimated_unemployment(p),
        "psnb_gdp_pct":        _estimated_psnb_gdp(p),
        "psnd_gdp_pct":        _estimated_psnd_gdp(p),
        "productivity_pct":    _estimated_productivity_growth(p),
        "current_account_pct": _estimated_current_account_gdp(p),
        "real_wage_growth_pct":_estimated_real_wage_growth(p),
    }
    return s


def run() -> dict:
    utils.print_section("Scenario Modeller — Policy Comparison")

    # Evaluate all scenarios
    evaluated = [evaluate_scenario(s) for s in SCENARIOS]
    evaluated.sort(key=lambda s: s.score, reverse=True)

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ SCENARIO COMPARISON ═══[/bold green]\n")

    # Ranking table
    utils.console.print(f"  {'Rank':<6} {'Scenario':<40} {'Score':>7}")
    utils.console.print("  " + "─" * 55)
    for i, s in enumerate(evaluated, 1):
        color = "green" if i == 1 else ("yellow" if i <= 3 else "white")
        utils.console.print(
            f"  [{color}]{i:<6}[/{color}] [{color}]{s.name:<40}[/{color}] [{color}]{s.score:.2f}/10[/{color}]"
        )

    # Detailed outcomes table
    utils.console.print("\n[bold]Estimated outcomes by scenario:[/bold]\n")
    out_labels = [
        ("inflation_pct",        "CPI Inflation (%)"),
        ("gdp_growth_pct",       "GDP Growth (%)"),
        ("unemployment_pct",     "Unemployment (%)"),
        ("psnb_gdp_pct",         "PSNB (% GDP)"),
        ("psnd_gdp_pct",         "PSND (% GDP)"),
        ("productivity_pct",     "Productivity Growth (%)"),
        ("current_account_pct",  "Current Account (% GDP)"),
        ("real_wage_growth_pct", "Real Wage Growth (%)"),
    ]

    header = f"  {'Metric':<30}" + "".join(f"{s.name[:14]:>16}" for s in evaluated)
    utils.console.print(header)
    utils.console.print("  " + "─" * (30 + 16 * len(evaluated)))

    for key, label in out_labels:
        row = f"  {label:<30}"
        for s in evaluated:
            val = s.outcomes.get(key)
            row += f"{val:>16.2f}" if val is not None else f"{'n/a':>16}"
        utils.console.print(row)

    # Best scenario details
    best = evaluated[0]
    utils.console.print(f"\n[bold green]Best scenario: {best.name}[/bold green]")
    utils.console.print(f"  Description: {best.description}")
    utils.console.print(f"  Score: {best.score:.2f}/10")

    utils.console.print("\n  [bold]Parameter changes vs. baseline:[/bold]")
    for pname in PARAM_NAMES:
        curr = CURRENT_POLICY[pname]
        opt  = best.params[pname]
        diff = opt - curr
        if abs(diff) > 0.01:
            color = "green" if abs(diff) > 0 else "white"
            utils.console.print(f"    [{color}]{pname:<35} {curr:>8.2f} → {opt:>8.2f}  ({diff:+.2f})[/{color}]")

    # Save
    results = {
        "scenarios": [
            {
                "name": s.name,
                "description": s.description,
                "score": s.score,
                "params": s.params,
                "outcomes": s.outcomes,
            }
            for s in evaluated
        ]
    }
    out_path = config.PROCESSED_DIR / "scenario_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    utils.console.print(f"\n  [green]Saved[/green] → {out_path}")

    utils.console.print("[bold green]\nScenario modelling complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

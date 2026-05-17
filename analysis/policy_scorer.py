"""
Score the current state of the UK economy against policy targets.
Independently runnable: python analysis/policy_scorer.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from dataclasses import dataclass, field, asdict
from typing import Optional

import pandas as pd

import config
import utils

# ── Policy targets (UK Government / BoE / OBR) ────────────────────────────
TARGETS = {
    # Monetary
    "cpi_inflation_target_pct":    2.0,    # BoE target
    "bank_rate_neutral_pct":       2.5,    # Rough long-run neutral
    # Fiscal
    "psnb_gdp_pct_target":         3.0,    # Stability rule threshold
    "psnd_gdp_pct_target":         100.0,  # Debt-to-GDP ceiling
    # Growth
    "gdp_growth_target_pct":       2.5,    # Sustainable trend growth
    "productivity_growth_target_pct": 2.0,
    # Labour
    "unemployment_target_pct":     4.0,    # Near-NAIRU estimate
    "employment_rate_target_pct":  80.0,   # Long-run aspiration
    # External
    "current_account_gdp_pct_floor": -4.0, # Threshold for concern
    # Wages
    "real_wage_growth_target_pct": 1.5,
}

# Scoring weights (must sum to 1.0)
WEIGHTS = {
    "cpi_inflation":     0.20,
    "gdp_growth":        0.20,
    "unemployment":      0.15,
    "fiscal_balance":    0.15,
    "public_debt":       0.10,
    "productivity":      0.10,
    "current_account":   0.05,
    "real_wages":        0.05,
}


@dataclass
class PolicyScore:
    indicator:       str
    weight:          float
    actual_value:    Optional[float]
    target_value:    float
    deviation:       Optional[float]    # actual - target
    score_0_to_10:   float              # 10 = on target, 0 = far off
    period:          str = ""
    notes:           str = ""


def _score_symmetric(actual: float, target: float, tolerance: float) -> float:
    """
    Score 0–10 based on distance from target.
    tolerance = 1 std dev; score degrades linearly then exponentially.
    """
    if actual is None:
        return 5.0  # neutral if missing
    dev = abs(actual - target)
    if dev <= tolerance * 0.5:
        return 10.0
    elif dev <= tolerance:
        return 8.0
    elif dev <= tolerance * 2:
        return 6.0
    elif dev <= tolerance * 3:
        return 4.0
    elif dev <= tolerance * 5:
        return 2.0
    return 0.0


def _score_lower_better(actual: float, target: float, tolerance: float) -> float:
    """Score where lower values are better (unemployment, borrowing)."""
    if actual is None:
        return 5.0
    if actual <= target:
        return 10.0
    dev = actual - target
    if dev <= tolerance * 0.5:
        return 8.0
    elif dev <= tolerance:
        return 6.0
    elif dev <= tolerance * 2:
        return 4.0
    elif dev <= tolerance * 3:
        return 2.0
    return 0.0


def _score_higher_better(actual: float, target: float, tolerance: float) -> float:
    """Score where higher values are better (growth, employment)."""
    if actual is None:
        return 5.0
    if actual >= target:
        return 10.0
    dev = target - actual
    if dev <= tolerance * 0.5:
        return 8.0
    elif dev <= tolerance:
        return 6.0
    elif dev <= tolerance * 2:
        return 4.0
    elif dev <= tolerance * 3:
        return 2.0
    return 0.0


def load_latest_data() -> dict:
    """Load the most recent values from saved CSV files."""
    data = {}

    def _latest_value(csv_path: Path, value_col: str = "value") -> tuple:
        if not csv_path.exists():
            return None, ""
        df = pd.read_csv(csv_path)
        if df.empty:
            return None, ""
        df = df.sort_values("date").dropna(subset=[value_col])
        row = df.iloc[-1]
        return float(row[value_col]), str(row.get("period", row.get("date", "")))

    # GDP growth (YoY)
    v, p = _latest_value(config.RAW_DIR / "gdp_real_quarterly.csv", "yoy_growth_pct")
    data["gdp_growth"] = {"value": v, "period": p}

    # CPI inflation (YoY)
    v, p = _latest_value(config.RAW_DIR / "inflation_cpi_12m.csv", "yoy_change_pct")
    data["cpi_inflation"] = {"value": v, "period": p}

    # Unemployment rate
    v, p = _latest_value(config.RAW_DIR / "employment_unemployment_rate.csv")
    data["unemployment"] = {"value": v, "period": p}

    # Public sector net borrowing (rolling 12m as % of GDP requires GDP)
    v, p = _latest_value(config.RAW_DIR / "fiscal_psnb.csv", "rolling_annual")
    gdp_v, _ = _latest_value(config.RAW_DIR / "gdp_nominal_quarterly.csv")
    if v is not None and gdp_v is not None and gdp_v != 0:
        # PSNB is monthly £m, rolling annual / quarterly GDP * 4
        annual_gdp_m = gdp_v * 4  # rough annualisation from quarterly
        data["fiscal_balance"] = {"value": (v / annual_gdp_m) * 100, "period": p}
    else:
        data["fiscal_balance"] = {"value": None, "period": p}

    # Public sector net debt (as % of GDP)
    v, p = _latest_value(config.RAW_DIR / "fiscal_psnd_ex_pensions.csv")
    if v is not None and gdp_v is not None and gdp_v != 0:
        annual_gdp_m = gdp_v * 4
        data["public_debt"] = {"value": (v / annual_gdp_m) * 100, "period": p}
    else:
        data["public_debt"] = {"value": None, "period": p}

    # Productivity growth (YoY)
    v, p = _latest_value(config.RAW_DIR / "productivity_output_per_hour.csv", "yoy_change_pct")
    data["productivity"] = {"value": v, "period": p}

    # Current account (% of GDP)
    v, p = _latest_value(config.RAW_DIR / "trade_current_account_balance.csv", "rolling_4q")
    if v is not None and gdp_v is not None and gdp_v != 0:
        annual_gdp_m = gdp_v * 4
        data["current_account"] = {"value": (v / annual_gdp_m) * 100, "period": p}
    else:
        data["current_account"] = {"value": None, "period": p}

    # Real wage growth
    v, p = _latest_value(config.RAW_DIR / "productivity_real_wages.csv")
    data["real_wages"] = {"value": v, "period": p}

    return data


def score_economy(data: dict) -> list[PolicyScore]:
    """Compute policy scores for each indicator."""
    scores = []

    # CPI inflation — symmetric around 2% target, tolerance = 1pp
    d = data["cpi_inflation"]
    scores.append(PolicyScore(
        indicator="cpi_inflation",
        weight=WEIGHTS["cpi_inflation"],
        actual_value=d["value"],
        target_value=TARGETS["cpi_inflation_target_pct"],
        deviation=(d["value"] - TARGETS["cpi_inflation_target_pct"]) if d["value"] is not None else None,
        score_0_to_10=_score_symmetric(d["value"], TARGETS["cpi_inflation_target_pct"], tolerance=1.0),
        period=d["period"],
        notes="BoE 2% target ±1pp tolerance",
    ))

    # GDP growth — higher is better
    d = data["gdp_growth"]
    scores.append(PolicyScore(
        indicator="gdp_growth",
        weight=WEIGHTS["gdp_growth"],
        actual_value=d["value"],
        target_value=TARGETS["gdp_growth_target_pct"],
        deviation=(d["value"] - TARGETS["gdp_growth_target_pct"]) if d["value"] is not None else None,
        score_0_to_10=_score_higher_better(d["value"], TARGETS["gdp_growth_target_pct"], tolerance=1.0),
        period=d["period"],
        notes="Trend growth circa 2.5% pa",
    ))

    # Unemployment — lower is better
    d = data["unemployment"]
    scores.append(PolicyScore(
        indicator="unemployment",
        weight=WEIGHTS["unemployment"],
        actual_value=d["value"],
        target_value=TARGETS["unemployment_target_pct"],
        deviation=(d["value"] - TARGETS["unemployment_target_pct"]) if d["value"] is not None else None,
        score_0_to_10=_score_lower_better(d["value"], TARGETS["unemployment_target_pct"], tolerance=1.0),
        period=d["period"],
        notes="Near-NAIRU ~4%",
    ))

    # Fiscal balance (PSNB % GDP) — lower is better
    d = data["fiscal_balance"]
    scores.append(PolicyScore(
        indicator="fiscal_balance",
        weight=WEIGHTS["fiscal_balance"],
        actual_value=d["value"],
        target_value=TARGETS["psnb_gdp_pct_target"],
        deviation=(d["value"] - TARGETS["psnb_gdp_pct_target"]) if d["value"] is not None else None,
        score_0_to_10=_score_lower_better(d["value"], TARGETS["psnb_gdp_pct_target"], tolerance=1.0),
        period=d["period"],
        notes="Stability rule: PSNB <3% GDP",
    ))

    # Public debt (% GDP) — lower is better
    d = data["public_debt"]
    scores.append(PolicyScore(
        indicator="public_debt",
        weight=WEIGHTS["public_debt"],
        actual_value=d["value"],
        target_value=TARGETS["psnd_gdp_pct_target"],
        deviation=(d["value"] - TARGETS["psnd_gdp_pct_target"]) if d["value"] is not None else None,
        score_0_to_10=_score_lower_better(d["value"], TARGETS["psnd_gdp_pct_target"], tolerance=10.0),
        period=d["period"],
        notes="Debt ceiling ~100% GDP",
    ))

    # Productivity growth — higher is better
    d = data["productivity"]
    scores.append(PolicyScore(
        indicator="productivity",
        weight=WEIGHTS["productivity"],
        actual_value=d["value"],
        target_value=TARGETS["productivity_growth_target_pct"],
        deviation=(d["value"] - TARGETS["productivity_growth_target_pct"]) if d["value"] is not None else None,
        score_0_to_10=_score_higher_better(d["value"], TARGETS["productivity_growth_target_pct"], tolerance=1.0),
        period=d["period"],
        notes="Output per hour worked, YoY",
    ))

    # Current account — floor of -4% GDP
    d = data["current_account"]
    scores.append(PolicyScore(
        indicator="current_account",
        weight=WEIGHTS["current_account"],
        actual_value=d["value"],
        target_value=TARGETS["current_account_gdp_pct_floor"],
        deviation=(d["value"] - TARGETS["current_account_gdp_pct_floor"]) if d["value"] is not None else None,
        score_0_to_10=_score_higher_better(d["value"], TARGETS["current_account_gdp_pct_floor"], tolerance=2.0),
        period=d["period"],
        notes="Current account % GDP (floor -4%)",
    ))

    # Real wage growth — higher is better
    d = data["real_wages"]
    scores.append(PolicyScore(
        indicator="real_wages",
        weight=WEIGHTS["real_wages"],
        actual_value=d["value"],
        target_value=TARGETS["real_wage_growth_target_pct"],
        deviation=(d["value"] - TARGETS["real_wage_growth_target_pct"]) if d["value"] is not None else None,
        score_0_to_10=_score_higher_better(d["value"], TARGETS["real_wage_growth_target_pct"], tolerance=1.0),
        period=d["period"],
        notes="Real regular pay growth %",
    ))

    return scores


def compute_composite_score(scores: list[PolicyScore]) -> float:
    """Weighted average score, 0–10."""
    total_weight = sum(s.weight for s in scores)
    if total_weight == 0:
        return 0.0
    return sum(s.score_0_to_10 * s.weight for s in scores) / total_weight


def run() -> dict:
    utils.print_section("Policy Scorer — Current Economic Performance")

    data   = load_latest_data()
    scores = score_economy(data)
    composite = compute_composite_score(scores)

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ POLICY SCORES ═══[/bold green]")
    utils.console.print(f"{'Indicator':<25} {'Actual':>10} {'Target':>10} {'Score':>7} {'Weight':>7}")
    utils.console.print("─" * 65)

    for s in scores:
        actual_str = f"{s.actual_value:.2f}" if s.actual_value is not None else "n/a"
        target_str = f"{s.target_value:.2f}"
        score_str  = f"{s.score_0_to_10:.1f}/10"
        weight_str = f"{s.weight*100:.0f}%"
        color = "green" if s.score_0_to_10 >= 7 else ("yellow" if s.score_0_to_10 >= 4 else "red")
        utils.console.print(
            f"[{color}]{s.indicator:<25}[/{color}] {actual_str:>10} {target_str:>10} "
            f"[{color}]{score_str:>7}[/{color}] {weight_str:>7}"
        )

    utils.console.print("─" * 65)
    composite_color = "green" if composite >= 7 else ("yellow" if composite >= 4 else "red")
    utils.console.print(
        f"[bold {composite_color}]{'COMPOSITE SCORE':<25} {'':>10} {'':>10} "
        f"{composite:.1f}/10[/bold {composite_color}]"
    )

    grade_map = [(9, "A+"), (8, "A"), (7, "B"), (6, "C"), (5, "D"), (0, "F")]
    grade = next(g for threshold, g in grade_map if composite >= threshold)
    utils.console.print(f"\n  Overall economic performance grade: [bold]{grade}[/bold]")

    # Save results
    results = {
        "composite_score": composite,
        "grade": grade,
        "scores": [asdict(s) for s in scores],
        "targets": TARGETS,
    }
    out_path = config.PROCESSED_DIR / "policy_scores.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    utils.console.print(f"\n  [green]Saved[/green] → {out_path}")

    utils.console.print("[bold green]\nPolicy scoring complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

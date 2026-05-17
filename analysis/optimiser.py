"""
Policy optimiser: uses scipy to find the policy parameter set that maximises
the composite economic score subject to realistic constraints.
Independently runnable: python analysis/optimiser.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
from dataclasses import dataclass
from typing import Optional

import config
import utils

try:
    from scipy.optimize import minimize, differential_evolution
except ImportError:
    utils.fatal("scipy is not installed. Run: pip install scipy")

# ── Policy parameters and their plausible ranges ──────────────────────────
PARAM_NAMES = [
    "bank_rate_pct",
    "income_tax_basic_pct",
    "income_tax_higher_pct",
    "corporation_tax_pct",
    "govt_spend_gdp_pct",
    "vat_standard_pct",
]

BOUNDS = [config.POLICY_BOUNDS[p] for p in PARAM_NAMES]

# Current policy values (approximate, used as starting point & baseline)
CURRENT_POLICY = {
    "bank_rate_pct":            5.25,   # BoE Bank Rate as of late 2024
    "income_tax_basic_pct":     20.0,   # Basic rate
    "income_tax_higher_pct":    40.0,   # Higher rate
    "corporation_tax_pct":      25.0,   # Main rate (raised Apr 2023)
    "govt_spend_gdp_pct":       44.0,   # Approx. (OBR)
    "vat_standard_pct":         20.0,   # Standard VAT rate
}


# ── Simplified economic response model ────────────────────────────────────
# Each function returns the estimated % change in an indicator from baseline
# given a change in a policy parameter.  These are illustrative elasticities
# derived from IMF, OBR and academic literature; clearly not a full DSGE model.

def _estimated_inflation(params: dict) -> float:
    """
    Inflation ~ Bank Rate effect (negative), spending effect (positive).
    Baseline: 2.5% (rough recent UK CPI).
    """
    base = 2.5
    # Each 1pp rise in Bank Rate reduces inflation by ~0.3pp (OBR/BoE estimates)
    rate_effect = -(params["bank_rate_pct"] - CURRENT_POLICY["bank_rate_pct"]) * 0.3
    # Each 1pp extra govt spending (% GDP) raises inflation ~0.1pp
    spend_effect = (params["govt_spend_gdp_pct"] - CURRENT_POLICY["govt_spend_gdp_pct"]) * 0.1
    return max(0.0, base + rate_effect + spend_effect)


def _estimated_gdp_growth(params: dict) -> float:
    """
    GDP growth ~ spending (positive), taxes (negative), rates (negative).
    Baseline: 1.0% (weak UK growth circa 2024).
    """
    base = 1.0
    # Fiscal multiplier ~0.5 for govt spending
    spend_effect = (params["govt_spend_gdp_pct"] - CURRENT_POLICY["govt_spend_gdp_pct"]) * 0.5
    # Corp tax: 1pp rise reduces investment/growth ~0.1pp (IMF)
    corp_effect  = -(params["corporation_tax_pct"] - CURRENT_POLICY["corporation_tax_pct"]) * 0.1
    # Rate: 1pp rise reduces growth ~0.2pp
    rate_effect  = -(params["bank_rate_pct"] - CURRENT_POLICY["bank_rate_pct"]) * 0.2
    # Income tax: 1pp basic rate rise reduces consumption ~0.05pp GDP growth
    it_effect    = -(params["income_tax_basic_pct"] - CURRENT_POLICY["income_tax_basic_pct"]) * 0.05
    return base + spend_effect + corp_effect + rate_effect + it_effect


def _estimated_unemployment(params: dict) -> float:
    """
    Unemployment ~ GDP growth (negative), rates (positive).
    Baseline: 4.2% (recent UK LFS).
    Okun's Law: 1pp extra GDP growth → ~0.5pp lower unemployment.
    """
    base   = 4.2
    growth = _estimated_gdp_growth(params)
    baseline_growth = 1.0
    growth_diff   = growth - baseline_growth
    growth_effect = -growth_diff * 0.5
    return max(0.0, base + growth_effect)


def _estimated_psnb_gdp(params: dict) -> float:
    """
    PSNB as % GDP ~ spending minus receipts.
    Baseline: 4.5% (OBR forecast 2024-25).
    """
    base = 4.5
    spend_effect  = (params["govt_spend_gdp_pct"] - CURRENT_POLICY["govt_spend_gdp_pct"]) * 0.9
    # Tax receipts: corp tax +1pp → +0.1pp GDP revenue
    corp_receipt  = -(params["corporation_tax_pct"] - CURRENT_POLICY["corporation_tax_pct"]) * 0.1
    # Basic IT +1pp → ~+0.3pp GDP in income tax receipts
    it_receipt    = -(params["income_tax_basic_pct"] - CURRENT_POLICY["income_tax_basic_pct"]) * 0.3
    # VAT +1pp → +0.15pp GDP in VAT receipts
    vat_receipt   = -(params["vat_standard_pct"] - CURRENT_POLICY["vat_standard_pct"]) * 0.15
    # Higher growth also expands tax base: ~0.5pp GDP per 1pp growth
    growth_diff   = _estimated_gdp_growth(params) - 1.0
    growth_receipt = -growth_diff * 0.5
    return base + spend_effect + corp_receipt + it_receipt + vat_receipt + growth_receipt


def _estimated_psnd_gdp(params: dict) -> float:
    """
    Debt-to-GDP ~ cumulative borrowing & nominal GDP.
    Baseline: 98% (rough UK PSND/GDP 2024).
    """
    base  = 98.0
    psnb  = _estimated_psnb_gdp(params)
    # Each 1pp extra borrowing adds ~1pp to debt over medium term
    borrow_effect = (psnb - 4.5) * 1.0
    # Nominal GDP growth erodes debt ratio
    gdp_growth  = _estimated_gdp_growth(params) + _estimated_inflation(params)
    growth_effect = -(gdp_growth - 3.5) * 2.0   # ~2pp debt reduction per 1pp extra nominal GDP
    return max(0.0, base + borrow_effect + growth_effect)


def _estimated_productivity_growth(params: dict) -> float:
    """
    Productivity growth ~ corp tax (negative), investment climate.
    Baseline: 0.5% (UK productivity puzzle).
    """
    base = 0.5
    corp_effect  = -(params["corporation_tax_pct"] - CURRENT_POLICY["corporation_tax_pct"]) * 0.05
    spend_effect = (params["govt_spend_gdp_pct"] - CURRENT_POLICY["govt_spend_gdp_pct"]) * 0.03
    return base + corp_effect + spend_effect


def _estimated_current_account_gdp(params: dict) -> float:
    """
    Current account as % GDP.  Baseline: -3.0%.
    """
    base = -3.0
    # Higher domestic spending → more imports → worse CA
    spend_effect = -(params["govt_spend_gdp_pct"] - CURRENT_POLICY["govt_spend_gdp_pct"]) * 0.1
    # Higher rates → stronger sterling (short run) → worse exports
    rate_effect  = -(params["bank_rate_pct"] - CURRENT_POLICY["bank_rate_pct"]) * 0.1
    return base + spend_effect + rate_effect


def _estimated_real_wage_growth(params: dict) -> float:
    """Real wage growth ~ productivity - inflation."""
    return _estimated_productivity_growth(params) - (_estimated_inflation(params) - 2.0)


# ── Score function ─────────────────────────────────────────────────────────

def compute_score_from_params(param_vector: np.ndarray) -> float:
    """
    Given a parameter vector, compute the composite policy score (0–10).
    This is the objective function for the optimiser (we maximise → negate for minimise).
    """
    params = dict(zip(PARAM_NAMES, param_vector))

    from analysis.policy_scorer import (
        _score_symmetric, _score_lower_better, _score_higher_better,
        TARGETS, WEIGHTS,
    )

    inflation  = _estimated_inflation(params)
    gdp_growth = _estimated_gdp_growth(params)
    unemp      = _estimated_unemployment(params)
    psnb_gdp   = _estimated_psnb_gdp(params)
    psnd_gdp   = _estimated_psnd_gdp(params)
    prod_growth = _estimated_productivity_growth(params)
    ca_gdp     = _estimated_current_account_gdp(params)
    rw_growth  = _estimated_real_wage_growth(params)

    scores = {
        "cpi_inflation":  _score_symmetric(inflation,  TARGETS["cpi_inflation_target_pct"],  1.0),
        "gdp_growth":     _score_higher_better(gdp_growth, TARGETS["gdp_growth_target_pct"], 1.0),
        "unemployment":   _score_lower_better(unemp,  TARGETS["unemployment_target_pct"],    1.0),
        "fiscal_balance": _score_lower_better(psnb_gdp, TARGETS["psnb_gdp_pct_target"],      1.0),
        "public_debt":    _score_lower_better(psnd_gdp, TARGETS["psnd_gdp_pct_target"],      10.0),
        "productivity":   _score_higher_better(prod_growth, TARGETS["productivity_growth_target_pct"], 1.0),
        "current_account": _score_higher_better(ca_gdp, TARGETS["current_account_gdp_pct_floor"], 2.0),
        "real_wages":     _score_higher_better(rw_growth, TARGETS["real_wage_growth_target_pct"], 1.0),
    }

    composite = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    return composite


def _negative_score(param_vector: np.ndarray) -> float:
    """Negated score for use with scipy minimize (which minimises)."""
    return -compute_score_from_params(param_vector)


def run() -> dict:
    utils.print_section("Policy Optimiser — Finding Optimal Parameters")

    # ── Baseline score ─────────────────────────────────────────────────────
    baseline_vector = np.array([CURRENT_POLICY[p] for p in PARAM_NAMES])
    baseline_score  = compute_score_from_params(baseline_vector)

    utils.console.print(f"\n  Baseline policy score : [bold]{baseline_score:.2f}/10[/bold]")
    utils.console.print("  Running global optimisation (differential evolution) …\n")

    # ── Global optimisation ────────────────────────────────────────────────
    result_global = differential_evolution(
        _negative_score,
        bounds=BOUNDS,
        seed=42,
        maxiter=500,
        tol=1e-6,
        workers=1,
        disp=False,
        polish=True,
    )

    if not result_global.success:
        utils.log_error(
            "Differential evolution did not fully converge",
            extra=result_global.message,
        )
        utils.console.print(
            f"[yellow]WARNING:[/yellow] Optimiser message: {result_global.message}"
        )

    opt_vector = result_global.x
    opt_score  = compute_score_from_params(opt_vector)
    opt_params = dict(zip(PARAM_NAMES, opt_vector.tolist()))

    # ── Local refinement ──────────────────────────────────────────────────
    result_local = minimize(
        _negative_score,
        opt_vector,
        method="L-BFGS-B",
        bounds=BOUNDS,
        options={"maxiter": 1000, "ftol": 1e-9},
    )
    if result_local.fun < result_global.fun:
        opt_vector = result_local.x
        opt_score  = compute_score_from_params(opt_vector)
        opt_params = dict(zip(PARAM_NAMES, opt_vector.tolist()))

    improvement = opt_score - baseline_score

    # ── Terminal summary ───────────────────────────────────────────────────
    utils.console.print("\n[bold green]═══ OPTIMISATION RESULTS ═══[/bold green]")
    utils.console.print(f"\n  {'Parameter':<35} {'Current':>10} {'Optimal':>10} {'Change':>10}")
    utils.console.print("  " + "─" * 65)

    for pname in PARAM_NAMES:
        curr = CURRENT_POLICY[pname]
        opt  = opt_params[pname]
        diff = opt - curr
        color = "green" if abs(diff) > 0.1 else "white"
        utils.console.print(
            f"  [{color}]{pname:<35}[/{color}] {curr:>10.2f} {opt:>10.2f} [{color}]{diff:>+10.2f}[/{color}]"
        )

    utils.console.print("  " + "─" * 65)
    utils.console.print(f"\n  Baseline composite score : [bold]{baseline_score:.2f}/10[/bold]")
    utils.console.print(f"  Optimal  composite score : [bold green]{opt_score:.2f}/10[/bold green]")
    utils.console.print(f"  Improvement              : [bold green]{improvement:+.2f}[/bold green]")

    # Estimate model outputs under optimal params
    opt_dict = dict(zip(PARAM_NAMES, opt_vector))
    utils.console.print("\n  [bold]Estimated outcomes under optimal policy:[/bold]")
    utils.print_summary([
        ("CPI Inflation (%)",          f"{_estimated_inflation(opt_dict):.2f}"),
        ("GDP Growth (%)",             f"{_estimated_gdp_growth(opt_dict):.2f}"),
        ("Unemployment (%)",           f"{_estimated_unemployment(opt_dict):.2f}"),
        ("PSNB (% GDP)",               f"{_estimated_psnb_gdp(opt_dict):.2f}"),
        ("PSND (% GDP)",               f"{_estimated_psnd_gdp(opt_dict):.2f}"),
        ("Productivity Growth (%)",    f"{_estimated_productivity_growth(opt_dict):.2f}"),
        ("Current Account (% GDP)",    f"{_estimated_current_account_gdp(opt_dict):.2f}"),
        ("Real Wage Growth (%)",       f"{_estimated_real_wage_growth(opt_dict):.2f}"),
    ])

    results = {
        "baseline_score": baseline_score,
        "optimal_score":  opt_score,
        "improvement":    improvement,
        "current_policy": CURRENT_POLICY,
        "optimal_policy": opt_params,
        "convergence":    result_global.success,
        "estimated_outcomes": {
            "inflation":     _estimated_inflation(opt_dict),
            "gdp_growth":    _estimated_gdp_growth(opt_dict),
            "unemployment":  _estimated_unemployment(opt_dict),
            "psnb_gdp":      _estimated_psnb_gdp(opt_dict),
            "psnd_gdp":      _estimated_psnd_gdp(opt_dict),
            "productivity":  _estimated_productivity_growth(opt_dict),
            "current_account": _estimated_current_account_gdp(opt_dict),
            "real_wages":    _estimated_real_wage_growth(opt_dict),
        },
    }

    out_path = config.PROCESSED_DIR / "optimisation_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    utils.console.print(f"\n  [green]Saved[/green] → {out_path}")

    utils.console.print("[bold green]\nOptimisation complete.[/bold green]\n")
    return results


if __name__ == "__main__":
    run()

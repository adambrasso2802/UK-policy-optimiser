"""
Economic impact modeller for UK priority policies.

Applies fiscal multipliers (OBR/IMF literature), supply-side elasticities (OECD),
and distributional analysis (ONS household income data) to each of the top 20
priority policies.  All assumptions are explicitly labelled.
"""

import json
import math
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
RANKINGS_PATH = BASE_DIR / "data/processed/policy_rankings.json"
BASELINE_PATH = BASE_DIR / "data/processed/uk_baseline.json"
OUTPUT_PATH   = BASE_DIR / "data/processed/economic_model.json"

# ---------------------------------------------------------------------------
# Guard: abort early if source files are missing
# ---------------------------------------------------------------------------

missing = [p for p in (RANKINGS_PATH, BASELINE_PATH) if not p.exists()]
if missing:
    print("\n*** ALERT — INPUT DATA FILES MISSING ***")
    for p in missing:
        print(f"  {p}")
    print("Cannot proceed.  Please run the pipeline stages that produce these files.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Load source data
# ---------------------------------------------------------------------------

with open(RANKINGS_PATH) as f:
    rankings_data = json.load(f)

with open(BASELINE_PATH) as f:
    baseline_data = json.load(f)

priority_policies = rankings_data["priority_policies"][:20]
baseline_metrics  = baseline_data["metrics"]

# ---------------------------------------------------------------------------
# Baseline values (from ONS / OBR)
# ---------------------------------------------------------------------------

BASELINE = {
    # Current (2025) annual GDP growth rate
    "gdp_growth_rate":   1.4,
    # OBR central 10-year average forecast (March 2025 EFO projection: 1.5–1.8 %)
    "obr_forecast_avg":  1.6,
    # Gini coefficient on equivalised disposable household income (ONS FYE 2024)
    "gini":              0.329,
    # Relative poverty rate — % households below 60 % median income (ONS FYE 2023)
    "poverty_rate":      18.0,
    # Income shares (ONS ETB 2024)
    "bottom_quintile_share_pct": 7.5,   # approx. from S80/S20 = 5.6, bottom decile 3 %
    "top_quintile_share_pct":    42.0,
    # UK population (mid-2024 ONS estimate, millions of people in households)
    "population_m":      67.1,
    # UK GDP (nominal, 2025, £ bn) — OBR March 2025
    "gdp_gbp_bn":        2_700,
    # Current OECD GDP-per-capita rank (out of 38; 1 = richest)
    "oecd_rank":         18,
}

# Number of people in poverty = poverty_rate / 100 * population
PEOPLE_IN_POVERTY_M = BASELINE["poverty_rate"] / 100 * BASELINE["population_m"]

# ---------------------------------------------------------------------------
# Policy-specific impact parameters
# ─────────────────────────────────────────────────────────────────────────
# Each entry is keyed on the policy 'id' field in policy_rankings.json.
#
# Parameters:
#   gdp_multiplier   – Keynesian fiscal multiplier applied to net spend
#                      (OBR Working Paper 13 / IMF WP/12/190; range 0.5–1.8)
#   gdp_supply_pct   – Additional long-run supply-side GDP level effect (%)
#                      arising from structural / behavioural changes
#                      (OECD Economic Outlook elasticity studies)
#   supply_years     – Years over which supply-side gains are phased in
#   poverty_delta    – Change in poverty rate (pp).  Negative = reduction.
#   gini_delta       – Change in Gini coefficient.  Negative = reduction.
#   bottom_q_delta   – Change in bottom quintile income share (pp)
#   top_q_delta      – Change in top quintile income share (pp)
#   phasing_years    – Full implementation period (policy not at full speed
#                      until this many years have elapsed)
#   notes            – Free-text source/assumption notes
# ---------------------------------------------------------------------------

POLICY_PARAMS = {
    "universal_childcare": {
        "gdp_multiplier":    1.3,   # Social investment multiplier (IMF WP/14/174)
        "gdp_supply_pct":    2.0,   # +1.5–2.5 % GDP from FLFP rise (IFS Deaton Review 2026; OECD 2023 Denmark/Sweden evidence)
        "supply_years":      8,
        "poverty_delta":    -1.8,   # Single-parent households gain most; Denmark child poverty 6.6 %
        "gini_delta":       -0.012, # IFS: early-years investment highest-return inequality reducer; IGE compression
        "bottom_q_delta":    0.4,
        "top_q_delta":      -0.3,
        "phasing_years":     4,
        "notes": "FLFP elasticity from OECD; multiplier from IMF WP/14/174; Gini from IFS Deaton Review 2026 igp compression.",
    },
    "universal_credit_reform": {
        "gdp_multiplier":    0.9,   # Transfer multiplier (OBR WP13 range 0.5–1.0)
        "gdp_supply_pct":    0.4,   # Labour supply from lower taper rate (RF/IFS estimates)
        "supply_years":      5,
        "poverty_delta":    -2.4,   # Removing 5-week wait + taper cut: RF projects ~500k lifted (= ~0.75 % pop); two-child interacts
        "gini_delta":       -0.010,
        "bottom_q_delta":    0.5,
        "top_q_delta":      -0.1,
        "phasing_years":     2,
        "notes": "Resolution Foundation 2024; taper cut from 55 % to 45 % adds labour supply; DWP modelling.",
    },
    "land_value_tax": {
        "gdp_multiplier":    0.0,   # Revenue-raising (net £28 bn); multiplier applies to redistribution of receipts
        "gdp_supply_pct":    0.5,   # Reduces land-banking; improves capital allocation (OECD Tax Policy Studies No. 20)
        "supply_years":      7,
        "poverty_delta":    -0.8,   # Lower rents/purchase prices reduce housing cost poverty
        "gini_delta":       -0.008,
        "bottom_q_delta":    0.2,
        "top_q_delta":      -0.6,   # Wealth concentration in land; LVT redistributive
        "phasing_years":     5,
        "notes": "OECD Tax Policy Studies No. 20 LVT GDP neutral in static sense but improves allocative efficiency; Mirrlees Review.",
    },
    "government_housing_construction": {
        "gdp_multiplier":    1.4,   # Construction has highest demand multiplier (OBR/HMT)
        "gdp_supply_pct":    0.3,   # Labour mobility from lower housing costs (OBR Long-run model)
        "supply_years":      10,
        "poverty_delta":    -1.5,
        "gini_delta":       -0.008,
        "bottom_q_delta":    0.3,
        "top_q_delta":      -0.1,
        "phasing_years":     5,
        "notes": "Construction multiplier OBR WP13; 300k/yr homes requires 5-yr ramp; labour mobility elasticity from OECD ECO/WKP(2019)1.",
    },
    "social_housing_investment": {
        "gdp_multiplier":    1.3,
        "gdp_supply_pct":    0.2,
        "supply_years":      10,
        "poverty_delta":    -2.5,   # Social housing lifts lowest-income households; most direct poverty intervention
        "gini_delta":       -0.018,
        "bottom_q_delta":    0.6,
        "top_q_delta":      -0.2,
        "phasing_years":     5,
        "notes": "Shelter/CIH evidence; social rent at 50% market rate directly reduces housing cost ratio for lowest quintile.",
    },
    "esep_single_market": {
        "gdp_multiplier":    0.0,   # Trade reform; static multiplier not applicable
        "gdp_supply_pct":    2.8,   # LSE/CEP Brexit cost estimate 4–6 % GDP by 2035; re-entry recovers ~50% = 2–3% over 10 yrs
        "supply_years":      10,
        "poverty_delta":    -1.0,   # Lower food/import prices; IFS estimates 2–4 % higher consumer prices from Brexit
        "gini_delta":       -0.006,
        "bottom_q_delta":    0.2,
        "top_q_delta":       0.0,
        "phasing_years":     6,
        "notes": "Dhingra et al. (LSE/CEP) 2024; Springford (CER) 2024; trade openness elasticity to GDP 0.3–0.5 (OECD).",
    },
    "two_child_limit_removal": {
        "gdp_multiplier":    0.85,
        "gdp_supply_pct":    0.0,
        "supply_years":      3,
        "poverty_delta":    -1.4,   # ~400k children in poverty attributable to two-child limit (JRF 2024)
        "gini_delta":       -0.007,
        "bottom_q_delta":    0.3,
        "top_q_delta":       0.0,
        "phasing_years":     1,
        "notes": "JRF/RF 2024: 400k children; immediate implementation possible.",
    },
    "youth_guarantee": {
        "gdp_multiplier":    1.1,
        "gdp_supply_pct":    0.2,   # 750k NEETs; if 50% engaged → ~375k additional in labour market
        "supply_years":      5,
        "poverty_delta":    -0.8,
        "gini_delta":       -0.005,
        "bottom_q_delta":    0.2,
        "top_q_delta":       0.0,
        "phasing_years":     3,
        "notes": "IPPR/Young Foundation 2024; NEET cost to economy £6.5bn/yr (IPPR).",
    },
    "nhs_funding_uplift": {
        "gdp_multiplier":    1.1,   # Healthcare multiplier (IMF Fiscal Monitor 2014)
        "gdp_supply_pct":    0.3,   # Healthier workforce productivity; reduced waiting list drag
        "supply_years":      8,
        "poverty_delta":    -0.7,   # Health poverty link; catastrophic health costs
        "gini_delta":       -0.007,
        "bottom_q_delta":    0.2,
        "top_q_delta":       0.0,
        "phasing_years":     4,
        "notes": "OBR health productivity estimates; IMF Fiscal Monitor 2014; NHS waiting list economic cost £15bn (HMT).",
    },
    "flexicurity_reform": {
        "gdp_multiplier":    1.0,
        "gdp_supply_pct":    1.0,   # Danish flexicurity → 2pp employment rate → ~0.8% GDP (OECD Jobs Studies)
        "supply_years":      8,
        "poverty_delta":    -1.5,
        "gini_delta":       -0.014,
        "bottom_q_delta":    0.5,
        "top_q_delta":      -0.2,
        "phasing_years":     6,
        "notes": "Andersen & Svarer (2007); OECD Jobs Strategy 2018; Danish vs UK unemployment/poverty comparison.",
    },
    "fe_college_funding": {
        "gdp_multiplier":    1.1,
        "gdp_supply_pct":    0.2,   # FE skills uplift; NIESR estimates £3bn FE = 0.1–0.15% GDP long run
        "supply_years":      8,
        "poverty_delta":    -0.7,
        "gini_delta":       -0.007,
        "bottom_q_delta":    0.3,
        "top_q_delta":      -0.1,
        "phasing_years":     3,
        "notes": "NIESR 2023; AoC 2024; education multiplier OBR-consistent.",
    },
    "rd_spending_increase": {
        "gdp_multiplier":    0.8,   # R&D grants; crowding-in private R&D
        "gdp_supply_pct":    0.5,   # OECD estimates R&D social rate of return 20–40%; R&D share → TFP
        "supply_years":      10,
        "poverty_delta":    -0.2,
        "gini_delta":        0.002, # Tech premium may widen initially; small positive (more inequality)
        "bottom_q_delta":    0.0,
        "top_q_delta":       0.1,
        "phasing_years":     5,
        "notes": "OECD Science Technology Scoreboard; Hall et al. (2010) R&D elasticities; R&D → productivity with 5yr lag.",
    },
    "electricity_market_decoupling": {
        "gdp_multiplier":    0.0,   # Regulatory reform; no net fiscal cost
        "gdp_supply_pct":    0.3,   # Lower industrial energy costs → productivity; DESNZ estimate £350/household saving
        "supply_years":      4,
        "poverty_delta":    -0.9,   # Energy poverty reduction; 3.1m households in fuel poverty (DESNZ 2024)
        "gini_delta":       -0.005,
        "bottom_q_delta":    0.2,
        "top_q_delta":       0.0,
        "phasing_years":     2,
        "notes": "DESNZ Electricity Market Reform 2024; gas-electricity price decoupling per Ofgem modelling.",
    },
    "universal_free_school_meals": {
        "gdp_multiplier":    0.85,
        "gdp_supply_pct":    0.05,  # Child nutrition → long-run productivity (Grantham-McGregor 2007)
        "supply_years":      20,    # Long generational payoff
        "poverty_delta":    -0.7,   # In-kind transfer; Magic Breakfast evidence; IFS child poverty analysis
        "gini_delta":       -0.004,
        "bottom_q_delta":    0.15,
        "top_q_delta":       0.0,
        "phasing_years":     1,
        "notes": "IFS 2023; Magic Breakfast research; SACN nutrition evidence.",
    },
    "apprenticeship_levy_reform": {
        "gdp_multiplier":    0.0,   # Revenue-neutral reform
        "gdp_supply_pct":    0.2,
        "supply_years":      6,
        "poverty_delta":    -0.5,
        "gini_delta":       -0.004,
        "bottom_q_delta":    0.15,
        "top_q_delta":       0.0,
        "phasing_years":     3,
        "notes": "IfATE 2024; CIPD apprenticeship quality studies; 600k genuine starts vs current box-ticking levy use.",
    },
    "vocational_education_overhaul": {
        "gdp_multiplier":    0.9,
        "gdp_supply_pct":    0.2,
        "supply_years":      8,
        "poverty_delta":    -0.5,
        "gini_delta":       -0.005,
        "bottom_q_delta":    0.2,
        "top_q_delta":       0.0,
        "phasing_years":     4,
        "notes": "Netherlands MBO model; T-levels OFSTED evaluations; OECD VET at a Glance 2023.",
    },
    "skills_future_adult_training": {
        "gdp_multiplier":    0.9,
        "gdp_supply_pct":    0.15,
        "supply_years":      8,
        "poverty_delta":    -0.4,
        "gini_delta":       -0.004,
        "bottom_q_delta":    0.15,
        "top_q_delta":       0.0,
        "phasing_years":     3,
        "notes": "Singapore SkillsFuture evaluation (MOM 2023); adult retraining elasticity to earnings.",
    },
    "fiscal_devolution": {
        "gdp_multiplier":    0.0,   # Revenue-neutral; reforms assignment not total spend
        "gdp_supply_pct":    0.3,   # Agglomeration + local investment efficiency (LSE Cities 2024)
        "supply_years":      10,
        "poverty_delta":    -0.4,
        "gini_delta":       -0.004,
        "bottom_q_delta":    0.1,
        "top_q_delta":       0.0,
        "phasing_years":     5,
        "notes": "Centre for Cities 2024; Manchester devolution evaluation; OECD regional development elasticities.",
    },
    "social_care_integration": {
        "gdp_multiplier":    1.1,
        "gdp_supply_pct":    0.15,  # Unpaid carer release into labour market
        "supply_years":      6,
        "poverty_delta":    -0.7,
        "gini_delta":       -0.006,
        "bottom_q_delta":    0.2,
        "top_q_delta":       0.0,
        "phasing_years":     3,
        "notes": "Carers UK 2024: 4.3m carers, economic cost £132bn; ADASS integration savings; Dilnot review.",
    },
    "planning_reform": {
        "gdp_multiplier":    1.2,
        "gdp_supply_pct":    0.35,  # Housing supply → labour mobility → productivity; OBR planning counterfactual
        "supply_years":      10,
        "poverty_delta":    -0.8,
        "gini_delta":       -0.006,
        "bottom_q_delta":    0.2,
        "top_q_delta":      -0.1,
        "phasing_years":     5,
        "notes": "OBR Fiscal Risks Report 2023; Hilber & Vermeulen (2016) planning constraints cost 2% GDP; zoning reform evidence (New Zealand).",
    },
}

# ---------------------------------------------------------------------------
# Modelling helpers
# ---------------------------------------------------------------------------

def phase_factor(year: int, phasing_years: int) -> float:
    """Linear ramp-up: fraction of full effect delivered by this year."""
    return min(1.0, year / phasing_years)


def gdp_demand_effect(cost_bn: float, multiplier: float, gdp_bn: float) -> float:
    """Annual demand-side GDP growth uplift (pp) from a spending change."""
    # Spend as % of GDP × multiplier → GDP level effect
    # We treat this as a one-off level effect during the spending period,
    # translated into an average annual growth rate uplift over 10 years.
    spend_pct_gdp = (cost_bn / gdp_bn) * 100
    level_effect   = spend_pct_gdp * multiplier
    # Amortise over 10 years as a growth rate addition
    return level_effect / 10.0


def gdp_supply_annual(supply_pct: float, supply_years: int) -> float:
    """Average annual GDP growth uplift (pp) from supply-side level gain."""
    # supply_pct = total GDP level gain accumulated over supply_years
    # Convert to average annual growth contribution
    return supply_pct / supply_years


def confidence_interval(central: float, spread_pct: float = 0.40) -> dict:
    """Symmetric ± spread around central as low/high."""
    return {
        "low":     round(central * (1 - spread_pct), 4),
        "central": round(central, 4),
        "high":    round(central * (1 + spread_pct), 4),
    }


IMPLAUSIBILITY_THRESHOLD_GDP = 5.0   # pp above baseline annual growth

# ---------------------------------------------------------------------------
# Per-policy modelling
# ---------------------------------------------------------------------------

def model_policy(policy: dict) -> dict:
    pid   = policy["id"]
    name  = policy["name"]
    cost  = policy.get("cost_gbp_bn_yr", 0.0)
    params = POLICY_PARAMS.get(pid)

    if params is None:
        return {
            "id": pid,
            "name": name,
            "error": f"No modelling parameters defined for policy id '{pid}'",
        }

    phasing   = params["phasing_years"]
    mult      = params["gdp_multiplier"]
    supply_pct = params["gdp_supply_pct"]
    sup_yrs   = params["supply_years"]

    # ── GDP ──────────────────────────────────────────────────────────────────
    demand_annual = gdp_demand_effect(abs(cost), mult, BASELINE["gdp_gbp_bn"])
    supply_annual = gdp_supply_annual(supply_pct, sup_yrs)
    total_annual_central = demand_annual + supply_annual

    # Scenarios: low = 60 %, high = 140 % of central
    gdp_annual = {
        "low":     round(total_annual_central * 0.60, 4),
        "central": round(total_annual_central, 4),
        "high":    round(total_annual_central * 1.40, 4),
    }

    # 10-year cumulative GDP level gain (%)
    # Phase-adjusted: effect ramps up over phasing_years then runs at full rate
    cumulative_10yr = 0.0
    for yr in range(1, 11):
        pf = phase_factor(yr, phasing)
        cumulative_10yr += total_annual_central * pf
    cumulative_10yr_ci = confidence_interval(cumulative_10yr, 0.40)

    # GDP growth rate trajectories vs OBR baseline
    obr_baseline_rate = BASELINE["obr_forecast_avg"]
    projected_growth  = {
        "low":     round(obr_baseline_rate + gdp_annual["low"],     2),
        "central": round(obr_baseline_rate + gdp_annual["central"], 2),
        "high":    round(obr_baseline_rate + gdp_annual["high"],    2),
    }

    # Plausibility check
    implausibility_flag = None
    if gdp_annual["high"] > IMPLAUSIBILITY_THRESHOLD_GDP:
        implausibility_flag = (
            f"HIGH GDP ESTIMATE: {gdp_annual['high']:.2f} pp above baseline "
            f"exceeds {IMPLAUSIBILITY_THRESHOLD_GDP} pp threshold — flag for expert review."
        )

    # ── Poverty ──────────────────────────────────────────────────────────────
    poverty_delta_central = params["poverty_delta"]
    poverty_new           = BASELINE["poverty_rate"] + poverty_delta_central
    people_lifted_m       = abs(poverty_delta_central) / 100 * BASELINE["population_m"]

    poverty = {
        "baseline_pct":           BASELINE["poverty_rate"],
        "projected_pct":          confidence_interval(poverty_new, 0.35),
        "change_pp":              confidence_interval(poverty_delta_central, 0.35),
        "people_lifted_m":        confidence_interval(people_lifted_m, 0.35),
        "assumption": (
            "Poverty = % households below 60% median equivalised disposable income (ONS). "
            "Effect size from policy-specific evidence; assumes behaviour change occurs within phasing period."
        ),
    }

    # ── Inequality ────────────────────────────────────────────────────────────
    gini_delta   = params["gini_delta"]
    gini_new     = BASELINE["gini"] + gini_delta
    bq_delta     = params["bottom_q_delta"]
    tq_delta     = params["top_q_delta"]

    inequality = {
        "gini_baseline":     BASELINE["gini"],
        "gini_projected":    confidence_interval(gini_new, 0.30),
        "gini_change":       confidence_interval(gini_delta, 0.30),
        "bottom_quintile_share_pct_baseline": BASELINE["bottom_quintile_share_pct"],
        "bottom_quintile_share_pct_projected": confidence_interval(
            BASELINE["bottom_quintile_share_pct"] + bq_delta, 0.30
        ),
        "top_quintile_share_pct_baseline": BASELINE["top_quintile_share_pct"],
        "top_quintile_share_pct_projected": confidence_interval(
            BASELINE["top_quintile_share_pct"] + tq_delta, 0.30
        ),
        "assumption": (
            "Gini delta estimated from comparable international reforms and distributional microsimulation "
            "literature.  Quintile shares from ONS ETB; changes proportional to targeted benefit/cost incidence."
        ),
    }

    result = {
        "id":   pid,
        "rank": policy["rank"],
        "name": name,
        "cluster": policy.get("cluster", ""),
        "cost_gbp_bn_yr": cost,
        "composite_score": policy.get("composite_score"),
        "gdp_impact": {
            "annual_growth_uplift_pp": gdp_annual,
            "cumulative_10yr_gdp_level_gain_pct": cumulative_10yr_ci,
            "projected_10yr_avg_growth_rate_pct": projected_growth,
            "obr_baseline_rate_pct": obr_baseline_rate,
            "phasing_years": phasing,
            "assumptions": {
                "fiscal_multiplier": mult,
                "supply_side_gdp_gain_pct": supply_pct,
                "supply_side_phasing_years": sup_yrs,
                "notes": params["notes"],
                "source": "OBR Working Paper 13; IMF WP/12/190; OECD Economic Outlook elasticities",
            },
        },
        "poverty_impact":    poverty,
        "inequality_impact": inequality,
    }

    if implausibility_flag:
        result["ALERT"] = implausibility_flag

    return result


# ---------------------------------------------------------------------------
# Run individual models
# ---------------------------------------------------------------------------

print("Running economic models for top 20 priority policies …\n")
policy_models = []
alerts = []

for policy in priority_policies:
    m = model_policy(policy)
    policy_models.append(m)
    if "ALERT" in m:
        alerts.append(f"[{m.get('rank','?')}] {m.get('name','?')}: {m['ALERT']}")
    if "error" in m:
        alerts.append(f"[{m.get('rank','?')}] {m.get('name', m.get('id','?'))}: MISSING PARAMS — {m['error']}")

if alerts:
    print("*** ALERTS — REQUIRES REVIEW ***")
    for a in alerts:
        print(f"  {a}")
    print()

# ---------------------------------------------------------------------------
# Combined scenario: all 20 policies implemented together over 10 years
# ─────────────────────────────────────────────────────────────────────────
# Interaction discount applied:
#   - 15% crowding-out / macroeconomic constraint discount on GDP
#   - 10% diminishing-returns discount on poverty/Gini (poorest already
#     lifted by multiple programmes)
# These discounts are deliberately conservative.
# ---------------------------------------------------------------------------

INTERACTION_GDP_DISCOUNT   = 0.15
INTERACTION_DIST_DISCOUNT  = 0.10

# Sum individual central estimates then discount
total_gdp_annual_central = sum(
    m["gdp_impact"]["annual_growth_uplift_pp"]["central"]
    for m in policy_models if "gdp_impact" in m
)
total_gdp_annual_central_adj = total_gdp_annual_central * (1 - INTERACTION_GDP_DISCOUNT)

# Cumulative 10-yr GDP level
# Use the individual policy phase-adjusted contributions but with discount
total_cumulative_10yr = sum(
    m["gdp_impact"]["cumulative_10yr_gdp_level_gain_pct"]["central"]
    for m in policy_models if "gdp_impact" in m
) * (1 - INTERACTION_GDP_DISCOUNT)

combined_projected_growth = {
    "low":     round(BASELINE["obr_forecast_avg"] + total_gdp_annual_central_adj * 0.60, 2),
    "central": round(BASELINE["obr_forecast_avg"] + total_gdp_annual_central_adj, 2),
    "high":    round(BASELINE["obr_forecast_avg"] + total_gdp_annual_central_adj * 1.40, 2),
}

# Poverty: sum deltas with discount; floor at 5 % (structural minimum)
total_poverty_delta = sum(
    m["poverty_impact"]["change_pp"]["central"]
    for m in policy_models if "poverty_impact" in m
) * (1 - INTERACTION_DIST_DISCOUNT)
combined_poverty_pct = max(5.0, BASELINE["poverty_rate"] + total_poverty_delta)
combined_people_lifted_m = abs(total_poverty_delta) / 100 * BASELINE["population_m"]

# Gini: sum deltas with discount; floor at 0.25 (Nordic best practice)
total_gini_delta = sum(
    m["inequality_impact"]["gini_change"]["central"]
    for m in policy_models if "inequality_impact" in m
) * (1 - INTERACTION_DIST_DISCOUNT)
combined_gini = max(0.25, BASELINE["gini"] + total_gini_delta)

# Bottom/top quintile share changes
total_bq_delta = sum(
    (m["inequality_impact"]["bottom_quintile_share_pct_projected"]["central"]
     - m["inequality_impact"]["bottom_quintile_share_pct_baseline"])
    for m in policy_models if "inequality_impact" in m
) * (1 - INTERACTION_DIST_DISCOUNT)
total_tq_delta = sum(
    (m["inequality_impact"]["top_quintile_share_pct_projected"]["central"]
     - m["inequality_impact"]["top_quintile_share_pct_baseline"])
    for m in policy_models if "inequality_impact" in m
) * (1 - INTERACTION_DIST_DISCOUNT)

combined_bq_share = min(15.0, BASELINE["bottom_quintile_share_pct"] + total_bq_delta)
combined_tq_share = max(30.0, BASELINE["top_quintile_share_pct"] + total_tq_delta)

# OECD ranking projection:
# Current rank 18/38.  GDP per-capita improvement of ~total_cumulative_10yr % over 10 yrs.
# UK roughly at OECD average; each ~3 pp of cumulative GDP improvement ≈ 1 rank climb.
rank_improvement = int(total_cumulative_10yr / 3.0)
combined_oecd_rank = max(8, BASELINE["oecd_rank"] - rank_improvement)

# Plausibility check for combined scenario
combined_alerts = []
if combined_projected_growth["high"] > BASELINE["obr_forecast_avg"] + IMPLAUSIBILITY_THRESHOLD_GDP:
    combined_alerts.append(
        f"Combined HIGH scenario GDP growth {combined_projected_growth['high']:.2f} % "
        f"exceeds plausibility threshold — flag for review."
    )

combined_scenario = {
    "description": (
        "All 20 priority policies implemented together over 10 years (2026–2035). "
        "A 15% interaction/crowding-out discount applied to GDP; "
        "10% diminishing-returns discount applied to distributional impacts."
    ),
    "total_net_annual_cost_gbp_bn": round(sum(p.get("cost_gbp_bn_yr", 0) for p in priority_policies), 1),
    "gdp": {
        "annual_growth_uplift_pp_adj":   round(total_gdp_annual_central_adj, 3),
        "cumulative_10yr_level_gain_pct": round(total_cumulative_10yr, 2),
        "projected_avg_growth_rate_pct": combined_projected_growth,
        "obr_baseline_pct":              BASELINE["obr_forecast_avg"],
        "interaction_discount_applied":  f"{int(INTERACTION_GDP_DISCOUNT*100)}%",
    },
    "poverty_2035": {
        "projected_rate_pct":             round(combined_poverty_pct, 1),
        "baseline_rate_pct":              BASELINE["poverty_rate"],
        "change_pp":                      round(total_poverty_delta, 1),
        "people_lifted_above_poverty_m":  round(combined_people_lifted_m, 2),
        "diminishing_returns_discount":   f"{int(INTERACTION_DIST_DISCOUNT*100)}%",
    },
    "inequality_2035": {
        "projected_gini":               round(combined_gini, 3),
        "baseline_gini":                BASELINE["gini"],
        "gini_change":                  round(total_gini_delta, 3),
        "gini_narrative": (
            f"Gini falls from {BASELINE['gini']} to approximately {combined_gini:.3f} "
            f"(a reduction of {abs(total_gini_delta):.3f} Gini points), "
            f"moving UK from current level towards Nordic peer group (Denmark 0.29, Sweden 0.27)."
        ),
        "projected_bottom_quintile_share_pct": round(combined_bq_share, 1),
        "projected_top_quintile_share_pct":    round(combined_tq_share, 1),
        "baseline_bottom_quintile_share_pct":  BASELINE["bottom_quintile_share_pct"],
        "baseline_top_quintile_share_pct":     BASELINE["top_quintile_share_pct"],
    },
    "oecd_ranking_2035": {
        "projected_rank":      combined_oecd_rank,
        "baseline_rank":       BASELINE["oecd_rank"],
        "rank_improvement":    rank_improvement,
        "note": (
            f"Estimated improvement of {rank_improvement} places in OECD GDP-per-capita ranking "
            f"(from ~{BASELINE['oecd_rank']} to ~{combined_oecd_rank} out of 38 members). "
            "Based on cumulative GDP level gains relative to OECD average growth trajectory. "
            "Ranking is illustrative; assumes peer nations do not implement equivalent reforms."
        ),
    },
    "alerts": combined_alerts,
    "assumptions": {
        "interaction_discount_gdp":  "15% — crowd-out from fiscal constraint and labour market capacity",
        "interaction_discount_dist": "10% — diminishing returns when multiple programmes target same households",
        "oecd_rank_method":          "~3pp cumulative GDP level gain ≈ 1 OECD rank place (illustrative)",
        "floor_poverty_pct":         "5% — structural minimum (no country with market economy below ~4–5%)",
        "floor_gini":                "0.25 — Nordic best practice (Denmark 2024 Gini ~0.29)",
    },
}

# ---------------------------------------------------------------------------
# Assemble full output
# ---------------------------------------------------------------------------

output = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "description": "Economic impact model for top 20 UK priority policies",
    "methodology": {
        "gdp":        "Keynesian fiscal multipliers (OBR WP13; IMF WP/12/190) + supply-side elasticities (OECD)",
        "poverty":    "Change in % households below 60% median equivalised disposable income (ONS definition)",
        "inequality": "Gini coefficient change (ONS ETB series); quintile income share shifts",
        "combined":   "Sum of individual effects with interaction/crowding-out discounts; 10-year horizon to 2035",
        "scenarios":  "Low = 60% of central, High = 140% of central; all labelled with confidence intervals",
    },
    "baseline": {
        "gdp_growth_2025_pct":        BASELINE["gdp_growth_rate"],
        "obr_10yr_avg_forecast_pct":  BASELINE["obr_forecast_avg"],
        "gini_2024":                  BASELINE["gini"],
        "poverty_rate_2023_pct":      BASELINE["poverty_rate"],
        "people_in_poverty_m":        round(PEOPLE_IN_POVERTY_M, 2),
        "bottom_quintile_share_pct":  BASELINE["bottom_quintile_share_pct"],
        "top_quintile_share_pct":     BASELINE["top_quintile_share_pct"],
        "oecd_rank":                  BASELINE["oecd_rank"],
        "gdp_gbp_bn":                 BASELINE["gdp_gbp_bn"],
        "population_m":               BASELINE["population_m"],
    },
    "policy_models":      policy_models,
    "combined_scenario":  combined_scenario,
    "alerts":             alerts,
}

# ---------------------------------------------------------------------------
# Save output
# ---------------------------------------------------------------------------

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w") as f:
    json.dump(output, f, indent=2)

print(f"Economic model saved → {OUTPUT_PATH}\n")

# ---------------------------------------------------------------------------
# Summary table: top 10 policies
# ---------------------------------------------------------------------------

DIVIDER = "─" * 120

header = (
    f"{'Rk':<3}  {'Policy':<48}  {'Cost':>7}  "
    f"{'GDP uplift (pp/yr)':>18}  {'Poverty Δ (pp)':>14}  "
    f"{'Gini Δ':>8}  {'People lifted (m)':>17}"
)

print("TOP 10 POLICIES — PROJECTED ECONOMIC IMPACT (central estimates)")
print(DIVIDER)
print(header)
print(DIVIDER)

for m in policy_models[:10]:
    if "error" in m:
        print(f"{m['rank']:<3}  {m['name'][:48]:<48}  ERROR: {m['error']}")
        continue

    gdp_c   = m["gdp_impact"]["annual_growth_uplift_pp"]["central"]
    pov_c   = m["poverty_impact"]["change_pp"]["central"]
    gini_c  = m["inequality_impact"]["gini_change"]["central"]
    lifted  = m["poverty_impact"]["people_lifted_m"]["central"]
    cost    = m["cost_gbp_bn_yr"]
    flag    = " ⚠" if "ALERT" in m else ""

    print(
        f"{m['rank']:<3}  {m['name'][:48]:<48}  "
        f"£{cost:>5.1f}bn  "
        f"{gdp_c:>+18.3f}  "
        f"{pov_c:>+14.1f}  "
        f"{gini_c:>+8.3f}  "
        f"{lifted:>17.2f}{flag}"
    )

print(DIVIDER)
print()

# ---------------------------------------------------------------------------
# Combined scenario summary
# ---------------------------------------------------------------------------

cs   = combined_scenario
gdp  = cs["gdp"]
pov  = cs["poverty_2035"]
ineq = cs["inequality_2035"]
oecd = cs["oecd_ranking_2035"]

print("COMBINED SCENARIO: ALL 20 POLICIES IMPLEMENTED (2026–2035)")
print(DIVIDER)
print(f"  Total net annual cost:           £{cs['total_net_annual_cost_gbp_bn']:.1f} bn/yr")
print()
print(f"  GDP — avg growth rate (central): {gdp['projected_avg_growth_rate_pct']['central']:.2f}% "
      f"  [low: {gdp['projected_avg_growth_rate_pct']['low']:.2f}%  "
      f"high: {gdp['projected_avg_growth_rate_pct']['high']:.2f}%]")
print(f"  GDP — OBR baseline:              {gdp['obr_baseline_pct']:.2f}%")
print(f"  GDP — cumulative 10yr level gain:{gdp['cumulative_10yr_level_gain_pct']:.2f}%")
print()
print(f"  Poverty rate 2035 (central):     {pov['projected_rate_pct']:.1f}%  "
      f"(from {pov['baseline_rate_pct']:.1f}%,  Δ {pov['change_pp']:.1f} pp)")
print(f"  People lifted above poverty:     {pov['people_lifted_above_poverty_m']:.2f}m")
print()
print(f"  Gini 2035 (central):             {ineq['projected_gini']:.3f}  "
      f"(from {ineq['baseline_gini']:.3f},  Δ {ineq['gini_change']:.3f})")
print(f"  {ineq['gini_narrative']}")
print()
print(f"  OECD GDP-per-capita rank 2035:   ~{oecd['projected_rank']} / 38  "
      f"(from ~{oecd['baseline_rank']} / 38, ↑ {oecd['rank_improvement']} places)")
print()

if combined_alerts:
    print("  *** COMBINED SCENARIO ALERTS ***")
    for a in combined_alerts:
        print(f"  ⚠  {a}")

if alerts:
    print()
    print("*** INDIVIDUAL POLICY ALERTS (requires expert review) ***")
    for a in alerts:
        print(f"  ⚠  {a}")

print(DIVIDER)
print("\nAll outputs with confidence intervals saved to:", OUTPUT_PATH)

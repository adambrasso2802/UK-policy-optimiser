"""
Gap analysis: UK vs OECD peers.

Inputs:
  data/processed/uk_baseline.json
  data/processed/benchmarks.json
  data/raw/oecd/<ISO3>_policy_reforms.json

Output:
  data/processed/gap_analysis.json
  Formatted table to stdout
"""

import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / "data/processed/uk_baseline.json"
BENCHMARKS_PATH = ROOT / "data/processed/benchmarks.json"
OECD_RAW_DIR = ROOT / "data/raw/oecd"
OUTPUT_PATH = ROOT / "data/processed/gap_analysis.json"

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------
# Each entry: (key, label, field_extractor, higher_is_better, note)
# field_extractor: callable(country_dict) -> float | None
METRICS = [
    {
        "key": "gdp_growth_rate",
        "label": "GDP Growth Rate (5yr avg, %)",
        "extract": lambda c: c["gdp_growth_rate"].get("avg_5yr_2019_2024"),
        "higher_is_better": True,
        "welfare_note": "Sustained growth directly raises living standards and tax revenues for public services.",
        "note": "5-year average 2019-2024 from OECD National Accounts",
    },
    {
        "key": "gini_coefficient",
        "label": "Gini Coefficient",
        "extract": lambda c: c["gini_coefficient"].get("value"),
        "higher_is_better": False,
        "welfare_note": "Lower inequality linked to better health outcomes, social cohesion and intergenerational mobility.",
        "note": "Disposable income Gini, OECD IDD 2022",
    },
    {
        "key": "poverty_rate_pct",
        "label": "Poverty Rate (%)",
        "extract": lambda c: c["poverty_rate_pct"].get("value"),
        "higher_is_better": False,
        "welfare_note": "Direct measure of material deprivation; reducing it improves health, education and life expectancy.",
        "note": "Relative poverty <50% median, OECD IDD 2022",
    },
    {
        "key": "rd_expenditure_pct_gdp",
        "label": "R&D Expenditure (% GDP)",
        "extract": lambda c: c["rd_expenditure_pct_gdp"].get("value"),
        "higher_is_better": True,
        "welfare_note": "R&D drives long-run productivity growth and wage gains through innovation spillovers.",
        "note": "GERD % GDP, OECD MSTI 2023",
    },
    {
        "key": "labour_productivity_usd_ppp",
        "label": "Labour Productivity (USD PPP/hr)",
        "extract": lambda c: c["labour_productivity_usd_ppp"].get("value"),
        "higher_is_better": True,
        "welfare_note": "The single strongest predictor of wages and living standards; UK productivity gap costs ~20% of potential output.",
        "note": "Output per hour worked, USD PPP, OECD PDB_LV 2023. IRL value MNC-distorted.",
        "exclude": ["IRL"],  # MNC distortion
    },
    {
        "key": "public_debt_pct_gdp",
        "label": "Public Debt (% GDP)",
        "extract": lambda c: c["public_debt_pct_gdp"].get("value"),
        "higher_is_better": False,
        "welfare_note": "High debt constrains future investment capacity and raises borrowing costs, limiting welfare spending.",
        "note": "General government gross debt % GDP, OECD EO 2024. SGP excluded (structural difference).",
        "exclude": ["SGP"],  # SGP debt is domestic securities offset by massive assets
    },
    {
        "key": "unemployment_rate_pct",
        "label": "Unemployment Rate (%)",
        "extract": lambda c: c["unemployment_rate_pct"].get("value"),
        "higher_is_better": False,
        "welfare_note": "Unemployment destroys human capital and is linked to poor mental/physical health outcomes.",
        "note": "ILO unemployment, OECD KEI 2024",
    },
    {
        "key": "social_mobility_ige",
        "label": "Social Mobility (IGE)",
        "extract": lambda c: c["social_mobility_ige"].get("ige"),
        "higher_is_better": False,
        "welfare_note": "Lower IGE means earnings are less determined by parental income — fundamental to equality of opportunity.",
        "note": "Intergenerational earnings elasticity; lower = higher mobility. OECD 2023.",
    },
    {
        "key": "govt_effectiveness_wgi",
        "label": "Govt Effectiveness (WGI)",
        "extract": lambda c: c["govt_effectiveness_wgi"].get("value"),
        "higher_is_better": True,
        "welfare_note": "Effective government is the multiplier for all other policies — poor delivery wastes public spending.",
        "note": "World Bank WGI GE.EST 2023; higher = more effective",
    },
    {
        "key": "income_shares_ratio",
        "label": "Income Shares Ratio (top/bottom 10%)",
        "extract": lambda c: c["income_shares"].get("ratio"),
        "higher_is_better": False,
        "welfare_note": "Captures extremes of income distribution; high ratio linked to social tension and reduced mobility.",
        "note": "Ratio of top-decile to bottom-decile income share, OECD IDD 2022",
    },
]

# ---------------------------------------------------------------------------
# Impact × Feasibility ratings
# Hand-assessed, evidence-based
# ---------------------------------------------------------------------------
PRIORITY = {
    "gdp_growth_rate": {
        "impact": 8,
        "impact_reason": (
            "Sustained GDP growth above peers raises wages, tax revenues and public service capacity. "
            "Each 1pp of additional growth sustains ~£25bn of extra annual output over a decade."
        ),
        "feasibility": 5,
        "feasibility_reason": (
            "UK structural weaknesses (investment, skills, planning) are well-documented but politically "
            "contested. Trade policy post-Brexit limits easy wins. Medium-term supply-side reforms are "
            "achievable but slow-acting."
        ),
    },
    "gini_coefficient": {
        "impact": 7,
        "impact_reason": (
            "Reducing inequality improves health, social trust and intergenerational mobility. "
            "Scandinavia shows high welfare and growth are compatible."
        ),
        "feasibility": 4,
        "feasibility_reason": (
            "Requires sustained redistribution and wage policy changes. Politically divisive. "
            "Nordic levels require tax-to-GDP ratios ~10pp above current UK, which faces strong opposition."
        ),
    },
    "poverty_rate_pct": {
        "impact": 9,
        "impact_reason": (
            "Poverty directly destroys welfare — linked to 10+ year life expectancy gaps, worse child "
            "outcomes and higher long-run public costs (health, crime, benefit dependency)."
        ),
        "feasibility": 6,
        "feasibility_reason": (
            "Targeted interventions (benefit uprating, childcare, living wage) have demonstrated impact. "
            "Universal Credit reform already shows partial gains. Politically viable under current Labour "
            "government; cost manageable vs long-run savings."
        ),
    },
    "rd_expenditure_pct_gdp": {
        "impact": 8,
        "impact_reason": (
            "R&D investment has the highest long-run multiplier of any public spending (~3-5x). "
            "Closing half the gap to Korea/Germany could add 0.3-0.5pp to trend growth within a decade."
        ),
        "feasibility": 7,
        "feasibility_reason": (
            "R&D tax credits, Innovate UK grants and the Horizon association re-entry provide concrete "
            "levers. Cross-party consensus exists. Industrial Strategy already targets 2.4% GDP by 2027. "
            "Feasible but requires sustained funding commitment."
        ),
    },
    "labour_productivity_usd_ppp": {
        "impact": 10,
        "impact_reason": (
            "The UK productivity gap (~20-35% below frontier) is the single biggest driver of lower "
            "wages and living standards vs peers. Closing it fully would add ~£10,000/yr to median wages."
        ),
        "feasibility": 4,
        "feasibility_reason": (
            "The 'productivity puzzle' has persisted since 2008 despite multiple strategies. Requires "
            "simultaneous improvement in R&D, skills, management quality, investment and infrastructure. "
            "No single lever; long gestation periods. Historically very hard to shift quickly."
        ),
    },
    "public_debt_pct_gdp": {
        "impact": 5,
        "impact_reason": (
            "High debt narrows fiscal space and raises debt servicing costs (~£100bn/yr already). "
            "But moderate reduction vs peers has limited direct welfare impact unless crisis materialises."
        ),
        "feasibility": 3,
        "feasibility_reason": (
            "UK debt trajectory is driven by post-pandemic legacy and ageing costs. Fiscal rules constrain "
            "new borrowing but structural reduction requires either growth or spending cuts both politically "
            "difficult. Comparison to DNK/SWE levels unrealistic within a decade."
        ),
    },
    "unemployment_rate_pct": {
        "impact": 5,
        "impact_reason": (
            "UK unemployment is already near structural rate. Gap to best performers (SGP/KOR) reflects "
            "very different labour market models. Marginal further reduction has limited aggregate welfare gain."
        ),
        "feasibility": 6,
        "feasibility_reason": (
            "Active labour market policies, better job-matching and disability employment support can "
            "modestly reduce unemployment. Universal Credit already addresses some traps. "
            "Singapore/Korea levels not realistic without fundamental model change."
        ),
    },
    "social_mobility_ige": {
        "impact": 9,
        "impact_reason": (
            "High IGE (0.43) means UK life outcomes are heavily determined by birth. "
            "Improving mobility unlocks untapped talent, reduces welfare dependency and raises long-run growth."
        ),
        "feasibility": 3,
        "feasibility_reason": (
            "Social mobility is the hardest metric to shift quickly — it reflects accumulated advantages "
            "across housing, education and networks. Denmark took 30+ years of consistent policy. "
            "UK would need radical and sustained redistribution of early-years investment."
        ),
    },
    "govt_effectiveness_wgi": {
        "impact": 7,
        "impact_reason": (
            "Effective government multiplies returns on all other spending. "
            "UK delivery failures in infrastructure, NHS IT and benefits add £billions in waste annually."
        ),
        "feasibility": 6,
        "feasibility_reason": (
            "Civil service reform, digital transformation and spending review discipline are achievable "
            "without major new spending. Missions-based government approach already underway. "
            "WGI score improvement is realistic over 5-10 years."
        ),
    },
    "income_shares_ratio": {
        "impact": 6,
        "impact_reason": (
            "The top-to-bottom income share ratio captures distributional extremes. "
            "Reducing it lowers relative deprivation effects on health and social cohesion."
        ),
        "feasibility": 4,
        "feasibility_reason": (
            "Requires both raising bottom-decile incomes (minimum wage, benefits) and constraining top-end "
            "income growth (tax, corporate governance). Politically contested at both ends."
        ),
    },
}

# Policy attribution: which country's reforms most credibly address each metric gap
POLICY_ATTRIBUTION = {
    "gdp_growth_rate": {
        "lead_country": "IRL",
        "rationale": (
            "Ireland's FDI strategy and low corporate tax created sustained above-average growth. "
            "While MNC-distorted, the underlying lesson on investment attraction applies."
        ),
        "secondary_country": "KOR",
        "secondary_rationale": "Korea's broadband & digital infrastructure investment drove structural productivity growth.",
    },
    "gini_coefficient": {
        "lead_country": "SWE",
        "rationale": (
            "Sweden's comprehensive welfare state, free education and progressive taxation have achieved "
            "the lowest Gini (0.270) among peers, sustained over decades."
        ),
        "secondary_country": "DNK",
        "secondary_rationale": "Denmark's 2011 tax reform shifted burden from income to consumption while preserving equity.",
    },
    "poverty_rate_pct": {
        "lead_country": "DNK",
        "rationale": (
            "Denmark's flexicurity model — combining easy hiring/firing with generous unemployment benefits "
            "and active labour market policies — achieves the lowest poverty rate (6.6%) in this peer group."
        ),
        "secondary_country": "SWE",
        "secondary_rationale": "Sweden's universal childcare and housing subsidies keep child poverty rates extremely low.",
    },
    "rd_expenditure_pct_gdp": {
        "lead_country": "KOR",
        "rationale": (
            "South Korea leads with 4.93% GERD/GDP, driven by large chaebol R&D plus government-backed "
            "broadband and ICT infrastructure investment from the late 1990s onward."
        ),
        "secondary_country": "DEU",
        "secondary_rationale": "Germany's industrial R&D ecosystem (Fraunhofer institutes, Mittelstand innovation) drives 3.13% GERD.",
    },
    "labour_productivity_usd_ppp": {
        "lead_country": "NLD",
        "rationale": (
            "Netherlands achieves $75.4 USD PPP/hr through Wassenaar wage-moderation agreements, "
            "high capital investment, and a strong vocational training system (MBO/HBO)."
        ),
        "secondary_country": "DEU",
        "secondary_rationale": "Germany's dual apprenticeship system and Mittelstand manufacturing base underpin $67.3 productivity.",
    },
    "public_debt_pct_gdp": {
        "lead_country": "DNK",
        "rationale": (
            "Denmark's fiscal consolidation through pension reform (DC transition), revenue-neutral tax "
            "reform and the Stability and Growth Pact commitment kept debt below 30% of GDP."
        ),
        "secondary_country": "SWE",
        "secondary_rationale": "Sweden's constitutional expenditure ceiling and 1990s crisis resolution cut debt from 80% to 34%.",
    },
    "unemployment_rate_pct": {
        "lead_country": "SGP",
        "rationale": (
            "Singapore's SkillsFuture programme and tight active labour market policies maintain "
            "structural unemployment near 1.9%; however, city-state context limits direct transferability."
        ),
        "secondary_country": "KOR",
        "secondary_rationale": "Korea's social insurance expansion and active job-matching programmes sustain 2.8% unemployment.",
    },
    "social_mobility_ige": {
        "lead_country": "DNK",
        "rationale": (
            "Denmark has the lowest IGE (0.15) in this peer set, achieved through free university education, "
            "universal childcare, income-compressed wages and strong early-years investment."
        ),
        "secondary_country": "NLD",
        "secondary_rationale": "Netherlands' vocational education system (MBO) provides high-quality pathways that don't require university.",
    },
    "govt_effectiveness_wgi": {
        "lead_country": "SGP",
        "rationale": (
            "Singapore scores 2.28 WGI — the highest in this group — through meritocratic civil service, "
            "performance pay, long-term planning institutions (GIC, Temasek) and zero-tolerance for corruption."
        ),
        "secondary_country": "SWE",
        "secondary_rationale": "Sweden's transparent governance, digital public services and independent agencies drive WGI of 1.93.",
    },
    "income_shares_ratio": {
        "lead_country": "SWE",
        "rationale": (
            "Sweden has the lowest top/bottom income share ratio (6.4) through compressed wage distribution, "
            "universal welfare and progressive income tax with high thresholds exempting low earners."
        ),
        "secondary_country": "DNK",
        "secondary_rationale": "Denmark's income ratio of 6.1 reflects similar Nordic model with strong trade union wage floors.",
    },
}


def load_json(path: Path, label: str) -> dict:
    if not path.exists():
        print(f"\n*** ALERT: Required input file missing: {path} ***\n", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n*** ALERT: Malformed JSON in {label}: {e} ***\n", file=sys.stderr)
        sys.exit(1)


def load_policy_reforms() -> dict:
    """Load all country policy reform files from data/raw/oecd/."""
    reforms = {}
    for iso3 in ["GBR", "DNK", "NLD", "DEU", "SGP", "KOR", "IRL", "CAN", "AUS", "SWE"]:
        path = OECD_RAW_DIR / f"{iso3}_policy_reforms.json"
        if path.exists():
            with open(path) as f:
                reforms[iso3] = json.load(f)
    return reforms


def mean(values: list) -> float:
    return sum(values) / len(values)


def stdev(values: list) -> float:
    m = mean(values)
    variance = sum((v - m) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def compute_gaps(metric_def: dict, countries: dict) -> dict | None:
    """
    For a single metric, extract values for all countries, compute:
      - UK value
      - best value + best country
      - OECD average
      - per-country gaps
      - gap score
    Returns None if fewer than 5 countries have valid data.
    """
    key = metric_def["key"]
    extract = metric_def["extract"]
    higher_is_better = metric_def["higher_is_better"]
    excludes = set(metric_def.get("exclude", []))

    values_by_country = {}
    for iso3, cdata in countries.items():
        if iso3 in excludes:
            continue
        try:
            val = extract(cdata)
            if val is not None:
                values_by_country[iso3] = val
        except (KeyError, TypeError):
            pass

    uk_value = values_by_country.get("GBR")
    if uk_value is None:
        return None

    peer_values = {k: v for k, v in values_by_country.items() if k != "GBR"}
    all_values = list(values_by_country.values())

    if len(all_values) < 5:
        return None

    if higher_is_better:
        best_iso3 = max(peer_values, key=lambda k: peer_values[k])
    else:
        best_iso3 = min(peer_values, key=lambda k: peer_values[k])

    best_value = values_by_country[best_iso3]
    oecd_avg = mean(list(peer_values.values()))

    sd = stdev(all_values)
    gap_score = (uk_value - best_value) / sd if sd != 0 else 0.0

    per_country_gaps = {}
    for iso3, val in peer_values.items():
        if higher_is_better:
            per_country_gaps[iso3] = round(uk_value - val, 4)
        else:
            per_country_gaps[iso3] = round(uk_value - val, 4)

    uk_vs_oecd_avg = round(uk_value - oecd_avg, 4)

    return {
        "uk_value": round(uk_value, 4),
        "best_value": round(best_value, 4),
        "best_country_iso3": best_iso3,
        "oecd_avg": round(oecd_avg, 4),
        "uk_vs_oecd_avg": uk_vs_oecd_avg,
        "uk_vs_best": round(uk_value - best_value, 4),
        "gap_score": round(gap_score, 4),
        "std_dev": round(sd, 4),
        "per_country_gaps": per_country_gaps,
        "n_countries": len(all_values),
        "excluded_countries": list(excludes),
        "higher_is_better": higher_is_better,
    }


def get_policy_credit(metric_key: str, best_iso3: str, reforms: dict) -> dict:
    """Return the credited policy country and their top reforms for this metric."""
    attribution = POLICY_ATTRIBUTION.get(metric_key, {})
    lead = attribution.get("lead_country", best_iso3)
    secondary = attribution.get("secondary_country")

    lead_reforms = reforms.get(lead, {}).get("top_reforms", [])
    lead_name = reforms.get(lead, {}).get("country", lead)

    result = {
        "credited_country_iso3": lead,
        "credited_country_name": lead_name,
        "attribution_rationale": attribution.get("rationale", "Best performer in peer group."),
        "key_policies": lead_reforms,
    }

    if secondary:
        sec_reforms = reforms.get(secondary, {}).get("top_reforms", [])
        sec_name = reforms.get(secondary, {}).get("country", secondary)
        result["secondary_country_iso3"] = secondary
        result["secondary_country_name"] = sec_name
        result["secondary_rationale"] = attribution.get("secondary_rationale", "")
        result["secondary_key_policies"] = sec_reforms

    return result


def build_priority(metric_key: str) -> dict:
    p = PRIORITY.get(metric_key, {})
    return {
        "impact_score": p.get("impact", 5),
        "impact_justification": p.get("impact_reason", ""),
        "feasibility_score": p.get("feasibility", 5),
        "feasibility_justification": p.get("feasibility_reason", ""),
        "priority_product": round(p.get("impact", 5) * p.get("feasibility", 5) / 10, 1),
    }


def country_name(iso3: str, countries: dict) -> str:
    return countries.get(iso3, {}).get("name", iso3)


def main():
    # --- load inputs ---
    baseline = load_json(BASELINE_PATH, "uk_baseline.json")
    benchmarks = load_json(BENCHMARKS_PATH, "benchmarks.json")
    reforms = load_policy_reforms()

    countries = benchmarks["countries"]

    # --- compute gaps for each metric ---
    results = {}
    scored = []

    for metric_def in METRICS:
        key = metric_def["key"]
        gap_data = compute_gaps(metric_def, countries)
        if gap_data is None:
            print(f"  [SKIP] {key}: insufficient data (<5 countries)", file=sys.stderr)
            continue

        priority = build_priority(key)
        policy_credit = get_policy_credit(key, gap_data["best_country_iso3"], reforms)

        results[key] = {
            "label": metric_def["label"],
            "note": metric_def.get("note", ""),
            "higher_is_better": metric_def["higher_is_better"],
            **gap_data,
            "policy_credit": policy_credit,
            "priority_matrix": priority,
        }
        scored.append((key, gap_data["gap_score"]))

    # --- check minimum metric threshold ---
    if len(results) < 5:
        print(
            f"\n*** ALERT: Only {len(results)} metrics have sufficient data. "
            "Minimum required is 5. Aborting. ***\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- rank by severity (absolute gap score) ---
    ranked_keys = sorted(results.keys(), key=lambda k: abs(results[k]["gap_score"]), reverse=True)
    for rank, key in enumerate(ranked_keys, 1):
        results[key]["severity_rank"] = rank

    # --- build output document ---
    output = {
        "generated_at": "2026-05-17",
        "description": "UK gap analysis vs OECD peers — gap scores, policy attribution and priority matrix",
        "metrics_analysed": len(results),
        "countries_in_benchmark": list(countries.keys()),
        "ranking_method": "Absolute gap score = |UK value - Best value| / StdDev; ranked descending",
        "priority_matrix_method": "Impact (1-10) x Feasibility (1-10); product normalised to /10",
        "gaps": results,
        "severity_ranking": ranked_keys,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    # --- print formatted table ---
    print(f"\n{'='*110}")
    print(f"  UK POLICY GAP ANALYSIS — {len(results)} metrics vs OECD peers")
    print(f"{'='*110}")

    header = (
        f"{'#':>2}  "
        f"{'Metric':<38}  "
        f"{'UK Value':>10}  "
        f"{'Best Value':>10}  "
        f"{'Best Country':<14}  "
        f"{'Gap Score':>10}  "
        f"{'Impact':>6}  "
        f"{'Feasib':>6}  "
        f"{'Priority':>8}"
    )
    print(header)
    print("-" * 110)

    for key in ranked_keys:
        r = results[key]
        pm = r["priority_matrix"]
        best_name = country_name(r["best_country_iso3"], countries)
        direction = "↑ better" if r["higher_is_better"] else "↓ better"

        print(
            f"{r['severity_rank']:>2}.  "
            f"{r['label']:<38}  "
            f"{r['uk_value']:>10.3f}  "
            f"{r['best_value']:>10.3f}  "
            f"{best_name:<14}  "
            f"{r['gap_score']:>+10.3f}  "
            f"{pm['impact_score']:>6}  "
            f"{pm['feasibility_score']:>6}  "
            f"{pm['priority_product']:>8.1f}"
        )

    print("-" * 110)
    print(f"  Gap Score: (UK - Best) / StdDev  |  {direction} shown for last metric")
    print(f"  Priority = Impact × Feasibility / 10")
    print(f"\n  OECD Average comparisons:")
    for key in ranked_keys:
        r = results[key]
        direction_sym = ">" if r["uk_vs_oecd_avg"] > 0 else "<"
        adj = "above" if r["uk_vs_oecd_avg"] > 0 else "below"
        label_short = r["label"][:35]
        print(
            f"    {r['severity_rank']:>2}. {label_short:<35}  UK={r['uk_value']:.3f}  "
            f"OECD avg={r['oecd_avg']:.3f}  UK {adj} avg by {abs(r['uk_vs_oecd_avg']):.3f}"
        )

    print(f"\n  Output saved to: {OUTPUT_PATH}")
    print(f"{'='*110}\n")


if __name__ == "__main__":
    main()

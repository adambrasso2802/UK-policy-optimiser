"""
Generate a comprehensive plain-text and HTML report of the analysis.
Independently runnable: python reports/report_generator.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime, timezone

import config
import utils


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _fmt(value, fmt=".2f", suffix="", prefix="", fallback="n/a"):
    if value is None:
        return fallback
    try:
        return f"{prefix}{value:{fmt}}{suffix}"
    except (ValueError, TypeError):
        return fallback


def build_text_report(
    scores_data: dict | None,
    opt_data:    dict | None,
    scenario_data: dict | None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    div  = "=" * 70
    div2 = "-" * 70

    lines.append(div)
    lines.append("  UK ECONOMIC POLICY OPTIMISER — REPORT")
    lines.append(f"  Generated: {now}")
    lines.append(div)

    # ── Section 1: Policy Score ────────────────────────────────────────────
    lines.append("\n1. CURRENT ECONOMIC PERFORMANCE SCORECARD")
    lines.append(div2)

    if scores_data:
        composite = scores_data.get("composite_score", "n/a")
        grade     = scores_data.get("grade", "n/a")
        lines.append(f"   Composite Score  : {composite:.2f}/10  (Grade: {grade})")
        lines.append("")
        lines.append(f"   {'Indicator':<25} {'Actual':>10} {'Target':>10} {'Score':>8} {'Weight':>7}")
        lines.append("   " + "─" * 62)
        for s in scores_data.get("scores", []):
            actual = _fmt(s["actual_value"])
            target = _fmt(s["target_value"])
            score  = _fmt(s["score_0_to_10"], ".1f", "/10")
            weight = f"{s['weight']*100:.0f}%"
            lines.append(f"   {s['indicator']:<25} {actual:>10} {target:>10} {score:>8} {weight:>7}")
    else:
        lines.append("   [not available — run analysis/policy_scorer.py first]")

    # ── Section 2: Optimisation Results ───────────────────────────────────
    lines.append("\n2. OPTIMAL POLICY PARAMETERS")
    lines.append(div2)

    if opt_data:
        lines.append(f"   Baseline score : {opt_data['baseline_score']:.2f}/10")
        lines.append(f"   Optimal  score : {opt_data['optimal_score']:.2f}/10")
        lines.append(f"   Improvement    : {opt_data['improvement']:+.2f}")
        lines.append(f"   Converged      : {opt_data['convergence']}")
        lines.append("")
        lines.append(f"   {'Parameter':<35} {'Current':>10} {'Optimal':>10} {'Change':>10}")
        lines.append("   " + "─" * 65)
        cur = opt_data["current_policy"]
        opt = opt_data["optimal_policy"]
        for p in cur:
            diff = opt[p] - cur[p]
            lines.append(f"   {p:<35} {cur[p]:>10.2f} {opt[p]:>10.2f} {diff:>+10.2f}")
        lines.append("")
        lines.append("   Estimated outcomes under optimal policy:")
        for k, v in opt_data.get("estimated_outcomes", {}).items():
            lines.append(f"     {k:<35} {v:>8.2f}")
    else:
        lines.append("   [not available — run analysis/optimiser.py first]")

    # ── Section 3: Scenario Comparison ────────────────────────────────────
    lines.append("\n3. POLICY SCENARIO COMPARISON")
    lines.append(div2)

    if scenario_data:
        scenarios = sorted(scenario_data.get("scenarios", []), key=lambda x: x["score"], reverse=True)
        lines.append(f"   {'Rank':<6} {'Scenario':<38} {'Score':>7}")
        lines.append("   " + "─" * 52)
        for i, s in enumerate(scenarios, 1):
            lines.append(f"   {i:<6} {s['name']:<38} {s['score']:>7.2f}")
        lines.append("")
        lines.append("   Key outcome comparisons:")
        lines.append(f"   {'Metric':<30}" + "".join(f"{s['name'][:12]:>14}" for s in scenarios))
        lines.append("   " + "─" * (30 + 14 * len(scenarios)))

        outcome_keys = [
            ("inflation_pct",        "CPI Inflation (%)"),
            ("gdp_growth_pct",       "GDP Growth (%)"),
            ("unemployment_pct",     "Unemployment (%)"),
            ("psnb_gdp_pct",         "PSNB (% GDP)"),
        ]
        for key, label in outcome_keys:
            row = f"   {label:<30}"
            for s in scenarios:
                v = s["outcomes"].get(key)
                row += f"{v:>14.2f}" if v is not None else f"{'n/a':>14}"
            lines.append(row)
    else:
        lines.append("   [not available — run analysis/scenario_modeller.py first]")

    # ── Section 4: Caveats ────────────────────────────────────────────────
    lines.append("\n4. CAVEATS & METHODOLOGY NOTES")
    lines.append(div2)
    lines.append("""
   The policy optimiser uses simplified linear elasticity models derived from
   IMF Working Papers, OBR forecasting documentation, and published academic
   literature. It is NOT a full DSGE (Dynamic Stochastic General Equilibrium)
   model. Results should be treated as illustrative directional guidance only.

   Key limitations:
   - Policy interactions and non-linearities are simplified
   - Supply-side structural effects (trade policy, regulation) are omitted
   - Distributional impacts are not modelled
   - Uncertainty bands are not reported
   - Timing of policy transmission is not modelled (all effects are long-run)

   All underlying data is sourced from:
   - ONS Beta API  (https://api.beta.ons.gov.uk)
   - Bank of England Statistics Database
   """)

    lines.append(div)
    lines.append("  END OF REPORT")
    lines.append(div)

    return "\n".join(lines)


def build_html_report(text_report: str) -> str:
    """Wrap the text report in minimal HTML for readability."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    escaped = text_report.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>UK Policy Optimiser Report — {now}</title>
<style>
  body {{ font-family: monospace; background: #0d1117; color: #c9d1d9;
         padding: 2rem; max-width: 1000px; margin: auto; }}
  pre  {{ white-space: pre-wrap; word-wrap: break-word; line-height: 1.5; }}
  h1   {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: .5rem; }}
</style>
</head>
<body>
<h1>UK Economic Policy Optimiser</h1>
<pre>{escaped}</pre>
</body>
</html>"""


def run() -> dict:
    utils.print_section("Report Generator")

    scores_data   = _load_json(config.PROCESSED_DIR / "policy_scores.json")
    opt_data      = _load_json(config.PROCESSED_DIR / "optimisation_results.json")
    scenario_data = _load_json(config.PROCESSED_DIR / "scenario_results.json")

    missing = []
    if not scores_data:
        missing.append("policy_scores.json (run analysis/policy_scorer.py)")
    if not opt_data:
        missing.append("optimisation_results.json (run analysis/optimiser.py)")
    if not scenario_data:
        missing.append("scenario_results.json (run analysis/scenario_modeller.py)")

    if missing:
        utils.console.print("[yellow]WARNING:[/yellow] Some analysis files are missing:")
        for m in missing:
            utils.console.print(f"  - {m}")
        utils.console.print("  Generating partial report.\n")

    text_report = build_text_report(scores_data, opt_data, scenario_data)
    html_report = build_html_report(text_report)

    now_str     = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    txt_path    = config.REPORTS_DIR / f"uk_policy_report_{now_str}.txt"
    html_path   = config.REPORTS_DIR / f"uk_policy_report_{now_str}.html"
    latest_txt  = config.REPORTS_DIR / "latest_report.txt"
    latest_html = config.REPORTS_DIR / "latest_report.html"

    for path, content in [
        (txt_path,    text_report),
        (html_path,   html_report),
        (latest_txt,  text_report),
        (latest_html, html_report),
    ]:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        utils.console.print(f"  [green]Saved[/green] → {path}")

    # Print text report to terminal
    utils.console.print("\n" + text_report)

    utils.console.print("[bold green]\nReport generation complete.[/bold green]\n")
    return {"txt_path": str(txt_path), "html_path": str(html_path)}


if __name__ == "__main__":
    run()

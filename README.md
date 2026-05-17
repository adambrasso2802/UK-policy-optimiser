# UK Economic Policy Optimiser

A data-driven pipeline that benchmarks UK economic performance against OECD peers, scores and optimises policy interventions, and produces publication-ready advocacy materials. Inspired by Henry Fudge's *A Plan to Fix Britain*.

---

## What This Project Does

The pipeline answers a single question: **which policy changes would most improve UK living standards, and how do we get them adopted?**

It does this in six sequential phases:

1. **Fetch** — Pull live UK economic data from ONS, Bank of England, and IMF APIs
2. **Research** — Scrape OECD benchmarks across 10 peer countries and 11 metrics; scrape 8 UK think tanks; extract Henry Fudge's published policy positions
3. **Score** — Rank 33 candidate policies using a weighted composite score (GDP impact, poverty reduction, inequality reduction, political feasibility, implementation simplicity)
4. **Optimise** — Use `scipy` to find the parameter set (tax rates, spending levels, Bank Rate) that maximises the composite score subject to realistic bounds
5. **Model** — Run pre-defined scenarios (Austerity, Green New Deal, Nordic Model, Singapore Model) against the current baseline
6. **Advocate** — Generate a policy paper, MP briefing note, select committee submission, op-ed drafts, and a 90-day advocacy plan

---

## Folder Structure

```
UK-policy-optimiser/
├── main.py                        # Pipeline orchestrator (Phases 1–5)
├── compile_advocacy_plan.py       # Phase 6 advocacy plan compiler
├── config.py                      # API endpoints, series codes, policy bounds
├── utils.py                       # Logging, console helpers
├── requirements.txt
│
├── modules/                       # Phase 1 — Live data fetch (ONS / BoE)
│   ├── fetch_gdp.py               #   GDP chained volume (ABMI / YBHA)
│   ├── fetch_inflation.py         #   CPI, CPIH, RPI series
│   ├── fetch_employment.py        #   Employment, unemployment, inactivity rates
│   ├── fetch_interest_rates.py    #   Bank Rate, M4, mortgage rate
│   ├── fetch_fiscal.py            #   Public sector net borrowing & debt
│   ├── fetch_trade.py             #   Current account, trade balance
│   └── fetch_productivity.py     #   Output per hour worked
│
├── research/                      # Research data layer (run before analysis)
│   ├── fetch_ons_data.py          #   Bulk ONS pull: GDP, Gini, poverty, R&D, regional GVA
│   ├── fetch_oecd_data.py         #   10 peer countries × 11 metrics → data/raw/oecd/
│   ├── fetch_imf_data.py          #   IMF cross-check for macro indicators
│   ├── fetch_think_tanks.py       #   Scrape 8 UK think tanks for relevant reports
│   ├── scrape_henry_fudge.py      #   Scrape henryfudge.com policy positions
│   └── process_henry_fudge_manual.py  # Process manual Henry Fudge input
│
├── analysis/                      # Phases 2–4 — Scoring, optimisation, scenarios
│   ├── gap_analysis.py            #   UK vs OECD peer gap across 10 metrics
│   ├── policy_scorer.py           #   Synthesise sources → ranked policy list
│   ├── economic_modeller.py       #   Economic impact modelling for top policies
│   ├── optimiser.py               #   scipy optimisation of policy parameters
│   └── scenario_modeller.py      #   Pre-defined scenario comparisons
│
├── synthesis/                     # Policy paper and roadmap generation
│   ├── generate_policy_report.py  #   Full policy paper → outputs/policy_paper.md
│   └── generate_roadmap.py        #   MP/journalist briefing note → outputs/briefing_note.md
│
├── reports/                       # Phase 5 — Report generation
│   ├── report_generator.py        #   HTML + plain-text summary report
│   ├── latest_report.html         #   Most recent HTML report (symlink-style)
│   └── latest_report.txt          #   Most recent plain-text report
│
├── advocacy/                      # Phase 6 — Advocacy channel scripts
│   ├── parliament.py              #   Select committee submissions, MP briefing notes
│   ├── media.py                   #   Journalist targets, op-ed drafts, social posts
│   └── think_tank_routes.py       #   Think tank submission routes
│
├── data/
│   ├── raw/
│   │   ├── ons/                   #   ONS time-series JSON files
│   │   ├── oecd/                  #   Per-country per-metric JSON (ISO3_metric.json)
│   │   ├── think_tanks/           #   Scraped HTML and extracted reports.json per tank
│   │   └── henry_fudge/           #   Scraped and manually processed policy positions
│   └── processed/
│       ├── uk_baseline.json        #   UK current-values snapshot
│       ├── benchmarks.json         #   OECD peer country data
│       ├── gap_analysis.json       #   UK deficit vs peers per metric
│       ├── policy_rankings.json    #   Scored and ranked policy list
│       ├── optimisation_results.json  # Optimal parameter set and scores
│       └── scenario_results.json   #   Per-scenario outcome projections
│
├── outputs/                       # Publication-ready documents
│   ├── policy_paper.md            #   Full policy paper
│   ├── briefing_note.md           #   2-page MP/journalist briefing note
│   ├── select_committee_submission.md
│   ├── op_ed_drafts.md
│   └── advocacy_plan.md           #   90-day advocacy action plan
│
└── logs/
    └── errors.log
```

---

## How to Run

### Prerequisites

```bash
pip install -r requirements.txt
```

All dependencies are also installed automatically on first run.

### Full pipeline (Phases 1–5)

```bash
python main.py
```

Use cached data (skip live API calls):

```bash
python main.py --skip-fetch
```

### Research layer (run once before the full pipeline)

These scripts populate `data/raw/` and must be run before analysis:

```bash
python research/fetch_ons_data.py          # UK ONS bulk data
python research/fetch_oecd_data.py         # OECD peer benchmarks
python research/fetch_imf_data.py          # IMF cross-check
python research/fetch_think_tanks.py       # Think tank reports
python research/scrape_henry_fudge.py      # Henry Fudge positions
python research/process_henry_fudge_manual.py
```

### Individual analysis modules

Each analysis script is independently runnable:

```bash
python analysis/gap_analysis.py            # UK vs OECD gap table
python analysis/policy_scorer.py           # Ranked policy list
python analysis/optimiser.py               # Optimal parameter search
python analysis/scenario_modeller.py       # Scenario projections
```

### Policy paper and briefing note

```bash
python synthesis/generate_policy_report.py  # outputs/policy_paper.md
python synthesis/generate_roadmap.py        # outputs/briefing_note.md
```

### Phase 6 — Advocacy plan

```bash
python compile_advocacy_plan.py             # outputs/advocacy_plan.md
```

---

## Data Sources

| Source | What it provides | Module |
|--------|-----------------|--------|
| **ONS Beta API** | GDP, CPI/CPIH/RPI, employment, productivity, public debt, trade balance | `modules/`, `research/fetch_ons_data.py` |
| **Bank of England API** | Bank Rate, M4 money supply, effective mortgage rate | `modules/fetch_interest_rates.py` |
| **OECD** | 10 peer countries (AUS, CAN, DEU, DNK, IRL, KOR, NLD, SGP, SWE) across 11 metrics: GDP growth, Gini, poverty, unemployment, productivity, R&D spend, public debt, tax revenue, social mobility, income shares, government effectiveness | `research/fetch_oecd_data.py` |
| **IMF** | Macro indicator cross-check | `research/fetch_imf_data.py` |
| **Think tanks** (8) | Adam Smith Institute, Centre for Cities, Fabian Society, IFS, IPPR, Policy Exchange, Resolution Foundation, Tony Blair Institute — recent reports on growth, inequality, and poverty | `research/fetch_think_tanks.py` |
| **Henry Fudge** | Policy positions from *A Plan to Fix Britain* and related writing on henryfudge.com | `research/scrape_henry_fudge.py` |

---

## Key Outputs

| File | Description |
|------|-------------|
| `reports/latest_report.html` | Full HTML summary report with tables and scores |
| `reports/latest_report.txt` | Plain-text version of the same report |
| `data/processed/policy_rankings.json` | All 33 policies ranked by composite score (weights: 30% GDP impact, 25% poverty reduction, 25% inequality reduction, 10% political feasibility, 10% implementation simplicity) |
| `data/processed/optimisation_results.json` | Optimal policy parameter set found by `scipy.optimize.differential_evolution`, with score improvement vs baseline |
| `data/processed/scenario_results.json` | Projections for Baseline, Fiscal Austerity, Green New Deal, Nordic Model, Singapore Model, and Optimal scenarios |
| `data/processed/gap_analysis.json` | UK deficit or surplus vs OECD peer median on each metric |
| `outputs/policy_paper.md` | Full publication-ready policy paper |
| `outputs/briefing_note.md` | 2-page briefing note for MPs and journalists |
| `outputs/advocacy_plan.md` | 90-day action plan with parliamentary, media, and think tank routes |
| `outputs/select_committee_submission.md` | Draft select committee inquiry submission |
| `outputs/op_ed_drafts.md` | Op-ed drafts for national press |

### Current baseline result

UK GDP averaged **0.68%/yr** (2019–2024) vs an OECD peer average of **2.1%/yr**. The optimiser identifies a sequenced five-reform programme that the model projects would roughly double the growth rate, lift ~2 million people out of poverty, and reduce public debt as a share of GDP within a decade.

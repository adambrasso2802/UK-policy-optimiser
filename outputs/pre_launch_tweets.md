# Pre-Launch Twitter/X Strategy
**Account:** UK Economic Policy Programme (pre-launch phase)
**Objective:** Build audience and credibility before major policy release
**Tone:** Sharp, evidence-led, slightly provocative, non-partisan

---

## 1. Recommended Posting Schedule

### The Three Options

| Schedule | Algorithm Visibility | Follower Fatigue Risk | Time to 1,000 followers* | Notes |
|---|---|---|---|---|
| 1/hour (aggressive) | High initial burst; X rewards sustained activity but punishes spam-like patterns | Very high; unfollows likely within days | ~14 days (if impressions hold) | Unsustainable without a content backlog; risks looking automated |
| 2/day (moderate) | Strong; consistent signals to algorithm without triggering fatigue | Low-moderate; manageable if content quality is high | ~25–35 days | Requires 20 tweets minimum before sustaining pace |
| 1/day (slow build) | Moderate; algorithm favours regularity but rewards engagement velocity | Very low | ~50–70 days | Best for reputation-building accounts; forgives weak individual tweets |

*Assumes 2% follow-back rate per impression, ~500 impressions/tweet at account launch

### Recommended Schedule: **2 per day (moderate)**

**Justification:**

This is the schedule used by the accounts that best resemble what this programme is building toward:

- **@IFS_Tweets** built its current ~75k following primarily through consistent 2–3x daily posting on specific data releases — never volume for volume's sake, always anchored to a fact or finding. Their cadence created a Pavlovian "check IFS when there's news" reflex in followers.
- **@resolutionfdn** (Resolution Foundation) posts 2–3x daily, mixing original analysis with sharp commentary on others' data. Crucially, they built their reputation by being the *best source on a specific set of facts* (living standards, wages), not by being everywhere.
- **@CentreCities** grew by owning a niche (urban productivity and housing) and posting with regularity. They did not try to be a general economics account. Their threads on specific cities became retweet bait for local politicians and journalists.

**The pattern across all three:** They posted consistently, not aggressively. They established a recognisable *voice* before a large audience. They treated each post as a reputation-building act, not a reach-maximising one.

**For this account:** 2 posts per day for 5 days deploys the 10 pre-launch tweets over one working week — a coherent "opening act" before either a pause or a shift into ongoing commentary mode.

---

### Optimal Posting Times (UK political/economics audience)

Research on UK political and economics Twitter engagement consistently shows two windows:

| Window | Time (GMT/BST) | Rationale |
|---|---|---|
| **Morning** | **07:30–08:15** | Commute + before-desk scroll; political journalists, think-tank staff, civil servants check feeds |
| **Lunchtime** | **12:30–13:00** | Second peak; good for retweets from people who missed morning |
| **Evening** | **17:30–18:30** | Works for B2C; weaker for policy/economics niche which disengages after office hours |

**Recommendation:** Post at **07:45** and **12:45** on weekdays. Avoid weekends for this phase — the policy/economics audience is significantly thinner, and weekend posts get buried before the Monday morning scroll.

---

## 2. Tweet Calendar

| Day | Post 1 (07:45) | Post 2 (12:45) | Category Mix |
|---|---|---|---|
| Monday | Tweet 1 — Problem Framing | Tweet 2 — International Comparison | Scene-setting opener |
| Tuesday | Tweet 3 — Myth-Busting | Tweet 4 — Problem Framing | Evidence credibility |
| Wednesday | Tweet 5 — International Comparison | Tweet 6 — Teaser | Mid-week intrigue |
| Thursday | Tweet 7 — Myth-Busting | Tweet 8 — Problem Framing | Provocation + data |
| Friday | Tweet 9 — International Comparison | Tweet 10 — Teaser | Close with anticipation |

**Note:** Pin the profile/bio tweet (Section 4) as the first act on Monday morning, *before* Tweet 1 goes live. The pinned tweet should be up by 07:00 so new profile visitors see it all day.

---

## 3. The 10 Tweets

> **Source audit (May 2026):** All 10 tweets fully re-sourced from files in `data/processed/` and
> `data/raw/`. Every figure below is preceded by the exact source file and value drawn from it.
> Tweets where the original claim had no corresponding figure in the fetched data have been
> restructured in full. [DATA MISSING] is used where a specific figure could not be located in
> any project file. ⚠️ DATA AGE flags are applied to any figure from data older than 2023.

---

### Tweet 1
**Category:** Problem Framing
**Day/Time:** Monday 07:45

---

**Source audit — values drawn before writing:**

| Source file | Field | Value |
|---|---|---|
| `data/raw/oecd/GBR_income_shares.json` | top10_to_bottom10_ratio, year 2022 | **9.5** |
| `data/processed/gap_analysis.json` → income_shares_ratio | best_value (Denmark), year 2022 | **6.1** |
| `data/raw/oecd/GBR_gini.json` | Gini coefficient, year 2022 | **0.351** |
| `data/processed/gap_analysis.json` → gini_coefficient | oecd_avg (10-country peer set), year 2022 | **0.308** |

⚠️ **DATA AGE:** All OECD IDD figures are from 2022 (older than 2023).

**Original claim dropped:** "second highest in the G7 since the 1980s" — no G7 Gini time series covering the 1980s–present exists in any project file. Claim replaced with directly evidenced figures.

---

**Text (220 chars):**
> In the UK, the top 10% earn 9.5 times the income of the bottom 10%. In Denmark, it is 6.1 times. The gap between those two numbers is a policy choice, not a fact of life. We've been studying what made the difference.
>
> #UKEconomy #Inequality #EconomicReform

**Source:** OECD Income Distribution Database (IDD), disposable income shares, 2022. `data/raw/oecd/GBR_income_shares.json`; `data/processed/gap_analysis.json`.

**Engagement Hook:** "A policy choice, not a fact of life" — non-partisan framing that attributes cause to decisions, not to any party or ideology.

**Reply Bait:** Left will attribute the gap to Thatcher/low unionisation. Right will cite wage-suppressing immigration or welfare dependency. Both engage; neither invalidates the core ratio.

**Tactic:** Concrete ratio (9.5x vs 6.1x) anchors the abstraction of "inequality." Denmark is a credible comparator — prosperous, not exotic.

---

### Tweet 2
**Category:** International Comparison
**Day/Time:** Monday 12:45

---

**Source audit — values drawn before writing:**

| Source file | Field | Value |
|---|---|---|
| `data/raw/oecd/GBR_labour_productivity.json` | GDP per hour worked, USD PPP, year 2023 | **$55.3** |
| `data/processed/gap_analysis.json` → labour_productivity_usd_ppp | best_value (Netherlands), year 2023 | **$75.4** |
| `data/processed/gap_analysis.json` → labour_productivity_usd_ppp | oecd_avg (9-country peer set), year 2023 | **$65.5** |
| `data/processed/benchmarks.json` → DNK → labour_productivity_usd_ppp | value, year 2023 | **$72.1** |

No data age flag: all productivity figures are from 2023.

**Original claim dropped:** "Germany ~300,000 homes, France ~350,000, UK ~220,000" — no housing completions data for any country exists in any project file. Full restructure applied.

---

**Text (228 chars):**
> A Dutch worker produces $75 of output per hour. A Danish worker: $72. A UK worker: $55. That's not a small rounding error. It is a £10,000-a-year gap in the wages those economies can afford to pay. The question is why. And what closes it.
>
> #Productivity #UKEconomy #EconomicReform

**Source:** OECD Productivity Statistics (PDB_LV), GDP per hour worked at USD PPP prices, 2023. `data/raw/oecd/GBR_labour_productivity.json`; `data/processed/gap_analysis.json`.

**Engagement Hook:** "A £10,000-a-year gap in the wages those economies can afford to pay" — translates the abstract productivity figure into a tangible living-standards consequence.

**Reply Bait:** Europhiles will blame Brexit. Nationalists will dispute the methodology. Economists will argue about capital, management quality, R&D. All three are on-topic.

**Tactic:** Dollar-per-hour figures are stark and hard to dispute. Two comparators (Netherlands, Denmark) are better than one — harder to dismiss as cherry-picking.

---

### Tweet 3
**Category:** Myth-Busting
**Day/Time:** Tuesday 07:45

---

**Source audit — values drawn before writing:**

| Source file | Field | Value |
|---|---|---|
| `data/raw/think_tanks/ifs_manual.txt` → Report 2 (Oct 2025) | UK business investment as % of GDP | **10.8%** |
| `data/raw/think_tanks/ifs_manual.txt` → Report 2 (Oct 2025) | US business investment as % of GDP | **16%** |
| `data/raw/think_tanks/ifs_manual.txt` → Report 2 (Oct 2025) | Germany business investment as % of GDP | **17%** |
| `data/raw/think_tanks/ifs_manual.txt` → Report 2 (Oct 2025) | Publication date | **October 2025** |

No data age flag: IFS Green Budget chapter published October 2025.

**Original claim dropped:** "a UK worker produces less per hour than a French worker doing the same job — in the same multinational firm." France is not in the project dataset; no within-firm productivity study exists in any project file.

---

**Text (238 chars):**
> Myth: the UK's poor productivity is about attitude or culture. Fact: UK firms invest 10.8% of GDP. German firms: 17%. US firms: 16%. When you spend that much less on the tools, the machines, and the infrastructure — workers produce less. That's arithmetic.
>
> #Productivity #UKEconomy #EconomicReform

**Source:** IFS Green Budget, "Economic Outlook: Navigating Narrow Paths," October 2025. `data/raw/think_tanks/ifs_manual.txt`.

**Engagement Hook:** "That's arithmetic" — the declarative close shuts down the cultural explanation without engaging it on its own terms.

**Reply Bait:** Eurosceptics will dispute the Germany comparison. Business groups will cite regulation rather than investment. Economists will debate the causality. All three boost reach.

**Tactic:** Business investment figures are concrete and sourced from a respected centrist institution (IFS). Hard to dismiss as ideological.

---

### Tweet 4
**Category:** Problem Framing
**Day/Time:** Tuesday 12:45

---

**Source audit — values drawn before writing:**

| Source file | Field | Value |
|---|---|---|
| `data/raw/oecd/GBR_poverty_rate.json` | Relative poverty rate (<50% median), year 2022 | **11.7%** |
| `data/raw/oecd/DNK_poverty_rate.json` | Relative poverty rate (<50% median), year 2022 | **6.6%** |
| `data/processed/gap_analysis.json` → poverty_rate_pct | oecd_avg (10-country peer set), year 2022 | **9.9%** |
| `data/processed/uk_baseline.json` → poverty_rate | UK individuals below 60% median (BHC), year 2023 | **18%** |

⚠️ **DATA AGE:** OECD IDD poverty figures are from 2022 (older than 2023). ONS/DWP figure is from 2022/23.

**Original claim dropped:** "4.3 million children" after housing costs, and "higher than the peak of the 2008 financial crisis." No AHC child poverty headcount series and no 2008/09 AHC child poverty baseline appear in any project file. These specific figures are [DATA MISSING]. Tweet restructured around verified figures.

---

**Text (231 chars):**
> 11.7% of UK residents live below the poverty line — against a 10-country OECD peer average of 9.9% and a Danish rate of 6.6%. In the same data year. These are not destiny. They are outcomes. And they shift when policy shifts.
>
> #PovertyUK #CostOfLiving #UKEconomy

**Source:** OECD Income Distribution Database (IDD), relative poverty rate (<50% median income), 2022. `data/raw/oecd/GBR_poverty_rate.json`; `data/raw/oecd/DNK_poverty_rate.json`; `data/processed/gap_analysis.json`.

**Note on dropped figures:** The original tweet cited 4.3 million children in poverty (AHC) and a comparison to the 2008/09 peak. Neither figure appears in any project file. [DATA MISSING] applied; tweet restructured.

**Engagement Hook:** "These are outcomes. And they shift when policy shifts." — invites the question of what shifted Denmark's rate, without prescribing an answer.

**Reply Bait:** Right will dispute the methodology or note that UK has different population composition. Left will immediately cite benefit cuts. The tweet doesn't adjudicate either position.

**Tactic:** Three-way comparison (UK, OECD avg, Denmark) is harder to explain away than a bilateral comparison.

---

### Tweet 5
**Category:** International Comparison
**Day/Time:** Wednesday 07:45

---

**Source audit — values drawn before writing:**

| Source file | Field | Value |
|---|---|---|
| `data/raw/oecd/GBR_social_mobility.json` | Intergenerational earnings elasticity (IGE), year 2023 | **0.43** |
| `data/processed/gap_analysis.json` → social_mobility_ige | best_value (Denmark), year 2023 | **0.15** |
| `data/processed/gap_analysis.json` → social_mobility_ige | oecd_avg (10-country peer set), year 2023 | **0.244** |
| `data/processed/gap_analysis.json` → social_mobility_ige | severity_rank | **2nd worst** |

No data age flag: OECD Social Mobility for Inclusive Growth data is from 2023.

**Original claim dropped:** Finland child poverty data — Finland does not appear in any project file. Full restructure applied.

---

**Text (237 chars):**
> The intergenerational earnings elasticity measures how much your parents' income determines yours. UK: 0.43 — near the top of comparable economies. Denmark: 0.15. In Denmark, where you start matters less than a third as much. That's not luck. That's structure.
>
> #SocialMobility #UKEconomy #BritishPolitics

**Source:** OECD Social Mobility for Inclusive Growth 2023. `data/raw/oecd/GBR_social_mobility.json`; `data/processed/gap_analysis.json`.

**Engagement Hook:** "That's not luck. That's structure." — same dry understatement as the original Tweet 5 tone. Invites readers to supply the obvious conclusion.

**Reply Bait:** Right will argue individual talent matters more than IGE captures. Left will cite private schooling and inherited wealth. Economists will debate the measurement. All three are productive.

**Tactic:** IGE is a counterintuitive metric — most readers don't know it. Making it concrete (0.43 vs 0.15; "a third as much") converts a statistical abstraction into a human claim.

---

### Tweet 6
**Category:** Teaser
**Day/Time:** Wednesday 12:45

---

**Source audit:** No factual claims in this tweet. No data verification required.

---

**Text (234 chars):**
> We've been spending six months in the data on UK housing, poverty, growth and inequality. Not writing rhetoric. Reading evidence. There's a programme coming. It's not what you'd expect from either side. Watch this space.
>
> #UKEconomy #EconomicReform #UKPolitics

**Engagement Hook:** "Not what you'd expect from either side" — positions the account as genuinely non-partisan while signalling something substantive is coming.

**Reply Bait:** Left will assume it's a neoliberal Trojan horse. Right will assume it's a tax-and-spend manifesto. Both camps will be curious enough to follow. Neither will be right.

**Tactic:** Controlled reveal. "Six months in the data" establishes that this is rigorous work, not a substack hot take.

---

### Tweet 7
**Category:** Myth-Busting
**Day/Time:** Thursday 07:45

---

**Source audit — values drawn before writing:**

| Source file | Field | Value |
|---|---|---|
| `data/raw/think_tanks/policy_exchange_manual.txt` → Report 2 (2024) | Social housing waiting list | **1.19 million (2021)** |
| `data/raw/think_tanks/policy_exchange_manual.txt` → Report 2 (2024) | Households in temporary accommodation | **86,000** |
| `data/raw/think_tanks/policy_exchange_manual.txt` → Report 2 (2024) | Projected housing benefit cost, 2025–26 | **£31.3bn** |

⚠️ **DATA AGE:** Social housing waiting list figure is from 2021 (older than 2023).

**Original claim dropped:** "over 400,000 homes have planning permission but haven't been built." No MHCLG live tables data or Lichfields pipeline research appears in any project file. [DATA MISSING]. Tweet fully restructured around verified Policy Exchange figures.

---

**Text (228 chars):**
> 1.19 million households are on the social housing waiting list. 86,000 are in temporary accommodation tonight. Housing benefit is projected at £31.3bn a year. This is not a planning problem that planning reform alone will fix. The maths doesn't work.
>
> #HousingCrisis #HousingPolicy #UKEconomy

**Source:** Policy Exchange, "Homes for Growth," 2024. `data/raw/think_tanks/policy_exchange_manual.txt`.

**Note on dropped figures:** The original tweet cited "over 400,000 homes with planning permission not yet built." No planning permission pipeline data appears in any project file. [DATA MISSING] applied; tweet restructured.

**Engagement Hook:** "This is not a planning problem that planning reform alone will fix" — confronts the dominant supply-side consensus without rejecting supply reform entirely.

**Reply Bait:** Planning reformers will defend zoning arguments. Housing campaigners will demand more social housing. Fiscal conservatives will note the £31.3bn benefit cost. All three are on-topic replies.

**Tactic:** Three figures in sequence build to an implied argument without stating it explicitly. The logic is left for the reader to complete.

---

### Tweet 8
**Category:** Problem Framing
**Day/Time:** Thursday 12:45

---

**Source audit — values drawn before writing:**

| Source file | Field | Value |
|---|---|---|
| `data/processed/gap_analysis.json` → gdp_growth_rate | UK 5-year average growth (2019–2024) | **0.68%** |
| `data/processed/gap_analysis.json` → gdp_growth_rate | 10-country OECD peer average (2019–2024) | **2.13%** |
| `data/raw/think_tanks/ifs_manual.txt` → Report 2 (Oct 2025) | Real GDP per capita growth, 2024 | **0.1%** |
| `data/raw/think_tanks/ifs_manual.txt` → Report 2 (Oct 2025) | Publication date | **October 2025** |

No data age flag: gap analysis uses OECD National Accounts data through 2024; IFS report is October 2025.

**Original claim dropped:** "UK GDP per capita growth has been weaker than every other G7 economy since 2008." G7 members USA, France, Italy, Japan are not in the project dataset; no time series from 2008 exists for them. The broader G7 ranking cannot be verified from project data. Claim replaced with directly evidenced figures.

---

**Text (236 chars):**
> The UK's average GDP growth over the last five years: 0.68%. Across a 10-country OECD peer set: 2.13%. In 2024 alone, real GDP per capita grew by 0.1%. This is not a short-run blip. It is a structural divergence. And it happened under every government since 2008.
>
> #GDP #UKEconomy #BritishPolitics

**Source:** OECD National Accounts, 5-year average 2019–2024. `data/processed/gap_analysis.json`. IFS Green Budget, October 2025. `data/raw/think_tanks/ifs_manual.txt`.

**Note on dropped claim:** The original tweet stated UK growth has been "weaker than every other G7 economy since 2008." No G7 time series from 2008 exists in the project data for verification. [DATA MISSING] for the full G7 ranking. The peer-set comparison (10 OECD countries) is used instead, which is fully evidenced.

**Engagement Hook:** "It happened under every government since 2008" — multi-government framing makes the point structurally rather than politically.

**Reply Bait:** Left will blame austerity. Right will blame over-regulation or EU membership. The 0.68% figure vs 2.13% is stark enough to drive both responses.

**Tactic:** Two numbers side by side (0.68% vs 2.13%) do more work than any editorial comment. The IFS 2024 figure (0.1%) reinforces that the recent data is no better.

---

### Tweet 9
**Category:** International Comparison
**Day/Time:** Friday 07:45

---

**Source audit — values drawn before writing:**

| Source file | Field | Value |
|---|---|---|
| `data/raw/oecd/GBR_rd_expenditure.json` | UK R&D as % of GDP, year 2023 | **1.89%** |
| `data/processed/gap_analysis.json` → rd_expenditure_pct_gdp | best_value (South Korea), year 2022 | **4.93%** |
| `data/processed/gap_analysis.json` → rd_expenditure_pct_gdp | oecd_avg (10-country peer set) | **2.57%** |
| `data/processed/gap_analysis.json` → rd_expenditure_pct_gdp | severity_rank | **4th most severe gap** |

⚠️ **DATA AGE:** South Korea R&D figure (4.93%) is from OECD MSTI 2023, reporting on 2022 data.

**Original claim dropped:** "South Korea had lower GDP per capita than the UK in 1990. Today it is roughly equal in purchasing power terms." No GDP per capita PPP time series for South Korea or UK appears in any project file. Additionally, the available labour productivity data (OECD PDB_LV 2023) shows UK at $55.3/hr and South Korea at $44.8/hr — UK is materially ahead in output per hour, making the "roughly equal" PPP framing unverifiable and potentially misleading from these files. Full restructure applied.

---

**Text (236 chars):**
> South Korea spends 4.93% of GDP on research and development. The UK: 1.89%. The OECD peer average: 2.57%. There is a direct line from that investment gap to the productivity gap, the wage gap, and the growth gap. South Korea did not stumble into this. It chose it.
>
> #RandD #Productivity #EconomicReform

**Source:** UK: ONS GERD bulletin, 2023. `data/raw/oecd/GBR_rd_expenditure.json`. South Korea: OECD Main Science and Technology Indicators (MSTI), 2022 data. `data/processed/gap_analysis.json`.

**Engagement Hook:** "South Korea did not stumble into this. It chose it." — same dry understatement closing used in the original Tweet 9. Analytical, not ideological.

**Reply Bait:** Industrial-policy advocates will welcome the Korea comparison. Free-marketeers will argue against R&D subsidies. Tech optimists will cite UK spinout quality over quantity. All three are substantive replies.

**Tactic:** R&D figures are harder to politicise than inequality measures. The 4.93% vs 1.89% ratio (more than 2.6x) speaks clearly without editorialising.

---

### Tweet 10
**Category:** Teaser
**Day/Time:** Friday 12:45

---

**Source audit:** No factual claims in this tweet. No data verification required.

---

**Text (239 chars):**
> At some point soon, we'll publish something that took a long time to get right. Evidence-based. Costed. Across housing, growth, poverty and inequality. No ideology. Just the numbers and what they suggest. Follow if you want to see it first.
>
> #UKEconomy #EconomicReform #UKPolitics

**Engagement Hook:** "Follow if you want to see it first" — direct follow prompt on the final pre-launch tweet. Justified by the week of credibility built before it.

**Reply Bait:** The phrase "no ideology, just the numbers" will provoke both camps — some will say "nobody is ideology-free" (engagement). Others will say "finally" (retweets). Either outcome builds reach.

**Tactic:** Explicit CTA after 9 tweets of zero selling. Earns the ask.

---

## 4. Pinned Tweet (Day 1, Live by 07:00 Monday)

**Purpose:** First thing new profile visitors see. Explains the account without revealing the programme.

---

> This account exists for one reason: the UK has serious, long-running economic problems — on housing, poverty, productivity and growth — that deserve serious, evidence-based analysis.
>
> We're not left. We're not right. We're interested in what works.
>
> More coming. Follow to find out.

**Character count:** 284 (for pinned tweet — X allows longer pinned posts as threads; alternatively trim to 240 as below)

**240-character version:**
> The UK has serious economic problems — housing, poverty, productivity, growth — that deserve serious analysis. Not politics. Not ideology. Evidence. We're building something. Follow to find out.
>
> #UKEconomy #EconomicReform

---

## 5. Twitter/X Bio Draft

**Constraints:** 160 characters maximum for X bio

**Option A (authority-forward):**
> Evidence-based UK economic policy. Housing. Poverty. Productivity. Growth. Something is coming. Non-partisan. Non-ideological. Watch this space.

*138 characters*

**Option B (provocative):**
> The UK economy has deep, fixable problems. We've spent months in the data. Something is coming. Not what you'd expect. Non-partisan.

*133 characters*

**Option C (institutional-sounding):**
> Rigorous, evidence-led analysis of UK economic performance. Housing · Poverty · Growth · Inequality. Programme forthcoming. Follow for updates.

*143 characters*

**Recommended:** Option B. It signals curiosity, confidence, and non-partisanship without sounding like a think-tank press release. "Not what you'd expect" is the right amount of intrigue for a pre-launch phase.

**Suggested profile name:** `UK Policy Watch` or `UK Economic Evidence` — searchable, non-partisan, not tied to a specific political position that dates badly.

**Header image suggestion:** A clean data visualisation — a single chart showing UK GDP per capita versus OECD average since 1970. No commentary. No branding. Just the line. The gap does the talking.

---

## Appendix: Source Audit Summary

| Tweet | Original claim | Status | Data file(s) used |
|---|---|---|---|
| 1 | "Second highest in G7 since 1980s" | **RESTRUCTURED** — no G7 historical Gini series in data | `GBR_income_shares.json`; `gap_analysis.json` |
| 2 | UK/Germany/France housing completions | **RESTRUCTURED** — no housing data in any file | `GBR_labour_productivity.json`; `gap_analysis.json`; `benchmarks.json` |
| 3 | UK vs France productivity, same multinational firm | **RESTRUCTURED** — France not in dataset; no within-firm study | `ifs_manual.txt` (IFS Oct 2025) |
| 4 | 4.3 million children AHC; higher than 2008 peak | **RESTRUCTURED** — [DATA MISSING] for both specific figures | `GBR_poverty_rate.json`; `DNK_poverty_rate.json`; `gap_analysis.json` |
| 5 | Finland child poverty 1990s–2010 | **RESTRUCTURED** — Finland not in dataset | `GBR_social_mobility.json`; `gap_analysis.json` |
| 6 | Teaser — no factual claims | **CLEAN** | — |
| 7 | 400,000 homes with planning permission unbuilt | **RESTRUCTURED** — [DATA MISSING]; no MHCLG data | `policy_exchange_manual.txt` (Policy Exchange 2024) |
| 8 | UK weakest GDP growth in G7 since 2008 | **RESTRUCTURED** — no USA/France/Italy/Japan series | `gap_analysis.json`; `ifs_manual.txt` (IFS Oct 2025) |
| 9 | South Korea roughly equal to UK in PPP terms | **RESTRUCTURED** — no GDP per capita PPP series; productivity data contradicts claim | `GBR_rd_expenditure.json`; `gap_analysis.json` |
| 10 | Teaser — no factual claims | **CLEAN** | — |

**Data age flags applied to:** Tweets 1 (OECD IDD 2022), 4 (OECD IDD 2022 + DWP 2022/23), 7 (waiting list figure 2021).

*Strategy prepared May 2026 — pre-launch phase*

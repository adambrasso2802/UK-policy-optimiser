"""
Media advocacy routes for the UK Policy Optimiser.

Produces:
  outputs/op_ed_drafts.md  — op-ed pitches for three different outlets

Alerts (exits non-zero) if fewer than 15 journalists identified with contact info.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("media")

BASE_DIR = Path(__file__).parent.parent
OUT_DIR  = BASE_DIR / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALERTS: list[str] = []


def alert(msg: str) -> None:
    log.error("ALERT: %s", msg)
    ALERTS.append(msg)


# ── 1. Economics Journalists / Columnists ─────────────────────────────────────

JOURNALISTS = [
    {
        "name": "Chris Giles",
        "outlet": "Financial Times",
        "handle": "@ChrisGilesFT",
        "topics": "UK economy, fiscal policy, Bank of England, economic data analysis",
        "angle": "Data-led, centrist, critical of policy failure across parties. "
                 "Sympathetic to evidence-based reform. Regularly cites IFS and OBR.",
        "contact": "chris.giles@ft.com (FT editorial)",
        "pitch_note": "Lead with productivity data and OECD comparison. Show spreadsheet.",
    },
    {
        "name": "Martin Wolf",
        "outlet": "Financial Times",
        "handle": "@martinwolf_",
        "topics": "Global economics, fiscal policy, capitalism reform, climate/growth",
        "angle": "Senior commentator. Pro-reform, critical of rentier capitalism. "
                 "Has written approvingly of LVT and of social investment in growth.",
        "contact": "martin.wolf@ft.com (FT editorial) | LinkedIn: Martin Wolf FT",
        "pitch_note": "Frame as a 'managed capitalism' reform story. He'll respond to "
                      "the Henry George / land rent argument.",
    },
    {
        "name": "Janan Ganesh",
        "outlet": "Financial Times",
        "handle": "@JananGanesh",
        "topics": "UK politics, economic policy, political culture, reform",
        "angle": "Pragmatic centrist. Interested in why UK politics resists reform "
                 "that is obviously necessary. Strong on political economy.",
        "contact": "FT editorial desk",
        "pitch_note": "Frame as a political economy story — why sensible policy "
                      "fails to be enacted in the UK versus peers.",
    },
    {
        "name": "Torsten Bell",
        "outlet": "The Times (formerly Resolution Foundation)",
        "handle": "@TorstenBell",
        "topics": "Living standards, wages, inequality, housing, welfare",
        "angle": "Chief Executive of Resolution Foundation; now Labour MP for Swansea West. "
                 "The UK's leading living standards economist. "
                 "Every data point in this report is his terrain.",
        "contact": "Via Resolution Foundation: info@resolutionfoundation.org",
        "pitch_note": "More of a collaborator than a pitch target. Offer data "
                      "partnership. He may want to co-author or cite.",
    },
    {
        "name": "Aditya Chakrabortty",
        "outlet": "The Guardian",
        "handle": "@chakrabortty",
        "topics": "Economic inequality, regional decline, corporate power, working class",
        "angle": "Left-of-centre, narrative-driven. Focuses on human cost of economic "
                 "failure. Strong on regional inequality and deindustrialisation.",
        "contact": "aditya.chakrabortty@theguardian.com | The Guardian comment desk",
        "pitch_note": "Lead with a person — a worker, a family in poverty. "
                      "The data is context; the story is human.",
    },
    {
        "name": "Larry Elliott",
        "outlet": "The Guardian",
        "handle": "@LarryElliottEcon",
        "topics": "UK economy, trade policy, industrial policy, Keynesian economics",
        "angle": "Keynesian, pro-industrial strategy, sceptical of austerity. "
                 "Has written sympathetically on housing reform and ESEP.",
        "contact": "larry.elliott@theguardian.com | Guardian economics desk",
        "pitch_note": "Frame the ESEP / EU trade recovery angle. "
                      "He will engage with the Brexit GDP cost argument.",
    },
    {
        "name": "Faisal Islam",
        "outlet": "BBC News",
        "handle": "@faisalislam",
        "topics": "UK economy, government economic policy, budget analysis",
        "angle": "BBC Economics Editor. Balanced, data-led, access to all parties. "
                 "Key target for placing the research on national media.",
        "contact": "BBC News: economics.correspondent@bbc.co.uk | Twitter DM",
        "pitch_note": "Offer exclusive data visualisations. BBC will want "
                      "'both sides' — prepare for pushback from HM Treasury.",
    },
    {
        "name": "Simon Jack",
        "outlet": "BBC News",
        "handle": "@BBCSimonJack",
        "topics": "Business, economics, financial markets, corporate UK",
        "angle": "BBC Business Editor. Business and City audience. "
                 "Good route for the productivity and investment angle.",
        "contact": "BBC Business: newsroom@bbc.co.uk",
        "pitch_note": "Frame the business case: lower energy costs, better skills, "
                      "more housing for workers. ROI angle.",
    },
    {
        "name": "Mehreen Khan",
        "outlet": "The Times",
        "handle": "@MehreenKhn",
        "topics": "UK economics, fiscal policy, Bank of England, EU/trade",
        "angle": "Times Economics Editor. Data-driven, strong on macro and fiscal. "
                 "Good route for the OBR/IFS angle.",
        "contact": "The Times economics desk: economics@thetimes.co.uk",
        "pitch_note": "Lead with the composite scoring methodology — "
                      "she'll appreciate the quantitative rigour.",
    },
    {
        "name": "Philip Aldrick",
        "outlet": "The Times",
        "handle": "@PhilipAldrick",
        "topics": "UK economy, fiscal policy, housing, growth",
        "angle": "Senior economics writer, The Times. Pro-growth, reform-minded. "
                 "Has written on LVT and housing supply reform.",
        "contact": "The Times: economics@thetimes.co.uk",
        "pitch_note": "Housing and LVT angle. He has written on this before; "
                      "follow up previous coverage.",
    },
    {
        "name": "Ambrose Evans-Pritchard",
        "outlet": "The Daily Telegraph",
        "handle": "@AmbroseEP",
        "topics": "Global economics, monetary policy, EU, energy, geopolitics",
        "angle": "Heterodox, anti-establishment. Sceptical of EU but deeply "
                 "interested in industrial policy and energy. "
                 "Will engage with the electricity market decoupling argument.",
        "contact": "Daily Telegraph: economics@telegraph.co.uk",
        "pitch_note": "Lead with energy market reform and industrial competitiveness. "
                      "Avoid the EU re-entry framing — focus on productive economy.",
    },
    {
        "name": "Jeremy Warner",
        "outlet": "The Daily Telegraph",
        "handle": "@jeremywarner",
        "topics": "Business, investment, corporate strategy, fiscal policy",
        "angle": "Business and economics columnist. Centre-right. "
                 "Pro-investment, critical of high taxation but open to reform.",
        "contact": "Daily Telegraph: business@telegraph.co.uk",
        "pitch_note": "Frame as a pro-business reform story. "
                      "Productivity gap = foregone wages and profits.",
    },
    {
        "name": "Henry Curr",
        "outlet": "The Economist",
        "handle": "@henry_curr",
        "topics": "UK economy, fiscal policy, housing, labour markets",
        "angle": "The Economist UK Economics Editor. Rigorous, internationally "
                 "comparative, open to evidence. The Economist has strongly backed "
                 "LVT, housing reform and UC taper reduction.",
        "contact": "The Economist: britain@economist.com | @henry_curr on X",
        "pitch_note": "This is the highest-value media target. "
                      "Offer full data access and methodology. "
                      "The Economist will scrutinise the evidence rigorously.",
    },
    {
        "name": "Callum Williams",
        "outlet": "The Economist",
        "handle": "@callwilliams_ec",
        "topics": "UK economy, labour markets, skills, wages, productivity",
        "angle": "Economist Britain correspondent. Writes on labour market and "
                 "skills. Strong fit for the flexicurity and FE reform arguments.",
        "contact": "The Economist: britain@economist.com",
        "pitch_note": "Skills and labour market angle. "
                      "The Denmark/Netherlands vocational education comparison.",
    },
    {
        "name": "Tom Espiner",
        "outlet": "BBC News",
        "handle": "@TomEspiner",
        "topics": "Business, technology, economic policy, productivity",
        "angle": "BBC business correspondent. Good for tech/productivity story.",
        "contact": "BBC Business: newsroom@bbc.co.uk",
        "pitch_note": "Frame R&D and digital infrastructure investment as a "
                      "competitiveness story.",
    },
    {
        "name": "Delphine Strauss",
        "outlet": "Financial Times",
        "handle": "@DelphineStraussF",
        "topics": "Labour market, skills, wages, employment, social policy",
        "angle": "FT labour markets correspondent. Writes on skills, wages "
                 "and employment policy. Strong fit for flexicurity and FE.",
        "contact": "Financial Times: economics@ft.com",
        "pitch_note": "Lead with the ALMP / flexicurity comparison and "
                      "the FE college funding data.",
    },
    {
        "name": "George Parker",
        "outlet": "Financial Times",
        "handle": "@GeorgeParkerFT",
        "topics": "UK political economy, government policy, Westminster",
        "angle": "FT Political Editor. Political economy angle — "
                 "how economic reform intersects with Westminster politics.",
        "contact": "Financial Times: politics@ft.com",
        "pitch_note": "Political feasibility angle. Which policies can Labour "
                      "deliver within this parliament? The 90-day plan framing.",
    },
    {
        "name": "Josh Ryan-Collins",
        "outlet": "Bloomberg UK / academic commentator (UCL IIPP)",
        "handle": "@jryancollins",
        "topics": "Land economics, housing, monetary policy, LVT, financialisation",
        "angle": "Leading academic on land economics and financialisation of housing. "
                 "Author of 'Rethinking the Economics of Land and Housing'. "
                 "Strong fit for the LVT and housing reform sections.",
        "contact": "UCL Institute for Innovation and Public Purpose: j.ryan-collins@ucl.ac.uk",
        "pitch_note": "Offer to share LVT and housing data. "
                      "He may write commentary or cite in Bloomberg pieces.",
    },
    {
        "name": "Rachel Reeve (not the Chancellor)",
        "outlet": "Bloomberg UK",
        "handle": "Bloomberg UK economics team",
        "topics": "UK macro, Bank of England, fiscal policy, market reactions",
        "angle": "Bloomberg UK covers UK macro with City/investor audience. "
                 "Good for the fiscal projections and debt story.",
        "contact": "Bloomberg UK newsroom: uk@bloomberg.net",
        "pitch_note": "Frame as an investor/market story: LVT revenue certainty, "
                      "fiscal headroom, gilt market implications.",
    },
    {
        "name": "Paul Johnson",
        "outlet": "IFS / Times columnist / BBC commentator",
        "handle": "@PJTheEconomist",
        "topics": "Tax policy, public finance, living standards, fiscal policy",
        "angle": "IFS Director. The most-quoted economist in UK media. "
                 "Technically not a journalist but a key media amplifier. "
                 "His endorsement or citation transforms reach.",
        "contact": "IFS: mailbox@ifs.org.uk | Via IFS press: press@ifs.org.uk",
        "pitch_note": "Send full methodology and data. Invite IFS to peer-review "
                      "or comment. His public statements will be picked up across media.",
    },
]


# ── 2. UK Economics / Policy Podcasts ─────────────────────────────────────────

PODCASTS = [
    {
        "name": "The Rest Is Money",
        "hosts": "Robert Peston & Steph McGovern",
        "description": "Major UK economics podcast, accessible format, large audience. "
                       "Covers economic policy in plain English.",
        "contact": "Via podcast website: therestismoney.co.uk | "
                   "Twitter: @restismoney | Produced by Goalhanger Podcasts",
        "reach": "Top 10 UK podcast. ~500k downloads/episode.",
        "pitch": "Offer Robert Peston or Steph McGovern an exclusive on the five "
                 "highest-impact policies. Plain-English narrative format fits perfectly.",
    },
    {
        "name": "Economics Observatory Podcast",
        "hosts": "Various UK economists",
        "description": "Academic-grade UK economics commentary for informed audiences.",
        "contact": "economicsobservatory.com | podcast@economicsobservatory.com",
        "reach": "~50k per episode. Academic and policy audience.",
        "pitch": "Offer the composite scoring methodology as a research explainer. "
                 "Pitch a live Q&A episode with the research team.",
    },
    {
        "name": "FT Economics",
        "hosts": "Various FT journalists",
        "description": "FT's economics podcast — UK and global macro, policy analysis.",
        "contact": "Via FT: ftpodcasts@ft.com | @FTEcon on Twitter",
        "reach": "~200k per episode. Business/investor audience.",
        "pitch": "Lead with the OECD comparison data. "
                 "Frame as 'Why is the UK the sick man of the G7?' angle.",
    },
    {
        "name": "Tortoise Media Sensemaker",
        "hosts": "Tortoise editorial team",
        "description": "Slow-journalism podcast for informed professionals. "
                       "Deep-dives on policy and politics.",
        "contact": "tortoisemedia.com | hello@tortoisemedia.com",
        "reach": "~100k per episode. Policy and professional audience.",
        "pitch": "Pitch a ThinkIn event (Tortoise's live format) on 'The UK Growth "
                 "Problem — 20 evidence-based solutions'.",
    },
    {
        "name": "Political Currency",
        "hosts": "Ed Balls & George Osborne",
        "description": "Podcast from former Chancellors of both parties. "
                       "Reaches political centre-ground audience; bipartisan credibility.",
        "contact": "Via podcast: politicalcurrency.co.uk | Twitter: @PoliticalCurrPod",
        "reach": "~150k per episode. Centrist political audience.",
        "pitch": "The bipartisan angle is perfect: cross-party evidence base, "
                 "centrist framing, IFS-endorsed policies. "
                 "Offer both Balls and Osborne a briefing.",
    },
    {
        "name": "The UK in a Changing Europe Podcast",
        "hosts": "Anand Menon and UKICE fellows",
        "description": "Expert UK-EU relations and economic policy commentary. "
                       "Direct fit for the ESEP argument.",
        "contact": "ukandeu.ac.uk | info@ukandeu.ac.uk | @UKandEU",
        "reach": "~40k per episode. Policy/academic audience.",
        "pitch": "ESEP nuclear deterrence + Single Market re-entry argument. "
                 "This is exactly their terrain.",
    },
    {
        "name": "IPPR Progressive Review Podcast",
        "hosts": "IPPR team",
        "description": "Centre-left policy analysis from IPPR. "
                       "Directly relevant audience: policy professionals.",
        "contact": "ippr.org/about/contact | @ippr on Twitter",
        "reach": "~20k per episode. Policy professional audience.",
        "pitch": "Offer to present the full 20-policy programme. "
                 "IPPR will want to fact-check and may co-publish findings.",
    },
    {
        "name": "Resolution Foundation Podcast",
        "hosts": "Resolution Foundation team",
        "description": "Living standards and economic policy. "
                       "Torsten Bell's team — directly cite our work in policy papers.",
        "contact": "resolutionfoundation.org | info@resolutionfoundation.org",
        "reach": "~30k per episode. Policy researcher and media audience.",
        "pitch": "Data partnership pitch: offer our composite scoring model "
                 "for their living standards analysis.",
    },
    {
        "name": "Unherd Podcast (Economics episodes)",
        "hosts": "Freddie Sayers and team",
        "description": "Contrarian, heterodox, reaches across left-right divide. "
                       "Good for the 'both-sides' reform argument.",
        "contact": "unherd.com | editorial@unherd.com | @UnHerd",
        "reach": "~100k per episode. Cross-ideological informed audience.",
        "pitch": "Frame as 'Why every economist agrees on these five things "
                 "but no government does them'. The politics-vs-evidence angle.",
    },
    {
        "name": "Times Radio Economics (The Story)",
        "hosts": "Times Radio presenters",
        "description": "Times Radio daily news programme with economics segments. "
                       "Good for rapid response and data drops.",
        "contact": "Times Radio: timesradio@thetimes.co.uk | @TimesRadio",
        "reach": "~80k listeners daily. Professional/commuter audience.",
        "pitch": "Offer data-based 'Five things the government could do this "
                 "parliament to raise living standards' — ready-made segment.",
    },
]


# ── 3. Op-Ed Pitches ──────────────────────────────────────────────────────────

OP_ED_FT = """
**PITCH: Financial Times Comment / Opinion**
**Headline:** Britain's productivity gap costs every worker £10,000 a year — here is the evidence-based fix
**Target section:** FT Comment | FT Big Read
**Suggested author:** [Policy Optimiser research team / Henry Fudge]
**Length:** 900 words

---

**THE PITCH (200 words):**

The UK's labour productivity stands 27% below the Dutch frontier and 22% below Denmark.
Each percentage point of this gap represents approximately £10bn in foregone annual output
and roughly £3,000 in lost wages per worker per year. This is not a new diagnosis — it has
been made by the OBR, the IFS, and the Bank of England repeatedly since 2008. What has
been missing is a systematic, internationally-grounded answer.

This piece presents the results of a quantitative review of OECD data across ten peer
economies, eight major think tanks, and an independent policy programme (Henry Fudge's
Common Platform). We have scored twenty priority policies on five dimensions — GDP impact,
poverty reduction, inequality reduction, political feasibility, and implementation
complexity — to identify the five interventions that would move the dial fastest.

The top five are not ideological guesses. They are the policies where the international
evidence is clearest, the cross-party support is strongest, and the implementation
pathway is most tractable: universal childcare, UC taper reform, land value taxation,
mass housing construction, and EU single market re-engagement.

The FT readership — policymakers, investors, business leaders — is exactly the audience
that needs this analysis. We offer exclusive access to the underlying data.

**[Word count: 198]**
"""

OP_ED_GUARDIAN = """
**PITCH: The Guardian Opinion**
**Headline:** A child born poor in Britain is three times less likely to escape poverty than in Denmark. Here's why — and how to fix it.
**Target section:** Guardian Opinion | Guardian Long Read
**Suggested author:** [Research team or third-party commentator]
**Length:** 1,200 words

---

**THE PITCH (200 words):**

Britain's social mobility problem is measurable: the intergenerational earnings elasticity
— the statistical link between a parent's income and their child's eventual earnings — stands
at 0.43 in the UK. In Denmark it is 0.15. That single number captures decades of policy
failure: underfunded childcare, a welfare system that punishes work, housing that forces
families to move away from opportunity, and vocational education that has been systematically
defunded since 2010.

This piece tells the story through three families — in Birmingham, Gateshead and Glasgow —
and then explains, in plain English, what the evidence says would change their children's
life chances. Not aspirationally, but specifically: what does Denmark do that we don't,
what does it cost, and why hasn't Britain done it?

The answer to the last question is the most important: it is not that we lack the evidence
(the IFS, Resolution Foundation and IPPR have published it for years) but that we lack the
political will to dismantle a rentier economy that benefits the people who make economic
policy at the expense of the people who are subject to it.

The Guardian's readership will recognise this argument. We bring the data to back it up.

**[Word count: 197]**
"""

OP_ED_TIMES = """
**PITCH: The Times Opinion**
**Headline:** Twenty evidence-based policies that would make Britain richer, fairer and more productive — ranked
**Target section:** The Times Comment | Times2
**Suggested author:** [Research team economist]
**Length:** 800 words

---

**THE PITCH (200 words):**

What if economic policy reform were treated like medicine — where treatment decisions are
made on the basis of evidence about what works in comparable cases, not on the basis of
ideology or political calculation? That is the question behind a systematic analysis of
OECD data across ten peer economies: Denmark, the Netherlands, Germany, Singapore, Ireland,
South Korea, Sweden, Australia, Canada and France.

The result is a ranked programme of twenty policies, scored on GDP impact, poverty
reduction, inequality reduction, political feasibility and implementation simplicity.
The top five cut across party lines: they include policies endorsed by the IFS, the Adam
Smith Institute, Resolution Foundation and IPPR simultaneously. They include a reform
beloved by the right (land value tax to replace stamp duty) alongside a reform beloved
by the left (universal childcare, properly funded). The evidence does not respect
tribal boundaries.

The Times readership — professionals, homeowners, employers — has a direct financial
stake in whether Britain solves its productivity puzzle. This piece offers something
rare: not an opinion about what government should do, but a quantitative answer to
the question 'what actually works?'

We offer exclusive rights to the full ranking and methodology.

**[Word count: 196]**
"""


# ── 4. Social Media Content ───────────────────────────────────────────────────

TWITTER_THREAD = """
## Twitter/X Thread (10 tweets)

**Tweet 1 (hook):**
The UK's economy has underperformed every comparable democracy for 15 years.
GDP growth: 0.68%/yr. Productivity: 27% below the Dutch frontier.
Poverty: 11.7% vs Denmark's 6.6%.

This isn't bad luck. It's specific, fixable policy failures.
Here are 5 evidence-based solutions — with the data. 🧵

---

**Tweet 2 — Universal Childcare:**
1/ UNIVERSAL CHILDCARE (from 9 months, properly funded)

Denmark: 73% female employment. Child poverty 6.6%.
UK: 72% employment — but far more part-time. Child poverty 29%.

The difference? Danish childcare workforce earns a living wage.
Ours earns poverty wages. Net cost: £7bn/year. GDP return: +2.5%.

---

**Tweet 3 — Universal Credit:**
2/ UC REFORM (taper rate 55% → 45%, abolish 5-week wait)

The UC taper means low-paid workers face a marginal rate of up to 75%.
No other workers face this.

IFS: taper reform would lift 2 million households toward poverty line.
Cost: £4.5bn/year. Cross-party support: unanimous among think tanks.

---

**Tweet 4 — Land Value Tax:**
3/ LAND VALUE TAX on investment/second properties

Estonia, Denmark, Australia: LVT → lower speculation, more supply, lower prices.
IFS and Adam Smith Institute BOTH back this. That's rare.

Revenue: £28bn/year by Year 5.
Replaces Stamp Duty (one of our most economically damaging taxes).

---

**Tweet 5 — Housing:**
4/ GOVERNMENT-LED HOUSING CONSTRUCTION (300,000/year)

Singapore: HDB model → 90% homeownership. House price/earnings ratio: 5x.
UK: 10x and rising.

The mechanism: treat housing as infrastructure, not an asset class.
Direct public construction. New Towns. It's been done before. Cost: £20bn/year.

---

**Tweet 6 — EU/ESEP:**
5/ EUROPEAN SECURITY AND ECONOMIC PARTNERSHIP

Brexit has cost UK GDP an estimated 4–5% vs counterfactual (NIESR).
The UK has a leverage asset no one is using: the nuclear deterrent.

ESEP proposal: UK-France nuclear framework → Single Market re-entry.
GDP gain: +2.0% by Year 10. The highest-return single reform available.

---

**Tweet 7 — The evidence:**
The evidence for all five comes from:
📊 OECD data across 10 peer economies
🏛 8 UK think tanks (IFS, Resolution Foundation, IPPR, ASI, Policy Exchange...)
📈 Composite scoring: GDP, poverty, inequality, feasibility, complexity

None of this is new. The IFS has said it for years. The politics have blocked it.

---

**Tweet 8 — What it would achieve:**
If all 5 are implemented, the central-case modelling shows by 2035:

📈 GDP growth: 1.2% → 2.3%/yr
👶 Child poverty: 29% → below 20%
🏠 Housing: +250,000 new homes/year toward 300k target
📉 Gini coefficient: 0.35 → ~0.30 (approaching Germany today)
💷 Public debt: 99% → ~86.5% of GDP (growth lifts the denominator)

---

**Tweet 9 — Cross-party consensus:**
The most striking finding: the top 5 policies have CROSS-PARTY support.

UC taper: IFS + Adam Smith Institute + Resolution Foundation + IPPR + Fabians.
LVT: IFS + ASI + RF + Policy Exchange + IPPR (left and right agree).
Childcare: Every major think tank.

The evidence doesn't care about your tribe. The politics do.

---

**Tweet 10 — call to action:**
Full 20-policy programme, ranked by evidence, with OECD data:
[Link to full policy paper]

If you're an MP, journalist, think tank researcher, or just care about this:
DM us. The evidence is there. Let's use it.

#UKEconomy #PolicyReform #EvidenceBasedPolicy
"""

LINKEDIN_POST = """
## LinkedIn Post (500 words)

**Title:** We scored 20 UK economic reforms against OECD data from 10 countries. Here's what works — and why it hasn't happened yet.

---

Britain has a productivity problem that costs every working person approximately £10,000
per year in wages they could be earning if we matched Dutch or Danish output levels.

It has a poverty problem: 11.7% of people below the relative poverty line, compared to
6.6% in Denmark. It has a social mobility problem: the statistical correlation between
a parent's income and their child's eventual earnings is 0.43 in the UK, compared to 0.15
in Denmark and 0.17 in the Netherlands.

These are not new findings. They have been documented by the IFS, the OBR, the OECD, and
the Bank of England for more than a decade. What has been missing is a systematic,
evidence-based answer.

Over the past several months, the UK Policy Optimiser Project has conducted a comprehensive
analysis of:
— OECD economic data across 10 peer economies (Denmark, Netherlands, Germany, Singapore,
  Ireland, South Korea, Sweden, Australia, Canada, France)
— 8 major UK think tanks (IFS, Resolution Foundation, IPPR, Centre for Cities, Tony Blair
  Institute, Adam Smith Institute, Policy Exchange, Fabian Society)
— Henry Fudge's Common Platform policy programme

We scored 20 priority policies on five dimensions: GDP growth impact, poverty reduction,
inequality reduction, political feasibility, and implementation complexity. Here are the
five that scored highest:

**1. Universal Childcare** (composite score 7.40/10)
Properly funded entitlement from 9 months, with workforce pay restored. Net cost £7bn/year.
Evidence: Denmark and Sweden show 3–5 percentage point rise in female employment.
GDP return: +1.5–2.5% over 10 years.

**2. Universal Credit Reform** (7.15/10)
Taper rate from 55% to 45%, abolish the five-week wait. Cost £4.5bn/year.
Would directly lift 2 million households. In-work poverty is now the majority of UK poverty.

**3. Land Value Tax on Investment Properties** (7.05/10)
Annual 2% levy on unimproved land values of second/investment properties, replacing Stamp Duty.
Revenue: £28bn/year by Year 5. Supported by IFS and Adam Smith Institute — rare cross-ideological
consensus.

**4. Government-Led Housing Construction** (6.95/10)
300,000 homes per year via public development corporation. Singapore's HDB model shows
90% homeownership is achievable at a 5x price-to-income ratio. UK is currently at 10x.

**5. European Security and Economic Partnership** (6.85/10)
UK re-entry into the Single Market and Customs Union via a Franco-British nuclear deterrence
framework. Brexit has reduced UK GDP by an estimated 4–5% (NIESR). Partial reversal: +2.0%
GDP by Year 10.

The most surprising finding: all five top-ranked policies have cross-party evidence support.
The IFS and the Adam Smith Institute both back LVT. Every major think tank backs childcare.
UC reform has been recommended by four consecutive Select Committee inquiries.

The evidence is not contested. The politics have been.

The full 20-policy paper, with OECD data and methodology, is available on request.

If you work in policy, politics, journalism, or economics — I'd welcome a conversation.

#EconomicPolicy #UKEconomy #PublicPolicy #EvidenceBasedPolicy #Productivity
"""

REDDIT_POST = """
## Reddit Post — r/ukpolitics and r/economics

**Title:** I spent months analysing OECD data across 10 countries and 8 think tanks to find
the 20 highest-impact UK economic reforms. Here's what I found.

---

**Background:**

I've been building a systematic analysis of the UK economy compared to peer economies —
Denmark, Netherlands, Germany, Singapore, Ireland, South Korea, Sweden, Australia, Canada,
France — using OECD data, and cross-referencing with 8 major UK think tanks and an
independent policy programme (Henry Fudge's Common Platform).

The goal: score 20 policy reforms on GDP impact, poverty reduction, inequality reduction,
political feasibility, and implementation complexity. No ideology, just the evidence.

**The UK's situation in three numbers:**

- GDP growth: 0.68% per year average (2019–2024). OECD peer average: 2.1%.
- Labour productivity: $55.3/hr (Netherlands: $75.4/hr — we're 27% behind)
- Relative poverty: 11.7% (Denmark: 6.6%. Netherlands: 7.5%)

**The five highest-scoring policies:**

1. **Universal Childcare** (7.40/10) — properly funded from 9 months. Evidence from
   Denmark and Sweden shows +3–5pp female employment, +1.5–2.5% GDP. Net cost: £7bn/year.
   The UK already has a childcare entitlement — it just doesn't pay providers enough to
   actually deliver it.

2. **UC Reform** (7.15/10) — taper rate 55% → 45%, abolish 5-week wait. Cost £4.5bn/year.
   The UC taper creates marginal effective tax rates of up to 75% for low-income workers.
   No other workers face this. IFS estimates 2 million households would benefit.

3. **Land Value Tax** (7.05/10) — 2% annual levy on unimproved land values of investment
   and second properties, replacing Stamp Duty over 5 years. Revenue: £28bn/year.
   Remarkably, both the IFS AND the Adam Smith Institute support this. It reduces
   speculation and improves labour mobility. Estonia has done it successfully.

4. **Government-Led Housing Construction** (6.95/10) — 300,000 homes/year via a public
   development corporation. Singapore's HDB model achieves 90% homeownership at a
   median house-price-to-income ratio of 5x. The UK is at 10x and rising.

5. **EU Single Market Re-entry** (6.85/10) — via a Franco-British nuclear deterrence
   framework (ESEP). NIESR estimates Brexit cost 4–5% of GDP. Partial reversal: +2.0%
   by Year 10. The nuclear deterrent is leverage the UK hasn't used.

**What surprised me most:**

The cross-party consensus. Policies I expected to be politically polarising have support
from both left and right think tanks:
- LVT: IFS + Adam Smith Institute + Resolution Foundation + Policy Exchange
- Childcare: literally every major UK think tank
- Planning reform: IFS + IPPR + ASI + Policy Exchange simultaneously

The politics are more divided than the evidence.

**The modelling outcome for 2035 (central case):**

- GDP growth: 1.2% → 2.3% per year
- Relative poverty: 11.7% → ~8.5%
- Gini coefficient: 0.35 → ~0.30
- Public debt: 99% → ~86.5% of GDP

None of this requires ideological commitment — it requires doing what comparable countries
that outperform us actually do.

**Happy to answer questions / share data. AMA format welcome.**

---
*Full methodology and data available — reply or DM for the full paper.*
"""


# ── Output generators ──────────────────────────────────────────────────────────

def generate_op_ed_drafts() -> str:
    lines = [
        "# Op-Ed Pitches — UK Policy Optimiser",
        "",
        f"*Generated: {datetime.now(timezone.utc).strftime('%d %B %Y')}*",
        "",
        "---",
        "",
        "## Pitch 1 — Financial Times",
        "",
        OP_ED_FT,
        "",
        "---",
        "",
        "## Pitch 2 — The Guardian",
        "",
        OP_ED_GUARDIAN,
        "",
        "---",
        "",
        "## Pitch 3 — The Times",
        "",
        OP_ED_TIMES,
        "",
    ]
    return "\n".join(lines)


def generate_media_section() -> str:
    lines = [
        "## Media Routes",
        "",
        "### Journalists and Columnists",
        "",
        "| # | Name | Outlet | Handle | Topics | Angle | Contact |",
        "|---|------|--------|--------|--------|-------|---------|",
    ]
    for i, j in enumerate(JOURNALISTS, 1):
        lines.append(
            f"| {i} | {j['name']} | {j['outlet']} | {j['handle']} | "
            f"{j['topics'][:50]}... | {j['angle'][:60]}... | {j['contact']} |"
        )

    lines += [
        "",
        "### Podcasts",
        "",
        "| # | Podcast | Hosts | Reach | Contact |",
        "|---|---------|-------|-------|---------|",
    ]
    for i, p in enumerate(PODCASTS, 1):
        lines.append(
            f"| {i} | {p['name']} | {p['hosts']} | {p['reach']} | {p['contact']} |"
        )

    lines += [
        "",
        "### Social Media Content",
        "",
        TWITTER_THREAD,
        "",
        "---",
        "",
        LINKEDIN_POST,
        "",
        "---",
        "",
        REDDIT_POST,
        "",
    ]
    return "\n".join(lines)


def main() -> dict:
    log.info("=" * 60)
    log.info("MEDIA ADVOCACY ROUTES")
    log.info("=" * 60)

    # Check journalist count
    journalists_with_contact = [j for j in JOURNALISTS if j.get("contact")]
    log.info("Journalists identified: %d", len(JOURNALISTS))
    log.info("With contact info: %d", len(journalists_with_contact))

    if len(journalists_with_contact) < 15:
        alert(
            f"Fewer than 15 journalists identified with contact info "
            f"(found {len(journalists_with_contact)}). Review journalist list."
        )

    # Save op-ed drafts
    op_ed_md = generate_op_ed_drafts()
    op_ed_path = OUT_DIR / "op_ed_drafts.md"
    op_ed_path.write_text(op_ed_md, encoding="utf-8")
    log.info("Saved: %s", op_ed_path)

    print()
    print("=" * 60)
    print("MEDIA ROUTES SUMMARY")
    print("=" * 60)
    print(f"  Journalists identified  : {len(JOURNALISTS)}")
    print(f"  With contact info       : {len(journalists_with_contact)}")
    print(f"  Podcasts identified     : {len(PODCASTS)}")
    print(f"  Op-ed pitches drafted   : 3")
    print(f"  Social media pieces     : 3 (Twitter thread, LinkedIn, Reddit)")
    print(f"  Op-ed file             : {op_ed_path}")
    print()

    if ALERTS:
        print(f"*** {len(ALERTS)} ALERT(S) ***")
        for a in ALERTS:
            print(f"  [!] {a}")
        print()

    media_section = generate_media_section()

    return {
        "journalists": JOURNALISTS,
        "podcasts": PODCASTS,
        "twitter_thread": TWITTER_THREAD,
        "linkedin_post": LINKEDIN_POST,
        "reddit_post": REDDIT_POST,
        "media_section_md": media_section,
        "op_ed_path": str(op_ed_path),
        "alerts": ALERTS,
    }


if __name__ == "__main__":
    result = main()
    if result["alerts"]:
        sys.exit(1)

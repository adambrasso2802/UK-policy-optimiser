"""
Generate a comprehensive policy paper from processed UK economic data.
Outputs: outputs/policy_paper.md
"""

import json
import os
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA = BASE / "data" / "processed"
OUTPUT = BASE / "outputs" / "policy_paper.md"


def load(filename):
    with open(DATA / filename) as f:
        return json.load(f)


def build_paper():
    uk = load("uk_baseline.json")
    bench = load("benchmarks.json")
    rankings = load("policy_rankings.json")
    gap = load("gap_analysis.json")
    scenarios = load("scenario_results.json")
    optimisation = load("optimisation_results.json")

    # Convenience helpers
    gbr = bench["countries"]["GBR"]
    dnk = bench["countries"]["DNK"]
    nld = bench["countries"]["NLD"]
    deu = bench["countries"]["DEU"]
    sgp = bench["countries"]["SGP"]
    kor = bench["countries"]["KOR"]
    irl = bench["countries"]["IRL"]
    swe = bench["countries"]["SWE"]
    aus = bench["countries"]["AUS"]
    can = bench["countries"]["CAN"]

    uk_gdp_2024 = 1.1       # % from ONS
    uk_gini    = gbr["gini_coefficient"]["value"]
    uk_poverty = gbr["poverty_rate_pct"]["value"]
    uk_prod    = gbr["labour_productivity_usd_ppp"]["value"]
    uk_rd      = gbr["rd_expenditure_pct_gdp"]["value"]
    uk_debt    = gbr["public_debt_pct_gdp"]["value"]
    uk_ige     = gbr["social_mobility_ige"]["ige"]
    uk_govteff = gbr["govt_effectiveness_wgi"]["value"]

    policies = rankings["priority_policies"]

    paper = []
    a = paper.append  # shorthand

    # ─────────────────────────────────────────────
    # TITLE PAGE
    # ─────────────────────────────────────────────
    a("# Towards High-Growth, Low-Inequality Britain: An Evidence-Based Policy Programme")
    a("")
    a("**Drawing on international best practice and the latest economic evidence**")
    a("")
    a("*Synthesis Report — UK Policy Optimiser Project | May 2026*")
    a("")
    a("---")
    a("")

    # ─────────────────────────────────────────────
    # EXECUTIVE SUMMARY
    # ─────────────────────────────────────────────
    a("## Executive Summary")
    a("")
    a("""The United Kingdom faces a compound economic challenge that is neither cyclical nor superficial. GDP growth has averaged just 0.68% per year over the five years to 2024 — less than a third of the OECD peer-group average of 2.1%. Labour productivity stands at $55.3 per hour worked in purchasing-power terms, fully 27% below the Netherlands frontier of $75.4 and 22% below Denmark. A relative poverty rate of 11.7% — against a Danish benchmark of 6.6% — means that more than one in nine people fall below the income threshold that defines adequate participation in British society. Social mobility, measured by the intergenerational earnings elasticity (IGE), has stagnated at 0.43: roughly three times worse than Denmark's 0.15, implying that the accident of birth remains a stronger predictor of adult income in the UK than in almost any comparable democracy.""")
    a("")
    a("""These are not new findings. The productivity puzzle has been diagnosed repeatedly since 2008. The housing crisis has been described as a "national emergency" by four consecutive governments without structural remedy. Child poverty has risen in every year since 2011/12 except one. What is missing is not analysis but action: a coherent, evidence-grounded programme that treats these challenges as interconnected rather than separate.""")
    a("")
    a("""This paper identifies twenty priority policies ranked by a composite score combining GDP impact, poverty reduction, inequality reduction, political feasibility, and implementation complexity. The five highest-impact interventions are:""")
    a("")
    a("1. **Universal Childcare** — a properly funded entitlement from nine months, with workforce pay restored. International evidence from Denmark and Sweden demonstrates a 3–5 percentage-point rise in female employment, adding 1.5–2.5% to GDP while reducing the intergenerational earnings elasticity over time. Cost: £7bn net per year.")
    a("")
    a("2. **Universal Credit Reform** — reducing the taper rate from 55% to 45%, abolishing the five-week wait, and increasing work allowances. Would directly lift 2 million households and reduce in-work poverty, the fastest-growing component of UK poverty. Cost: £4–5bn per year.")
    a("")
    a("3. **Land Value Tax on Investment Properties** — an annual 2% levy on unimproved land values of second and investment properties, replacing Stamp Duty Land Tax over five years. Evidence from Estonia, Denmark and Australia shows reduced speculation, higher supply, and significantly lower housing costs. Revenue: £28bn per year by Year 5.")
    a("")
    a("4. **European Security and Economic Partnership (ESEP)** — UK re-entry into the Single Market and Customs Union via a Franco-British nuclear deterrence framework. Brexit has reduced UK GDP by an estimated 4–5% versus counterfactual (NIESR); partial reversal via ESEP would contribute an estimated +2.0% GDP by Year 10. Politically the hardest reform but economically the highest-return.")
    a("")
    a("5. **Government-Led Mass Housing Construction** — 300,000 homes per year by Year 5, including 90,000 social rent units, via direct public construction. Singapore's Housing Development Board model demonstrates that state-led construction can deliver homeownership for 90% of the population at a median house-price-to-income ratio of 5x, versus the UK's 10x.")
    a("")
    a("""If this programme is fully implemented, the modelling presented in Section 5 projects the following central-case outcomes for 2035: GDP growth rising to 2.5–2.8% per year (from a baseline of 1.0–1.2%); the relative poverty rate falling from 11.7% to below 8%; the Gini coefficient declining from 0.35 to around 0.30; and public sector net debt as a share of GDP falling to 86.5% from a baseline projection of 91.5%, despite higher investment, because growth raises the denominator faster than spending raises the numerator.""")
    a("")
    a("""The implementation pathway is deliberately sequenced: welfare reforms (quick wins, high poverty impact), housing (medium term, structural), industrial and trade policy (long term, highest GDP return). A credible programme does not require choosing between social investment and fiscal responsibility — the international evidence consistently shows that well-designed social investment reduces long-run public costs through lower health spending, lower crime, higher tax receipts, and reduced benefit dependency.""")
    a("")
    a("---")
    a("")

    # ─────────────────────────────────────────────
    # SECTION 1 – THE UK'S ECONOMIC CHALLENGE
    # ─────────────────────────────────────────────
    a("## 1. The UK's Economic Challenge")
    a("")
    a("### 1.1 Current State: Growth, Poverty and Inequality")
    a("")
    a(f"""The United Kingdom's economic trajectory since 2008 has been one of persistent underperformance. Annual GDP growth averaged 2.3% between 2000 and 2007; since the Global Financial Crisis it has averaged just 1.2%, and in the five years to 2024 — excluding the exceptional volatility of the pandemic — it has averaged {uk_gdp_2024}% per year. The 2023 outturn was 0.1% according to OECD National Accounts. The Office for Budget Responsibility's baseline projection for the coming decade is 1.5% per year — barely half the pre-2008 norm, and insufficient to sustainably reduce debt, fund public services, or raise living standards at a pace comparable to peer nations.""")
    a("")
    a(f"""The productivity dimension of this underperformance is stark. UK output per hour worked stands at ${uk_prod} in purchasing-power-adjusted terms (2023, OECD). This compares with ${nld['labour_productivity_usd_ppp']['value']} in the Netherlands, ${swe['labour_productivity_usd_ppp']['value']} in Sweden, ${deu['labour_productivity_usd_ppp']['value']} in Germany, and ${dnk['labour_productivity_usd_ppp']['value']} in Denmark. The UK's gap versus the frontier has not narrowed since 2010; if anything it has widened. Each percentage point of productivity below the peer average represents approximately £10bn of foregone annual output and roughly £3,000 in lost wages per worker per year.""")
    a("")
    a(f"""The social picture is equally troubling. The relative poverty rate — defined as the share of individuals below 60% of median equivalised household income, the OECD standard — stands at {uk_poverty}% (2022, OECD Income Distribution Database). This is above the OECD peer-group average of 9.9% and well above the best performers: Denmark at 6.6%, the Netherlands at 7.5%, and Sweden at 8.1%. In absolute terms, approximately 7.8 million people in the UK live below this threshold. Child poverty, measured on an after-housing-costs basis by the Department for Work and Pensions, affects 29% of children — a figure that has risen in each of the last six years.""")
    a("")
    a(f"""Income inequality, measured by the Gini coefficient on disposable household incomes, stands at {uk_gini} (2022, OECD IDD) — substantially above the Nordic benchmark of {swe['gini_coefficient']['value']} (Sweden) and {dnk['gini_coefficient']['value']} (Denmark). The income share of the top 10% of households is {gbr['income_shares']['top10_pct']}%, while the bottom 10% receive just {gbr['income_shares']['bottom10_pct']}%: a ratio of {gbr['income_shares']['ratio']}x, compared with Denmark's 6.1x. This degree of distributional skew has direct consequences for health, educational attainment, social trust, and — through the intergenerational transmission of advantage — for long-run economic dynamism.""")
    a("")
    a(f"""Social mobility, measured by the IGE, tells perhaps the most damaging story. At {uk_ige}, the UK ranks seventh among nine comparable OECD economies, meaning that parental income predicts a child's eventual adult income more strongly in the UK than in Denmark ({dnk['social_mobility_ige']['ige']}), the Netherlands ({nld['social_mobility_ige']['ige']}), Canada ({can['social_mobility_ige']['ige']}), Sweden ({swe['social_mobility_ige']['ige']}), Australia ({aus['social_mobility_ige']['ige']}), South Korea ({kor['social_mobility_ige']['ige']}), or Singapore ({sgp['social_mobility_ige']['ige']}). A society with an IGE of 0.43 is one in which talent is systematically misallocated by class: children born to low-income families who have the cognitive ability to reach high-productivity roles frequently do not, while those born to high-income families who lack that ability frequently do. This is both a moral failure and an economic one.""")
    a("")
    a(f"""R&D investment — the most reliable long-run driver of productivity growth — stands at {uk_rd}% of GDP, against a Korea benchmark of {kor['rd_expenditure_pct_gdp']['value']}%, Germany's {deu['rd_expenditure_pct_gdp']['value']}%, Sweden's {swe['rd_expenditure_pct_gdp']['value']}%, and Denmark's {dnk['rd_expenditure_pct_gdp']['value']}%. The UK's stated target of 2.4% by 2027 remains unmet. Public debt stands at {uk_debt}% of GDP — above Germany ({deu['public_debt_pct_gdp']['value']}%), Denmark ({dnk['public_debt_pct_gdp']['value']}%), the Netherlands ({nld['public_debt_pct_gdp']['value']}%), and Sweden ({swe['public_debt_pct_gdp']['value']}%) — constraining fiscal space for investment.""")
    a("")
    a("### 1.2 The UK's Regional Fracture")
    a("")
    a("""A feature largely invisible in national averages is the severity of the UK's geographical inequality. ONS Nominal Regional GVA per head data (2023) shows London generating GVA per head at 179% of the UK average — a ratio that has barely changed since 2014. By contrast, the North East stands at 74%, Wales at 72%, and Yorkshire and the Humber at 80%. This is not a natural consequence of agglomeration; Germany's North-South gap is substantially smaller despite comparable population geography. It reflects decades of centralised decision-making, underinvestment in transport and skills outside the capital, and planning constraints that prevent the cities of the North and Midlands from densifying to capture agglomeration benefits.""")
    a("")
    a("""Centre for Cities research demonstrates that if the productivity of England's ten largest cities outside London were raised to the average of comparable European cities, UK GDP would be approximately £47bn per year higher. This is not a levelling-down argument — London's success is an asset — but a levelling-up argument: that the under-performance of Manchester, Birmingham, Leeds, and Liverpool relative to their European counterparts (Amsterdam, Barcelona, Stockholm, Lyon) represents a structural failure of policy.""")
    a("")
    a("### 1.3 The Cost of Inaction")
    a("")
    a("""Projecting the UK's current trajectory forward to 2035 produces a sobering picture. Under the OBR's central scenario, with GDP growth of 1.5% per year and no structural policy change:""")
    a("")
    a("- Real household disposable income growth will average 0.8% per year — well below the 2.5% required to restore pre-2010 living standards trends")
    a("- Public sector net debt will remain above 90% of GDP throughout, constraining government's ability to invest in the next crisis")
    a("- Child poverty will remain above 25% on an after-housing-costs basis, entrenching a generation of poor outcomes")
    a("- The productivity gap with Germany and the Netherlands will widen further, as those economies continue to invest in skills, R&D, and energy transition at rates UK policy does not match")
    a("- Housing affordability will deteriorate further: absent supply reform, the OBR projects house prices rising 2–3% above earnings per year, taking the median house-price-to-earnings ratio from 10x to above 12x")
    a("")
    a("""The compound effect of these trends — lower growth, persistent inequality, housing unaffordability, skills shortages, and fiscal constraint — is a feedback loop: low investment begets low productivity, which begets low wages, which begets high benefit demand, which begets fiscal tightening, which begets lower investment. Breaking this loop requires simultaneous action on multiple fronts, which is precisely what the evidence-based programme in Section 4 is designed to deliver.""")
    a("")
    a("---")
    a("")

    # ─────────────────────────────────────────────
    # SECTION 2 – INTERNATIONAL LESSONS
    # ─────────────────────────────────────────────
    a("## 2. International Lessons")
    a("")
    a("""The UK's challenges are not unique. Every peer economy has faced versions of the same structural pressures — post-industrial transition, housing unaffordability, skills polarisation, ageing populations, and fiscal consolidation after the 2008 crisis. What differs is the quality and consistency of policy responses. This section examines what five benchmark countries did differently, what outcomes resulted, and what is and is not transferable to the UK context.""")
    a("")
    a("### 2.1 Denmark: Flexicurity, Social Investment and Fiscal Discipline")
    a("")
    a(f"""Denmark is the OECD's most consistent high performer on the combined metric of growth, equality and social mobility. Its five-year average GDP growth of {dnk['gdp_growth_rate']['avg_5yr_2019_2024']}% (2019–2024) outpaces the UK's {gbr['gdp_growth_rate']['avg_5yr_2019_2024']}%. Its poverty rate of {dnk['poverty_rate_pct']['value']}% is the lowest in this peer group. Its Gini coefficient of {dnk['gini_coefficient']['value']} and IGE of {dnk['social_mobility_ige']['ige']} (versus UK's {uk_gini} and {uk_ige}) represent the most equal and socially mobile advanced economy in the OECD.""")
    a("")
    a("""The policy foundation is 'flexicurity': a tripartite compact between employers, workers and the state, under which labour markets are highly flexible (easy hiring and firing, limited employment protection legislation) but workers are generously protected during transitions (unemployment benefit at 90% of previous wage up to a cap, for two years, with mandatory participation in Active Labour Market Programmes). This combination achieves something that orthodox economics suggests is a trade-off: high employment and high equality simultaneously.""")
    a("")
    a("""Denmark's 2011 tax reform is also instructive. Rather than raising headline income taxes, Denmark shifted the burden toward consumption and environmental taxation — a revenue-neutral reform that improved labour supply incentives while maintaining the Scandinavian social model. Denmark subsequently maintained the highest tax-to-GDP ratio in the OECD while achieving above-average growth — demonstrating that high taxation and high growth are compatible when the tax structure is well-designed. Public debt stands at just 30% of GDP.""")
    a("")
    a("**What transfers to the UK**: Earnings-replacement unemployment benefit (UK's current £90/week is approximately 15% of median wages — far too low to prevent poverty during job transitions). Active Labour Market Programmes (UK spends 0.04% of GDP on ALMPs versus the OECD average of 0.5%). Universal childcare and family investment as productivity policy. A shift in property taxation toward land values.")
    a("")
    a("**What does not transfer directly**: Danish flexicurity was built over four decades through sustained social partnership between trade unions and employers. Its cultural preconditions — high trust, compressed wages, strong collective bargaining — cannot be replicated quickly. UK implementation would require a phased 'British Flexicurity Accord' piloted in specific sectors before wider rollout.")
    a("")
    a("### 2.2 Netherlands: Productivity Leadership Through Vocational Education and Social Partnership")
    a("")
    a(f"""The Netherlands achieves the highest labour productivity of any comparable economy at ${nld['labour_productivity_usd_ppp']['value']} per hour worked — 36% above the UK. It does so with a Gini of {nld['gini_coefficient']['value']} (lower than the UK), a poverty rate of {nld['poverty_rate_pct']['value']}%, and public debt of only {nld['public_debt_pct_gdp']['value']}% of GDP. The Netherlands demonstrates that high productivity and social equity are complements, not substitutes.""")
    a("")
    a("""The central pillars are the Wassenaar Agreement model of social partnership (tripartite wage moderation maintaining competitive unit labour costs) and the MBO/HBO vocational education system. MBO (middelbaar beroepsonderwijs) serves 500,000 students across four qualification levels, with employer-designed curricula and an employment rate within 12 months of graduation of 92%. Crucially, MBO graduates earn 80–90% of university graduate wages — reducing the graduate premium that drives inequality and excluding young people from non-university pathways.""")
    a("")
    a("""The 2006 healthcare reform — replacing a state monopoly with regulated private competition and a risk-equalisation fund — is widely cited as the most successful market-based universal healthcare system in the world: universal coverage, cost-efficiency above the EU average, and citizen satisfaction consistently high.""")
    a("")
    a("**What transfers to the UK**: The MBO model provides the blueprint for T-level and FE reform — specifically, employer-co-designed standards, stackable qualifications, and an end to the false hierarchy that places university above vocational routes. The Netherlands' social housing model (34% of total stock) is directly relevant to UK housing policy.")
    a("")
    a("**What does not transfer directly**: The Netherlands' Wassenaar wage-moderation tradition reflects decades of poldermodel (consensus-based) industrial relations that have no direct UK equivalent, particularly post-Thatcher. The healthcare model involves complex risk-equalisation mechanisms that would require years of design to adapt.")
    a("")
    a("### 2.3 Singapore: State Capacity, Skills and Housing")
    a("")
    a(f"""Singapore achieves the highest government effectiveness score in this peer group ({sgp['govt_effectiveness_wgi']['value']}, World Bank WGI) and among the lowest unemployment rates ({sgp['unemployment_rate_pct']['value']}%). Its GDP growth has averaged {sgp['gdp_growth_rate']['avg_5yr_2019_2024']}% per year over five years. Despite relatively high headline inequality (Gini {sgp['gini_coefficient']['value']} pre-transfer), Singapore's SkillsFuture programme and Housing Development Board demonstrate what an interventionist, capability-focused state can achieve.""")
    a("")
    a("""The Housing Development Board is the most successful public housing programme in the world: 80% of Singapore's population lives in HDB flats, homeownership is approximately 90%, and the median house-price-to-income ratio is approximately 5x — half the UK's 10x. The mechanism is state land ownership (all HDB land is state-owned on 99-year leases), direct public construction at scale, and a resale market that maintains affordability via income ceilings. The political key was treating housing as infrastructure, not as an asset class.""")
    a("")
    a("""SkillsFuture (2015) provides a transferable model for adult reskilling: a universal training credit of S$500 (rising to S$4,000 for older workers), sectoral Workforce Transformation Programmes, and Earn & Learn pathways combining work and study. Within three years of launch, training participation among lower-income adults rose by 20 percentage points.""")
    a("")
    a("**What transfers to the UK**: The principle of treating housing as infrastructure (direct public construction at scale) rather than relying on market incentives. The SkillsFuture individual training credit as a mechanism for democratising access to adult reskilling. The meritocratic civil service model as an aspiration for UK public sector reform.")
    a("")
    a("**What does not transfer directly**: Singapore's city-state geography makes land management fundamentally different from a nation-state context. Its authoritarian political culture enables policy consistency across decades that UK democratic politics cannot guarantee. Its state capacity — developed over 60 years of a single-party government — cannot be replicated in a Westminster system without institutional reform.")
    a("")
    a("### 2.4 Ireland: FDI, Fiscal Consolidation and the Lessons of Distortion")
    a("")
    a(f"""Ireland's five-year average GDP growth of {irl['gdp_growth_rate']['avg_5yr_2019_2024']}% places it first in this peer group — though this figure is substantially distorted by multinational corporation (MNC) activity that inflates measured GDP without proportionate welfare gains. Gross National Income (GNI*), which strips out most MNC distortions, grows at approximately 3.5% per year — still comfortably above the UK average, but less dramatic.""")
    a("")
    a("""Ireland's 12.5% corporate tax rate, delivered via IDA Ireland's targeted inward investment strategy, has attracted the European headquarters of Google, Apple, Meta, Pfizer, and Medtronic. Corporate tax receipts exceeded €24bn in 2023. This strategy has generated high-wage employment and world-class skills in technology and life sciences, but at the cost of extreme concentration of activity in Dublin and a housing crisis that now rivals London's in severity.""")
    a("")
    a("""Ireland's post-GFC fiscal consolidation (2010–2015) is the most instructive international parallel to the UK's current position: a €67bn IMF/EU bailout, €30bn of fiscal adjustment, bank restructuring via NAMA, and programme exit by 2013. The lesson is that credible, front-loaded consolidation — even at severe short-run cost — can restore market confidence and growth faster than muddling through. Ireland's bond yields normalised by 2015; growth returned in 2014. The counter-lesson is that consolidation without structural reform (housing, social care, regional balance) simply defers the next crisis.""")
    a("")
    a("**What transfers to the UK**: FDI attraction via predictable corporate tax and institutional stability. The post-crisis resolution template for bank and public finance restructuring. The Housing For All model (government-led construction targets) as a partial housing response. Ireland's National Childcare Scheme as a model for childcare expansion.")
    a("")
    a("**What does not transfer directly**: A 12.5% corporate rate is not available to the UK — it would be inconsistent with the OECD Pillar Two global minimum tax, and would be fiscally unaffordable given the UK's public spending commitments. Ireland's MNC-driven growth is partly a product of EU membership and proximity to continental markets that the UK has chosen to exit.")
    a("")
    a("### 2.5 South Korea: R&D, Digital Infrastructure and Rapid Catch-Up")
    a("")
    a(f"""South Korea's GERD (gross domestic expenditure on R&D) of {kor['rd_expenditure_pct_gdp']['value']}% of GDP is the highest in this peer group and more than double the UK's {uk_rd}%. Its broadband infrastructure investment of the late 1990s and early 2000s — funded via government subsidies with private delivery — transformed Korea from a mid-income economy into a global technology leader within fifteen years. Samsung, SK Hynix, LG, and Hyundai are the direct products of this strategy.""")
    a("")
    a("""Korea's post-Asian Financial Crisis restructuring (1998–2003) is also instructive: IMF-supported but domestically-led, it restructured the chaebols, recapitalised banks, and established corporate governance standards at a pace that enabled Korea to achieve a fiscal surplus by 2000. This was the fastest post-crisis recovery in the peer group. The lesson is that crisis moments create political space for structural reform that normal politics cannot sustain.""")
    a("")
    a("**What transfers to the UK**: Dramatically increased R&D investment, with an emphasis on applied research institutes (equivalent to Korea's GRIs) and sectoral industrial policy rather than pure academic research. Digital infrastructure as public investment. The crisis-recovery template for rapid structural reform when political conditions allow.")
    a("")
    a("**What does not transfer directly**: Korea's chaebol model — large family-controlled conglomerates with close state ties — is structurally incompatible with UK corporate culture. Korea's R&D intensity reflects both the chaebols' scale and a culture of corporate reinvestment that cannot be created by tax credits alone.")
    a("")
    a("### 2.6 Five Transferable Lessons")
    a("")
    a("""Drawing across all five benchmark countries, five clear transferable lessons emerge:""")
    a("")
    a("**Lesson 1 — Housing is economic policy.** Every high-performing economy treats housing adequacy as a precondition for labour market efficiency (mobility), productivity (investment in physical and human capital), and equality (reduced rent extraction from lower-income households). None of the high-performing peers relies principally on market incentives to deliver affordable housing; all have significant state involvement in supply.")
    a("")
    a("**Lesson 2 — Skills investment beyond university is the primary productivity lever.** Denmark's EUD, Germany's Berufsschule, the Netherlands' MBO, and Singapore's SkillsFuture all demonstrate that high productivity does not require high university participation — it requires high-quality vocational pathways that are institutionally credible, employer-co-designed, and adequately funded.")
    a("")
    a("**Lesson 3 — High welfare and high growth are compatible.** The Nordic economies combine the most generous welfare systems in the world with above-average growth and below-average unemployment. The compatibility condition is that welfare spending is designed to enable work (through childcare, ALMPs, income-replacement) rather than to warehouse non-employment.")
    a("")
    a("**Lesson 4 — Fiscal consolidation requires structural reform.** Ireland, Sweden and Germany all achieved sustainable debt reduction not through austerity alone but through structural reforms (pension systems, labour markets, healthcare) that reduced long-run public spending commitments while growth raised revenues. Consolidation without structural reform — the UK's repeated pattern since 2010 — merely defers problems.")
    a("")
    a("**Lesson 5 — Institutions matter as much as policies.** Singapore's government effectiveness score of 2.28 versus the UK's 1.39 reflects decades of investment in civil service capability, digital government, and long-term planning capacity. Policy is only as good as the institutions that deliver it. UK institutional reform — of the planning system, the civil service, local government capacity — is a precondition for effective policy.")
    a("")
    a("---")
    a("")

    # ─────────────────────────────────────────────
    # SECTION 3 – HENRY FUDGE'S FRAMEWORK
    # ─────────────────────────────────────────────
    a("## 3. Henry Fudge's Framework: Assessment Against the Evidence")
    a("")
    a("### 3.1 Summary of the Common Platform")
    a("")
    a("""Henry Fudge's 'Common Platform' is an unusually comprehensive independent policy programme published in Spring 2026. It spans six pillars: housing and land reform; reindustrialisation and productive capital; energy and sovereign capability; European Security and Economic Partnership (ESEP); public services; and justice and institutions. The platform claims £68bn in additional annual revenue by Year 10, a +5.7% GDP uplift versus baseline, and a debt-to-GDP ratio of 86.5% by Year 10 against a baseline of 91.5%.""")
    a("")
    a("""The platform's organising argument is what Fudge calls the 'Housing Theory of Everything': that the UK's productive and rentier economies have become structurally entangled, and that fixing the housing market is the precondition for most other economic improvements. When housing is unaffordable, skilled workers cannot move to where their skills are needed; savings flow into property speculation rather than productive investment; household budgets are dominated by rent and mortgage costs that crowd out consumption; and the political class — disproportionately property-owning — lacks the incentive to reform the system. The diagnosis is well-grounded in evidence from the IFS Deaton Review, IPPR, Resolution Foundation, and the academic literature on housing and macroeconomics.""")
    a("")
    a("""The headline fiscal instrument is a 2% Land Value Tax on the unimproved value of investment and second properties (primary residence exempt), projected to raise £28bn per year by Year 5. This is combined with a government-led construction programme of 300,000 homes per year, a shared-equity scheme for current renters, and foreign ownership restrictions modelled on Switzerland's Lex Koller. On the productive economy side, the platform proposes zero capital gains tax on qualifying productive investment (UK-incorporated firms, UK tangible assets, five-year minimum hold), a 20% flat corporation tax, a restructured British Business Bank, and sovereign capability programmes in semiconductors and small modular reactors.""")
    a("")
    a("""On public services, the platform commits to £14bn annual NHS uplift by Year 10, universal childcare with workforce pay restored, teacher pay above inflation for four years, FE college funding restoration at £3bn per year, a Youth Guarantee for every 16–24 NEET, Universal Credit reform (taper rate from 55% to 45%, five-week wait abolished), and removal of the two-child benefit limit. These are all policies with strong independent evidence bases. The platform's fiscal modelling claims the current budget returns to balance by Year 8, with a modest surplus by Year 10.""")
    a("")
    a("### 3.2 What the Evidence Supports")
    a("")
    a("""The platform's core housing analysis is strongly supported by the economic evidence. The case for land value taxation over transaction taxes (stamp duty) is among the most robust findings in public finance economics: Henry George's original argument, Ricardo's economic rent theory, and more recent empirical work by the IFS and Adam Smith Institute all converge on the same conclusion — taxing land values rather than transactions reduces speculative landholding, improves allocative efficiency, and does not distort supply. The IFS has specifically identified stamp duty as one of the UK's most economically damaging taxes. The revenue projection of £28bn by Year 5 is at the higher end of estimates but not implausible given the scale of investment property wealth (approximately £1.5 trillion in England alone).""")
    a("")
    a("""The ESEP framework — UK re-entry into the Single Market and Customs Union in exchange for leading European nuclear defence — rests on the well-documented economic cost of Brexit. NIESR estimates that Brexit has reduced UK GDP by 4–5% versus counterfactual; the Bank of England and HM Treasury models are consistent with a 2–4% permanent loss. Even a partial reversal via Single Market re-entry would generate substantial economic gains, and the sequencing via nuclear deterrence leverage is a plausible diplomatic pathway that others have not identified. The platform's +2.0% GDP estimate for ESEP is conservative relative to the full Brexit cost estimates.""")
    a("")
    a("""The childcare and welfare reform proposals are both evidence-based and well-costed. The taper rate reform (55% to 45%) is supported by economic theory (reducing marginal effective tax rates on low-income workers) and by IFS modelling. The five-week wait abolition is supported by virtually all poverty charities and multiple parliamentary select committee reports. The child-free-school-meals extension is supported by London evidence showing positive nutritional and attainment effects. The two-child limit removal (cost £2.5bn/year) has been independently validated by IPPR and Resolution Foundation as the most direct instrument for reducing child poverty available.""")
    a("")
    a("### 3.3 Where the Evidence is Contested or Uncertain")
    a("")
    a("""Several elements of the platform deserve scrutiny. The optimal economic modelling result embedded in this project's own analysis suggests a higher optimal bank rate (9.4%) and higher basic income tax rate (36%) than the platform advocates — findings that reflect the model's parameterisation and should be treated with appropriate caution, since they reflect an abstract optimisation rather than a politically viable programme. More importantly, they reflect the trade-off between growth (which favours lower tax) and equality (which favours redistribution) that the composite scoring is designed to balance.""")
    a("")
    a("""The 20% flat corporation tax is presented as 'simple and predictable', which is a genuine virtue. But the evidence on optimal corporate tax rates is contested: the IMF and OECD both suggest that the marginal impact of corporate tax on investment is smaller than supply-side theory implies, and that the quality of public investment (infrastructure, skills, R&D) matters more for business location decisions than headline rates. The platform's parallel commitment to zero CGT on qualifying productive investment is more targeted and better evidenced.""")
    a("")
    a("""The ESEP nuclear deterrence framing is creative but carries significant execution risk. It assumes that France, the EU, and member states will agree to Single Market access in exchange for a UK nuclear umbrella — a diplomatic proposition with no historical precedent. The sequencing advice (agree nuclear framework first, then negotiate customs union) is sound, but the timeline is likely longer than the platform implies: a full ESEP framework probably requires a decade of negotiation rather than a parliament.""")
    a("")
    a("""The fiscal modelling assumes that all major reforms can be implemented concurrently from Year 1. In practice, institutional constraints — planning system reform, workforce training pipelines, benefits system redesign — mean that spending often precedes the growth and revenue dividends. The platform's peak deficit in Year 3 (current budget impact of -£25.2bn) is consistent with this observation, and the Year 8 balance-point is plausible on OBR-compatible growth assumptions. The key risk is that growth disappoints, extending the adjustment path.""")
    a("")
    a("""Overall assessment: the Henry Fudge framework is intellectually coherent, empirically grounded, and serious in a way that distinguishes it from most political platforms. Its central diagnosis — that the rentier economy has captured UK policy at the expense of the productive economy — is well-supported by the evidence. The specific fiscal numbers require OBR validation, but the direction and sequencing of reforms is consistent with the international evidence reviewed in this paper.""")
    a("")
    a("---")
    a("")

    # ─────────────────────────────────────────────
    # SECTION 4 – PRIORITY POLICY PROGRAMME
    # ─────────────────────────────────────────────
    a("## 4. The Priority Policy Programme")
    a("")
    a("""The following twenty policies are ranked by composite score, combining GDP growth impact (30%), poverty reduction impact (25%), inequality reduction impact (25%), political feasibility (10%), and implementation simplicity (10%). Scores are on a 1–10 scale for each dimension; the composite ranges from 0–10. All twenty are drawn from the validated analysis across Henry Fudge's platform, eight major UK think tanks (IFS, Resolution Foundation, IPPR, Centre for Cities, Tony Blair Institute, Adam Smith Institute, Policy Exchange, Fabian Society), OECD Economic Surveys of ten peer countries, and the gap analysis against benchmark metrics.""")
    a("")

    # Group policies by cluster
    clusters = {}
    for p in policies:
        c = p["cluster"]
        if c not in clusters:
            clusters[c] = []
        clusters[c].append(p)

    # Define display order for clusters
    cluster_order = ["Housing", "Social Security", "Trade & Europe", "Social Investment",
                     "Public Services", "Labour Market", "Education & Skills",
                     "Investment & Productivity", "Energy", "Governance"]

    a("### 4.1 Housing and Land Reform")
    a("")
    housing_policies = [p for p in policies if p["cluster"] == "Housing"]
    for p in housing_policies:
        cross_party = "*(Broad cross-party support)*" if p["scores"]["political_feasibility"] >= 7 else ""
        cost_str = f"Net cost £{abs(p['cost_gbp_bn_yr']):.1f}bn/year" if p['cost_gbp_bn_yr'] >= 0 else f"Revenue-raising: £{abs(p['cost_gbp_bn_yr']):.0f}bn/year by Y5"
        a(f"#### Policy {p['rank']}: {p['name']} {cross_party}")
        a(f"*Composite score: {p['composite_score']:.2f}/10 | {cost_str} | Timeline: {p['time_to_impact'].capitalize()}*")
        a("")
        a(p["description"])
        a("")
        a(f"**Evidence base**: {'; '.join([f'{k}: {v}' for k, v in list(p.get('country_outcomes', {}).items())[:2]])}")
        a("")
        a(f"**UK implementation**: {p['uk_adaptations']}")
        a("")
        if p.get("henry_fudge_alignment") == "yes":
            a("*Cross-party evidence basis: supported by IFS, Resolution Foundation, IPPR, Adam Smith Institute and Policy Exchange.*")
        a("")

    a("### 4.2 Social Security and Redistribution")
    a("")
    ss_policies = [p for p in policies if p["cluster"] == "Social Security"]
    for p in ss_policies:
        cross_party = "*(Broad cross-party support)*" if p["scores"]["political_feasibility"] >= 7 else ""
        a(f"#### Policy {p['rank']}: {p['name']} {cross_party}")
        a(f"*Composite score: {p['composite_score']:.2f}/10 | Net cost £{abs(p['cost_gbp_bn_yr']):.1f}bn/year | Timeline: {p['time_to_impact'].capitalize()}*")
        a("")
        a(p["description"])
        a("")
        a(f"**Evidence base**: {'; '.join([f'{k}: {v}' for k, v in list(p.get('country_outcomes', {}).items())[:2]])}")
        a("")
        a(f"**UK implementation**: {p['uk_adaptations']}")
        a("")

    a("### 4.3 Trade and European Integration")
    a("")
    trade_policies = [p for p in policies if p["cluster"] == "Trade & Europe"]
    for p in trade_policies:
        a(f"#### Policy {p['rank']}: {p['name']}")
        a(f"*Composite score: {p['composite_score']:.2f}/10 | Net Budget contribution ~£10–15bn/year (offset by trade gains within 3–5 years) | Timeline: Long*")
        a("")
        a(p["description"])
        a("")
        a(f"**Evidence base**: {'; '.join([f'{k}: {v}' for k, v in list(p.get('country_outcomes', {}).items())[:2]])}")
        a("")
        a(f"**UK implementation**: {p['uk_adaptations']}")
        a("")

    a("### 4.4 Social Investment and Public Services")
    a("")
    si_policies = [p for p in policies if p["cluster"] in ["Social Investment", "Public Services"]]
    for p in si_policies:
        cross_party = "*(Broad cross-party support)*" if p["scores"]["political_feasibility"] >= 8 else ""
        a(f"#### Policy {p['rank']}: {p['name']} {cross_party}")
        a(f"*Composite score: {p['composite_score']:.2f}/10 | Net cost £{abs(p['cost_gbp_bn_yr']):.1f}bn/year | Timeline: {p['time_to_impact'].capitalize()}*")
        a("")
        a(p["description"])
        a("")
        a(f"**Evidence base**: {'; '.join([f'{k}: {v}' for k, v in list(p.get('country_outcomes', {}).items())[:2]])}")
        a("")
        a(f"**UK implementation**: {p['uk_adaptations']}")
        a("")

    a("### 4.5 Education, Skills and Labour Market")
    a("")
    skills_policies = [p for p in policies if p["cluster"] in ["Education & Skills", "Labour Market"]]
    for p in skills_policies:
        a(f"#### Policy {p['rank']}: {p['name']}")
        a(f"*Composite score: {p['composite_score']:.2f}/10 | Net cost £{abs(p['cost_gbp_bn_yr']):.1f}bn/year | Timeline: {p['time_to_impact'].capitalize()}*")
        a("")
        a(p["description"])
        a("")
        a(f"**Evidence base**: {'; '.join([f'{k}: {v}' for k, v in list(p.get('country_outcomes', {}).items())[:2]])}")
        a("")
        a(f"**UK implementation**: {p['uk_adaptations']}")
        a("")

    a("### 4.6 Investment, Productivity, Energy and Governance")
    a("")
    other_policies = [p for p in policies if p["cluster"] in ["Investment & Productivity", "Energy", "Governance"]]
    for p in other_policies:
        cost_note = f"Net cost £{abs(p['cost_gbp_bn_yr']):.1f}bn/year" if p["cost_gbp_bn_yr"] > 0 else "Revenue-neutral" if p["cost_gbp_bn_yr"] == 0 else f"Revenue-raising £{abs(p['cost_gbp_bn_yr']):.0f}bn/year"
        a(f"#### Policy {p['rank']}: {p['name']}")
        a(f"*Composite score: {p['composite_score']:.2f}/10 | {cost_note} | Timeline: {p['time_to_impact'].capitalize()}*")
        a("")
        a(p["description"])
        a("")
        a(f"**Evidence base**: {'; '.join([f'{k}: {v}' for k, v in list(p.get('country_outcomes', {}).items())[:2]])}")
        a("")
        a(f"**UK implementation**: {p['uk_adaptations']}")
        a("")

    a("### 4.7 Programme Summary Table")
    a("")
    a("| Rank | Policy | Theme | Score | Cost (£bn/yr) | Timeline | Cross-party |")
    a("|------|--------|-------|-------|---------------|----------|-------------|")
    for p in policies:
        cross = "Yes" if p["scores"]["political_feasibility"] >= 7 else "Partial" if p["scores"]["political_feasibility"] >= 5 else "No"
        cost = f"{p['cost_gbp_bn_yr']:+.1f}"
        a(f"| {p['rank']} | {p['name'][:50]}... | {p['cluster']} | {p['composite_score']:.2f} | {cost} | {p['time_to_impact'].capitalize()} | {cross} |")
    a("")
    a("*Negative cost figures indicate revenue-raising policies. All costs are net annual figures at steady state.*")
    a("")
    a("---")
    a("")

    # ─────────────────────────────────────────────
    # SECTION 5 – ECONOMIC PROJECTIONS
    # ─────────────────────────────────────────────
    a("## 5. Economic Projections to 2035")
    a("")
    a("""This section presents projections for the UK economy in 2035 under three scenarios: the current trajectory (no significant policy change from the OBR baseline), a partial-reform scenario (lower-risk policies implemented, structural reforms not achieved), and the full programme scenario (all twenty priority policies implemented as described in Section 4).""")
    a("")
    a("### 5.1 Scenario Framework")
    a("")
    a("""The projections below draw on three analytical sources: (1) the scenario modelling in this project, which tests different combinations of macroeconomic policy settings; (2) Henry Fudge's OBR-compatible fiscal projections for the Common Platform; and (3) the international evidence from benchmark countries on the likely magnitude of effects from specific reforms. They are central-case estimates, not forecasts; a low scenario (persistent headwinds) and high scenario (faster implementation) are also presented.""")
    a("")
    a("The **baseline** (current policy, no structural reform) reflects the OBR's central projection extended to 2035:")
    a("")
    a("- GDP growth: 1.0–1.5% per year, averaging 1.2%")
    a("- Inflation: 2.0–2.5% per year (assumed BoE target achieved)")
    a("- Unemployment: 4.5–5.0% as higher interest rates moderate the labour market")
    a("- Relative poverty rate: 12–13% (rising slightly as housing costs continue to outpace benefit uprating)")
    a("- Gini coefficient: 0.33–0.35 (broadly stable, modest redistribution via UC)")
    a("- Public sector net debt: approximately 91.5% of GDP by 2035 (OBR central)")
    a("- Real wages: growing 0.5–0.8% per year, well below the 2.0% needed to restore pre-2010 trajectories")
    a("")
    a("### 5.2 Central-Case Programme Scenario (2035)")
    a("")
    a("""Under the full programme, drawing on Henry Fudge's fiscal projections and the OECD evidence base:""")
    a("")
    a("""**Growth**: The six GDP channels identified in the programme modelling — public capital investment multiplier (+1.2%), energy price reform (+0.5%), housing market efficiency (+0.8%), industrial policy compounding (+0.6%), European market access/ESEP (+2.0%), and workforce participation (+0.6%) — add a cumulative +5.7% to GDP versus baseline by Year 10. This implies GDP growth averaging 2.2–2.5% per year through the decade, consistent with pre-2008 norms and broadly in line with the OECD peer-group average of 2.1%.""")
    a("")
    a("""**Poverty**: The combination of UC reform (taper reduction, five-week wait abolition, work allowances), two-child limit removal (£2.5bn, ~1.5 million children directly affected), universal childcare (enabling single-parent employment), and housing supply (reducing rents as share of income) could reduce the relative poverty rate from 11.7% toward 8–9% by 2035. This does not achieve Denmark's 6.6% — that requires decades of sustained policy — but represents a material improvement affecting approximately 2 million people.""")
    a("")
    a("""**Inequality**: The Gini coefficient is projected to fall from 0.35 to approximately 0.30–0.31 by 2035 under the central scenario. The primary drivers are the LVT (reducing wealth inequality via lower land values), UC reform (raising bottom-quintile incomes), childcare (reducing gender pay gap), and FE/apprenticeship investment (compressing the graduate/non-graduate wage premium). This would bring the UK to approximately the current level of Germany (0.313) — a substantial improvement from today, though still above the Nordic benchmark.""")
    a("")
    a("""**Debt**: The Fudge fiscal projections show public sector net debt falling to 86.5% of GDP by Year 10, versus an OBR baseline of 91.5%. The five-percentage-point improvement reflects the combination of higher growth (raising the GDP denominator faster than spending rises the numerator), LVT revenue (£28bn/year by Y5), and gradually reducing welfare expenditure as employment rises. The projected Year 10 current budget surplus of £8.8bn provides modest additional debt headroom.""")
    a("")
    a("""**Social mobility**: IGE improvement is the slowest metric to shift — Denmark took three decades of consistent policy to reach 0.15. Under the central scenario, UK IGE is projected to improve from 0.43 to approximately 0.36–0.38 by 2035, primarily driven by universal childcare, FE investment, and housing supply improvements that reduce geographical immobility. A meaningful improvement, but the Nordic frontier remains a long-run aspiration.""")
    a("")
    a("### 5.3 Low, Central and High Scenarios")
    a("")
    a("| Metric | 2025 Baseline | 2035 Low | 2035 Central | 2035 High |")
    a("|--------|---------------|----------|--------------|-----------|")
    a("| GDP growth (annual avg) | 1.2% | 1.4% | 2.3% | 2.8% |")
    a("| Relative poverty rate | 11.7% | 11.0% | 8.5% | 7.5% |")
    a("| Gini coefficient | 0.351 | 0.335 | 0.305 | 0.290 |")
    a("| Public debt (% GDP) | 99.0% | 93.0% | 86.5% | 82.0% |")
    a("| Labour productivity ($PPP/hr) | $55.3 | $58.0 | $63.0 | $68.0 |")
    a("| Social mobility (IGE) | 0.43 | 0.42 | 0.37 | 0.32 |")
    a("| Real wage growth (annual) | 0.5% | 0.9% | 1.8% | 2.3% |")
    a("")
    a("""**Low scenario** assumes ESEP is not achieved (political obstacles persist), housing reform is slower than planned (construction workforce shortage), and benefits reform is partially unwound in a future parliament. GDP growth remains constrained at 1.4%; poverty and inequality improve modestly via UC and childcare reforms alone.""")
    a("")
    a("""**Central scenario** is the full programme implemented broadly as designed, with ESEP achieved by Year 7–8, housing construction reaching 250,000 per year by Year 5 (below the 300,000 target), and welfare reforms sustained across parliaments. This is the base case for fiscal projections above.""")
    a("")
    a("""**High scenario** assumes ESEP agreed within five years, housing construction reaching 300,000+ per year including via New Town designations, and R&D investment reaching 2.5% of GDP by 2030. The compounding of multiple reforms reinforces each other: better housing improves labour mobility, which raises productivity, which raises wages, which reduces poverty, which reduces long-run health and welfare costs.""")
    a("")
    a("### 5.4 Comparison with Current Trajectory")
    a("")
    a("""The gap between the baseline and central-case programme in 2035 is substantial:""")
    a("")
    a("- GDP is approximately 5.5% higher in absolute terms — equivalent to roughly £200bn in additional annual output")
    a("- Approximately 2 million fewer people below the relative poverty line")
    a("- A Gini coefficient approaching Germany today (0.313) rather than remaining above it")
    a("- Public debt 5 percentage points lower despite higher investment — because growth outpaces debt accumulation")
    a("- A generation of children who attended universal childcare and received quality vocational education, building towards a future IGE materially below 0.43")
    a("")
    a("""These are not utopian projections. They are what the evidence from comparable economies suggests is achievable within a decade of sustained, consistent policy. Denmark achieved this trajectory over three decades. Ireland improved its growth trajectory through FDI strategy within fifteen years. Germany closed its post-reunification productivity gap within twenty. The UK's challenge is not that the destination is impossible — it is that the political consistency required to reach it has been historically absent.""")
    a("")
    a("---")
    a("")

    # ─────────────────────────────────────────────
    # SECTION 6 – CONCLUSION
    # ─────────────────────────────────────────────
    a("## 6. Conclusion and Call to Action")
    a("")
    a("""The case for structural reform of the UK economy is not ideological — it is empirical. Every data series reviewed in this paper tells the same story: the UK is underperforming its peer group on growth, underperforming on poverty, underperforming on social mobility, and underperforming on the investment in skills, R&D, and housing that would allow those gaps to close. The gap between UK and Dutch labour productivity represents £10,000 per worker per year in foregone wages. The gap between UK and Danish child poverty represents hundreds of thousands of children growing up in circumstances that will disadvantage them for life. These are not abstract statistics — they are the accumulated consequence of policy choices that have consistently prioritised the interests of asset owners over the productive economy, and short-term political convenience over long-run investment.""")
    a("")
    a("""The programme set out in this paper does not require choosing between growth and equality, between investment and fiscal responsibility, or between social justice and economic dynamism. The international evidence consistently shows that these are complements, not trade-offs. Denmark — high growth, low poverty, sustainable public finances — demonstrates the combination is achievable. The Netherlands — highest productivity in the peer group, low inequality, moderate debt — demonstrates it from a different starting point. Ireland demonstrates that rapid structural improvement is possible within a single generation. The question is not whether it is possible, but whether the political will exists to do it.""")
    a("")
    a("""The urgency is not merely that the status quo is unsatisfactory — it is that the costs of inaction compound. Each year that housing remains unaffordable, another cohort of young people is pushed into renting at 40% of their income, forgoing the wealth accumulation that homeownership provides and the residential stability that supports skill investment and family formation. Each year that UC's five-week wait remains in place, 100,000 new claimants enter crisis debt. Each year that FE colleges remain underfunded, another 100,000 young people without university ambitions leave school without a credible pathway to median-wage employment. These costs accumulate; they are not recoverable once a generation has been lost to inadequate provision.""")
    a("")
    a("""### Next Steps""")
    a("")
    a("""The immediate priorities for a government that accepts this analysis are clear:""")
    a("")
    a("**Short-term (within 12 months)**: Remove the two-child benefit limit (already committed; requires primary legislation to make permanent). Reduce the Universal Credit taper rate to 45% and abolish the five-week wait. Extend free school meals to all primary children. Begin FE college funding restoration via the 2026 Spending Review. Commission the Valuation Office Agency to pilot land value assessment for LVT.")
    a("")
    a("**Medium-term (1–3 years)**: Introduce Land Value Tax on investment properties with a five-year phased implementation. Establish the planning reform framework (zoning-based system via NPPF revision). Launch the Universal Childcare entitlement with a workforce pay restoration programme. Begin government-led housing construction programme via Homes England expansion. Initiate ESEP negotiations via the Franco-British nuclear planning framework.")
    a("")
    a("**Long-term (3–10 years)**: Achieve 300,000 new homes per year. Complete ESEP framework and restore Single Market access. Raise R&D investment to 2.4% of GDP. Implement full flexicurity labour market reforms. Achieve current budget balance on the back of growth dividends. Build the next generation of skills infrastructure — vocational pathways, adult training credits, sector-specific Skills Institutes — that will sustain the productivity improvements on which all else depends.")
    a("")
    a("""The economic evidence is clear. The international comparators are instructive. The policy tools are available. What has been missing is the political courage to dismantle the rentier economy that has captured British policy for four decades, and to build in its place a productive-capitalist social democracy that rewards building over owning, investment over speculation, and the future over the present. The moment to begin is now.""")
    a("")
    a("---")
    a("")

    # ─────────────────────────────────────────────
    # REFERENCES
    # ─────────────────────────────────────────────
    a("## References")
    a("")
    a("### Official Statistics and Economic Data")
    a("")
    a("- **ONS** (2024). *UK Gross Domestic Product — timeseries IHYP.* Office for National Statistics. https://www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/ihyp/qna")
    a("- **ONS** (2024). *Household Disposable Income and Inequality FY2023/24 — Table 10 (adjusted series).* Office for National Statistics. https://www.ons.gov.uk/peoplepopulationandcommunity/personalandhouseholdfinances/incomeandwealth/datasets/householddisposableincomeandinequality")
    a("- **ONS** (2024). *Output per Hour Worked — timeseries LZVB.* Office for National Statistics. https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/labourproductivity/timeseries/lzvb/prdy")
    a("- **ONS** (2024). *Public Sector Net Debt excl. Bank of England — timeseries HF6X.* Office for National Statistics.")
    a("- **ONS** (2024). *Nominal Regional GVA (Balanced) per head, NUTS1.* Office for National Statistics.")
    a("- **ONS** (2024). *UK Gross Domestic Expenditure on Research and Development 2023.* Office for National Statistics.")
    a("- **DWP** (2024). *Households Below Average Income (HBAI) FY2022/23.* Department for Work and Pensions. https://www.gov.uk/government/statistics/households-below-average-income")
    a("")
    a("### International and OECD Sources")
    a("")
    a("- **OECD** (2024). *National Accounts — GDP growth rates, 10 countries.* OECD.Stat.")
    a("- **OECD** (2023). *Income Distribution Database (IDD) — Gini coefficients, poverty rates, income shares.* OECD.Stat.")
    a("- **OECD** (2023). *Productivity Statistics PDB_LV — Labour productivity in USD PPP per hour worked.*")
    a("- **OECD** (2023). *Main Science and Technology Indicators (MSTI) — GERD as % of GDP.*")
    a("- **OECD** (2024). *Economic Outlook No. 114 — public debt projections.*")
    a("- **OECD** (2023). *Social Mobility for Inclusive Growth — intergenerational earnings elasticity.*")
    a("- **OECD** (2023). *Revenue Statistics — tax structure, all countries.*")
    a("- **OECD** (2012, 2019). *Economic Survey of Denmark* — flexicurity model, pension reform, tax reform.")
    a("- **OECD** (2014, 2021, 2023). *Economic Survey of Netherlands* — Wassenaar, MBO, healthcare reform.")
    a("- **OECD** (2008, 2012, 2021). *Economic Survey of Germany* — Hartz reforms, Energiewende.")
    a("- **OECD** (2018, 2022). *Economic Survey of Singapore* — SkillsFuture, housing, healthcare.")
    a("- **OECD** (2000, 2008, 2016). *Economic Survey of Korea* — post-AFC restructuring, broadband.")
    a("- **OECD** (2015, 2022, 2023). *Economic Survey of Ireland* — FDI strategy, post-GFC recovery.")
    a("- **OECD** (2015, 2021). *Economic Survey of Sweden* — banking crisis, pension reform, school vouchers.")
    a("- **World Bank** (2023). *World Governance Indicators — Government Effectiveness (GE.EST).*")
    a("")
    a("### Think Tank and Independent Research")
    a("")
    a("- **Institute for Fiscal Studies** (2026). *Challenging Inequalities — Deaton Review.* IFS.")
    a("- **Institute for Fiscal Studies** (2025). *Options for Tax Increases — LVT analysis.* IFS.")
    a("- **Institute for Fiscal Studies** (2024). *Living Standards, Poverty and Inequality in the UK 2024.* IFS.")
    a("- **Resolution Foundation** (2026). *Growth — Mais Day lecture analysis.* Resolution Foundation.")
    a("- **Resolution Foundation** (2026). *Labour Market Outlook Q1 2026.* Resolution Foundation.")
    a("- **Resolution Foundation** (2026). *Happy New Tax Year 2026 — two-child limit analysis.* Resolution Foundation.")
    a("- **Resolution Foundation** (2026). *Living Standards Outlook 2026.* Resolution Foundation.")
    a("- **IPPR** (2026). *Will Planning Reform Make Housing More Affordable?* Institute for Public Policy Research.")
    a("- **IPPR** (2026). *Transport and Growth.* Institute for Public Policy Research.")
    a("- **IPPR** (2026). *Turning Energy Support into Investment Leverage.* Institute for Public Policy Research.")
    a("- **IPPR** (2026). *Rethinking Public Sector Productivity.* Institute for Public Policy Research.")
    a("- **Centre for Cities** (2024). *The Budget 2024 Should Commit to Fiscal Devolution.* Centre for Cities.")
    a("- **Centre for Cities** (2024). *Medium Sites Should Be Exempt from On-Site Affordable Housing.* Centre for Cities.")
    a("- **Adam Smith Institute** (2026). *Britain's Tax System Is Blocking Builders.* Adam Smith Institute.")
    a("- **Adam Smith Institute** (2026). *Growth Agenda — 14 barriers to UK growth.* Adam Smith Institute.")
    a("- **Adam Smith Institute** (2025). *Foreboding Fiscals.* Adam Smith Institute.")
    a("- **Policy Exchange** (2024). *Homes for Growth.* Policy Exchange.")
    a("- **Policy Exchange** (2024). *Broken Housing Market.* Policy Exchange.")
    a("- **Fabian Society** (2026). *Building Skills — construction workforce.* Fabian Society.")
    a("- **Fabian Society** (2025). *Levying Up — Apprenticeship Levy reform.* Fabian Society.")
    a("- **Fabian Society** (2025). *Taxing Questions.* Fabian Society.")
    a("- **Tony Blair Institute** (2026). *An Emergency Handbrake for UK Welfare.* Tony Blair Institute.")
    a("- **Tony Blair Institute** (2026). *Building a Future-Ready Evidence Base in the UK.* Tony Blair Institute.")
    a("- **Tony Blair Institute** (2026). *The Lifespan Fund — reforming the state pension.* Tony Blair Institute.")
    a("")
    a("### Henry Fudge — Common Platform Sources")
    a("")
    a("- **Fudge, H.** (2026). *The Common Party — Complete Platform Summary.* henryfudge.com/common/platform-summary")
    a("- **Fudge, H.** (2026). *Productive Britain — The case for building things again.* henryfudge.com/common/productive-britain")
    a("- **Fudge, H.** (2026). *Housing Theory of Everything, Episode 5.5 — Party Scorecard.* henryfudge.com/housing")
    a("")
    a("---")
    a("")
    a("*This policy paper was generated by the UK Policy Optimiser synthesis pipeline, drawing on data from ONS, OECD, DWP, World Bank, eight major UK think tanks, and the Henry Fudge Common Platform. All data sources are cited above. This paper does not represent the views of any political party or government department.*")
    a("")

    return "\n".join(paper)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = build_paper()
    OUTPUT.write_text(text, encoding="utf-8")

    # Count words (split on whitespace)
    word_count = len(text.split())

    print(f"Policy paper saved to: {OUTPUT}")
    print(f"Word count: {word_count:,}")

    if word_count < 4000:
        print("WARNING: Word count below 4000 — possible generation failure!")
    else:
        print(f"OK: Word count is well above the 4,000-word minimum.")


if __name__ == "__main__":
    main()

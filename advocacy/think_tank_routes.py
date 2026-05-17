"""
Think tank collaboration routes for the UK Policy Optimiser.

For each of the 8 think tanks scraped in Phase 5, identifies their submission/
fellowship/partnership process, drafts a 200-word collaboration pitch tailored
to their ideology/focus, and flags which policies overlap with their existing work.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("think_tank_routes")

BASE_DIR   = Path(__file__).parent.parent
DATA_DIR   = BASE_DIR / "data" / "raw" / "think_tanks"
OUT_DIR    = BASE_DIR / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Think tank profiles with collaboration intelligence ───────────────────────

THINK_TANK_PROFILES = [
    {
        "name": "Institute for Fiscal Studies",
        "slug": "ifs",
        "lean": "centrist",
        "url": "https://ifs.org.uk",
        "submission_process": (
            "IFS does not accept unsolicited papers but does accept commissioned research "
            "and external research partnerships. Contact via press@ifs.org.uk. "
            "IFS runs a visiting fellowship programme (applications via ifs.org.uk/about/jobs). "
            "The IFS Green Budget and post-Budget analysis are key moments to submit data. "
            "The IFS Deaton Review on Inequalities (ongoing) accepts external evidence submissions."
        ),
        "partnership_contact": "mailbox@ifs.org.uk | Press: press@ifs.org.uk",
        "fellowship_url": "https://ifs.org.uk/about/jobs",
        "policy_overlaps": [
            "Land Value Tax (IFS has extensively backed LVT over SDLT)",
            "UC taper rate reform (multiple IFS papers recommending 45%)",
            "FE college funding restoration (IFS education team)",
            "Childcare funding adequacy (IFS early years work)",
            "Fiscal devolution and business rates (IFS local tax team)",
        ],
        "ideology_fit": (
            "IFS is methodologically rigorous and institutionally centrist. "
            "They respond to evidence, not ideology. Lead with the composite scoring "
            "methodology and the OECD data. Do not frame politically. "
            "Paul Johnson (Director) is the most influential economic commentator in UK media; "
            "IFS endorsement or citation multiplies reach enormously."
        ),
        "pitch": (
            "The UK Policy Optimiser Project has conducted a systematic comparative analysis "
            "of OECD economic data across ten peer economies, cross-referenced with eight "
            "major UK think tanks and the Henry Fudge Common Platform. We have developed a "
            "composite policy scoring model that weights GDP impact, poverty reduction, "
            "inequality reduction, political feasibility, and implementation complexity. "
            "\n\n"
            "Our methodology is directly complementary to IFS's work on tax-benefit "
            "microsimulation and fiscal policy analysis. We have found strong quantitative "
            "support for five policies where IFS research is already the gold standard: "
            "Land Value Tax (to replace SDLT), UC taper reduction, FE funding restoration, "
            "universal childcare, and fiscal devolution. "
            "\n\n"
            "We propose a research collaboration to independently validate our composite "
            "scoring model using IFS microsimulation data, and to co-author a policy brief "
            "on the three policies where cross-party, cross-think-tank consensus is strongest. "
            "We believe the combined IFS empirical rigour and our OECD comparative framework "
            "would produce the most robust evidence base available for the 2026 spending review."
        ),
    },
    {
        "name": "Resolution Foundation",
        "slug": "resolution_foundation",
        "lean": "centre-left",
        "url": "https://resolutionfoundation.org",
        "submission_process": (
            "Resolution Foundation accepts external research contributions and data. "
            "Contact via info@resolutionfoundation.org. "
            "They run a Research Fellows programme (details on site). "
            "Key moments: pre-Budget, living standards publication cycle (Feb/March annually). "
            "Torsten Bell is now an MP (Lab, Swansea West) but remains affiliated; "
            "contact current Director of Research."
        ),
        "partnership_contact": "info@resolutionfoundation.org | press@resolutionfoundation.org",
        "fellowship_url": "https://resolutionfoundation.org/about/jobs/",
        "policy_overlaps": [
            "UC taper reform (RF core work on in-work poverty)",
            "Two-child benefit limit removal (RF key campaigner)",
            "Universal childcare (RF female employment work)",
            "Housing affordability and supply (RF intergenerational inequality work)",
            "Low pay and minimum wage (RF Living Standards work)",
            "Social mobility (RF Intergenerational Commission)",
        ],
        "ideology_fit": (
            "RF is centre-left, evidence-driven, focused on living standards and "
            "intergenerational inequality. They respond to data on wages, poverty, "
            "and housing costs. Frame the project as building on RF's Living Standards "
            "Outlook and intergenerational work. The RF audience is media, parliamentarians, "
            "and policymakers — pitch the 90-day action plan as an implementable roadmap "
            "for the Labour government's current parliament."
        ),
        "pitch": (
            "The Resolution Foundation's Living Standards Outlook and Intergenerational "
            "Commission have provided the most robust UK evidence base on poverty, wages "
            "and housing inequality. The UK Policy Optimiser Project has built on this "
            "foundation to develop a systematic comparative framework — scoring twenty "
            "policy reforms against OECD data from ten peer economies on GDP, poverty, "
            "inequality, feasibility, and complexity. "
            "\n\n"
            "Our top five policies overlap substantially with RF's existing evidence: "
            "UC taper reform (to which RF has devoted five major publications), "
            "two-child limit removal, universal childcare, housing supply reform, and "
            "the fiscal cost of low-pay work. Where our work adds most value is the "
            "international comparison — showing exactly what Denmark, the Netherlands, "
            "and Singapore achieved with comparable reforms. "
            "\n\n"
            "We propose sharing our full OECD dataset and composite scoring model with "
            "RF's research team, and co-developing a policy brief for the 2026 Spending "
            "Review that combines RF's microsimulation capability with our international "
            "benchmarking. The goal: the most evidence-rich case ever made for the UC "
            "and childcare reforms that RF has championed."
        ),
    },
    {
        "name": "IPPR",
        "slug": "ippr",
        "lean": "centre-left",
        "url": "https://ippr.org",
        "submission_process": (
            "IPPR accepts external research proposals via research@ippr.org. "
            "They run a Fellowship and Research Associate programme. "
            "Key publications cycle: Economic Justice Commission reports (quarterly). "
            "IPPR North (Manchester) is a separate entity focused on regional inequality — "
            "contact via ippr@ippr.org. "
            "The IPPR Progressive Review journal accepts academic-format submissions."
        ),
        "partnership_contact": "research@ippr.org | press@ippr.org",
        "fellowship_url": "https://ippr.org/about/work-with-us/",
        "policy_overlaps": [
            "Planning reform and housing affordability (IPPR Will Planning Reform work)",
            "Transport infrastructure and regional growth (IPPR Transport and Growth)",
            "Energy market reform and green investment (IPPR energy leverage work)",
            "Public sector productivity (IPPR rethinking public sector work)",
            "Universal Credit reform (IPPR Economic Justice Commission)",
            "Flexicurity and labour market reform (IPPR Good Work agenda)",
        ],
        "ideology_fit": (
            "IPPR is centre-left, policy-activist in orientation, focused on economic justice "
            "and systemic reform. They respond to arguments about structural economic change "
            "and are particularly strong on regional inequality and the green economy. "
            "Frame the project around the 'foundational economy' and 'productive capitalism' "
            "language that IPPR's Economic Justice Commission uses. "
            "The ESEP / Single Market re-engagement argument is directly in their territory."
        ),
        "pitch": (
            "IPPR's Economic Justice Commission and its work on planning, transport, and "
            "the green economy have been central inputs to the UK Policy Optimiser Project. "
            "Our systematic analysis of twenty policy reforms across ten OECD peer economies "
            "has produced findings that align closely with IPPR's existing programme while "
            "adding an international quantitative dimension that strengthens the case for "
            "structural reform. "
            "\n\n"
            "Three areas of particular alignment: first, our housing analysis — showing "
            "that zoning-based planning reform (German B-Plan) combined with Land Value Tax "
            "and government-led construction could move the UK from its current 10x "
            "price-to-income ratio toward Singapore's 5x — builds directly on IPPR's "
            "planning reform work. Second, our EU Single Market re-engagement framework "
            "(ESEP) provides the economic case for a policy IPPR has long supported. "
            "Third, our flexicurity analysis for the UK labour market complements IPPR's "
            "Good Work agenda. "
            "\n\n"
            "We propose a joint publication: an IPPR policy brief co-authored with our "
            "research team presenting the international evidence for a combined housing, "
            "welfare, and labour market reform package — timed for the Spending Review."
        ),
    },
    {
        "name": "Centre for Cities",
        "slug": "centre_for_cities",
        "lean": "centrist",
        "url": "https://centreforcities.org",
        "submission_process": (
            "Centre for Cities accepts external research proposals and data partnerships. "
            "Contact via info@centreforcities.org. "
            "Key publication moments: Cities Outlook (annual, January). "
            "They run a Cities Forum and events programme — good for presenting findings "
            "to local government and business audiences. "
            "CfC is particularly responsive to data on regional economic inequality."
        ),
        "partnership_contact": "info@centreforcities.org | press@centreforcities.org",
        "fellowship_url": "https://centreforcities.org/about/",
        "policy_overlaps": [
            "Regional economic inequality (London vs rest of UK GVA data)",
            "Fiscal devolution and city region tax powers",
            "Planning reform and housing supply in cities",
            "Transport infrastructure and city productivity",
            "Business rates reform and local business investment",
        ],
        "ideology_fit": (
            "CfC is centrist, evidence-driven, city-focused. They respond to data on "
            "urban productivity, planning, and fiscal devolution. The ONS regional GVA data "
            "showing London at 179% of UK average vs North East at 74% is their terrain. "
            "Frame the project around the finding that if English cities outside London "
            "matched comparable European cities, UK GDP would be £47bn/year higher. "
            "This is CfC's own research finding — we are amplifying it."
        ),
        "pitch": (
            "The UK Policy Optimiser Project has incorporated Centre for Cities' finding "
            "that matching the productivity of England's ten largest cities outside London "
            "to comparable European peers would add £47bn per year to UK GDP. Our analysis "
            "extends this by identifying the specific policy levers — planning reform, "
            "fiscal devolution, transport investment, and skills infrastructure — that "
            "comparable European cities have used to close their productivity gaps. "
            "\n\n"
            "Our policy composite scoring places fiscal devolution (city region revenue "
            "retention to 15% of total tax receipts, from the current 5%) and planning "
            "reform as medium-term structural reforms with strong evidence bases. "
            "The German Länder model and Danish municipal tax retention provide the "
            "international template; our OECD data gives this quantitative weight. "
            "\n\n"
            "We propose a joint data analysis with CfC's Cities Outlook team: using our "
            "OECD international dataset alongside CfC's city-level UK data to produce "
            "a report on 'What European Cities Do Differently' — and what it would take "
            "for Birmingham, Manchester, and Leeds to match Barcelona, Amsterdam, and Lyon."
        ),
    },
    {
        "name": "Tony Blair Institute",
        "slug": "tony_blair_institute",
        "lean": "centrist",
        "url": "https://institute.global",
        "submission_process": (
            "TBI accepts research partnerships and external analysis via "
            "contact@institute.global. "
            "They run a Future Leaders programme and accept external research fellows. "
            "Key areas: technology and government, public services reform, economic strategy. "
            "TBI has direct access to current Labour government — high-value target for "
            "placing recommendations with decision-makers."
        ),
        "partnership_contact": "contact@institute.global | press@institute.global",
        "fellowship_url": "https://institute.global/about/careers",
        "policy_overlaps": [
            "NHS reform and digital government (TBI healthcare innovation work)",
            "Skills and FE reform (TBI future of work research)",
            "Industrial strategy and green economy (TBI economic prosperity work)",
            "Welfare reform and employment (TBI lifespan fund / UC emergency work)",
            "State capacity and public sector productivity (TBI core mission)",
        ],
        "ideology_fit": (
            "TBI is centrist, modernising, strongly focused on technology and state capacity. "
            "They respond to arguments about government effectiveness, digital transformation, "
            "and pragmatic reform. Frame the project around state capacity: "
            "Singapore's WGI government effectiveness score of 2.28 vs UK's 1.39. "
            "The argument that institutional quality is as important as policy design "
            "is central to TBI's mission. "
            "TBI has direct access to Labour ministers — the highest-value advocacy target."
        ),
        "pitch": (
            "The UK Policy Optimiser Project's analysis of ten OECD peer economies has "
            "produced a finding that is central to TBI's mission: the UK's policy failures "
            "are not primarily a problem of bad policy design, but of weak state capacity "
            "to implement good policy. Singapore's World Bank government effectiveness "
            "score of 2.28 versus the UK's 1.39 reflects sixty years of investment in "
            "civil service capability, digital government, and long-term planning. "
            "\n\n"
            "Our five highest-scoring policies — childcare, UC reform, LVT, housing "
            "construction, and EU market re-engagement — all require strong institutional "
            "delivery. The Valuation Office Agency needs AI-assisted land valuation. "
            "The UC system needs a rebuilt IT platform. The housing programme needs a "
            "public development corporation with genuine delivery capacity. "
            "\n\n"
            "We propose a joint policy brief with TBI on 'Building the State Capacity "
            "to Deliver Economic Reform' — combining our policy evidence base with TBI's "
            "expertise in technology and government. This positions both organisations "
            "optimally for the Labour government's current focus on 'missions' delivery."
        ),
    },
    {
        "name": "Adam Smith Institute",
        "slug": "adam_smith_institute",
        "lean": "right",
        "url": "https://adamsmith.org",
        "submission_process": (
            "ASI accepts external policy papers via submissions@adamsmith.org. "
            "They run a Young Writer on Liberty programme and host external events. "
            "ASI is particularly responsive to supply-side reform arguments: "
            "planning deregulation, tax simplification, LVT, competition policy. "
            "Key publication: Eamonn Butler (Director) and Tom Clougherty (research) "
            "are the main contacts for research collaboration."
        ),
        "partnership_contact": "enquiries@adamsmith.org | submissions@adamsmith.org",
        "fellowship_url": "https://adamsmith.org/young-writer-on-liberty/",
        "policy_overlaps": [
            "Land Value Tax to replace Stamp Duty (ASI has explicitly backed LVT)",
            "Planning reform — by-right zoning (ASI Growth Agenda)",
            "Apprenticeship Levy reform (ASI education work)",
            "Business rates reform (ASI local taxation work)",
            "Reducing marginal effective tax rates on low income (UC taper critique)",
            "Electricity market reform and energy price competition",
        ],
        "ideology_fit": (
            "ASI is right-of-centre, libertarian-leaning, pro-market, pro-deregulation. "
            "They respond to supply-side arguments: removing barriers to building, "
            "cutting distortionary taxes, reducing regulatory burden. "
            "The key framing for ASI: LVT is a Georgist/libertarian reform that "
            "reduces the tax burden on productive investment while taxing economic rent. "
            "Planning reform as 'freeing the market' not 'state planning'. "
            "Electricity market decoupling as pro-competition reform. "
            "Avoid framing anything as 'public spending' — frame as 'investment' and "
            "'removing market failures'."
        ),
        "pitch": (
            "The UK Policy Optimiser Project has produced a ranked analysis of twenty "
            "economic reforms that will interest the Adam Smith Institute precisely because "
            "several of our highest-scoring policies are classically Georgist and supply-side. "
            "\n\n"
            "Land Value Tax — replacing Stamp Duty Land Tax with an annual levy on "
            "unimproved land values of investment properties — scores 7.05/10 in our "
            "composite model. As ASI has argued, SDLT is one of the most economically "
            "damaging taxes in the UK system, reducing housing market liquidity, "
            "discouraging labour mobility, and rewarding land banking over productive use. "
            "Estonia's experience demonstrates the growth benefits of shifting taxation "
            "from buildings to land. "
            "\n\n"
            "Similarly, our zoning-based planning reform (German B-Plan, Tokyo model) "
            "aligns directly with ASI's Growth Agenda on planning deregulation. "
            "The UC taper rate critique — a marginal effective tax rate of up to 75% on "
            "low-paid workers — is a supply-side argument ASI has made repeatedly. "
            "\n\n"
            "We propose co-publishing a policy brief on the three supply-side reforms "
            "with broadest cross-ideological support: LVT, planning deregulation, and "
            "electricity market reform. An ASI-endorsed supply-side reform paper with "
            "OECD evidence would reach a different audience than our other partnerships."
        ),
    },
    {
        "name": "Fabian Society",
        "slug": "fabian_society",
        "lean": "left",
        "url": "https://fabians.org.uk",
        "submission_process": (
            "Fabian Society accepts pamphlet submissions via editorial@fabians.org.uk. "
            "They publish Fabian Review (quarterly magazine) and research pamphlets. "
            "External authors are welcome for pamphlets — this is a key publication route "
            "for placing policy arguments with the Labour movement. "
            "The Fabian Society has direct links to Labour MPs and trade unions."
        ),
        "partnership_contact": "info@fabians.org.uk | editorial@fabians.org.uk",
        "fellowship_url": "https://fabians.org.uk/about/internships/",
        "policy_overlaps": [
            "UC reform and poverty reduction (Fabian welfare work)",
            "FE college funding and skills (Fabian Building Skills report)",
            "Apprenticeship Levy reform (Fabian Levying Up report)",
            "NHS funding and social care (Fabian public services work)",
            "Wealth taxation and inequality (Fabian Taxing Questions)",
            "Social housing supply and right-to-buy reform",
        ],
        "ideology_fit": (
            "The Fabians are left-of-centre, Labour-movement-aligned, focused on "
            "social democratic reform through the existing state. They respond to "
            "arguments about public investment, inequality reduction, and workers' rights. "
            "Frame the project around the human cost of policy failure: "
            "29% child poverty, rising in-work poverty, the FE funding collapse. "
            "The Fabian audience is Labour activists, trade unionists, and left-leaning "
            "academics — a key audience for building the political coalition for reform."
        ),
        "pitch": (
            "The UK Policy Optimiser Project has systematically compared the UK's "
            "economic performance against its peer economies — and the findings are "
            "damning. Child poverty at 29% (Denmark: 6.6%). Social mobility ranked "
            "seventh of nine comparable OECD economies. FE colleges defunded by 35% "
            "in real terms per student since 2010. These are not abstract statistics "
            "— they represent a generation of preventable disadvantage. "
            "\n\n"
            "Our analysis identifies a cluster of high-impact, short-timeline reforms "
            "that could be implemented within this parliament and that align directly "
            "with the Fabian Society's existing work: UC taper reform (composite score "
            "7.15/10), two-child limit removal (6.75/10), Youth Guarantee (6.65/10), "
            "and FE college funding restoration (6.55/10). All four have cross-party "
            "evidence support and could be delivered within two years. "
            "\n\n"
            "We propose a Fabian pamphlet: 'What Would Actually End Child Poverty? "
            "An Evidence-Based Programme for This Parliament'. We would bring the OECD "
            "comparative data; the Fabian Society would bring the political economy "
            "analysis and Labour movement context. Target audience: Labour MPs, "
            "trade union policy teams, and local government."
        ),
    },
    {
        "name": "Policy Exchange",
        "slug": "policy_exchange",
        "lean": "centre-right",
        "url": "https://policyexchange.org.uk",
        "submission_process": (
            "Policy Exchange accepts external research contributions via "
            "info@policyexchange.org.uk. "
            "They publish research papers (typically 40–80 pages) and shorter briefing notes. "
            "Key research areas: housing, planning, education, economic policy, defence. "
            "Policy Exchange has strong links to Conservative Party and has influenced "
            "Conservative housing and planning policy significantly."
        ),
        "partnership_contact": "info@policyexchange.org.uk | press@policyexchange.org.uk",
        "fellowship_url": "https://policyexchange.org.uk/about/",
        "policy_overlaps": [
            "Planning reform and housing supply (Policy Exchange Homes for Growth)",
            "Broken housing market (PX Broken Housing Market report)",
            "FE and vocational education reform",
            "Business rates and local economic policy",
            "Social housing and right-to-buy reform",
        ],
        "ideology_fit": (
            "Policy Exchange is centre-right, pro-market, strong on planning reform "
            "and housing supply. They respond to arguments about economic efficiency, "
            "deregulation, and supply-side growth. "
            "Frame the project around supply-side economics: planning deregulation, "
            "LVT as a market-distortion-reducing reform, and housing as a supply problem "
            "rather than a demand problem. "
            "The 'Homes for Growth' framing resonates strongly with PX's work. "
            "The demographic argument (young people priced out, labour market immobility) "
            "is also compelling for a centre-right audience."
        ),
        "pitch": (
            "Policy Exchange's Homes for Growth and Broken Housing Market reports have "
            "been central inputs to the UK Policy Optimiser Project's housing analysis. "
            "Our systematic comparison of UK housing outcomes against OECD peers confirms "
            "the core Policy Exchange diagnosis: the UK's housing crisis is fundamentally "
            "a supply problem driven by a dysfunctional planning system. "
            "\n\n"
            "Our analysis goes further by quantifying the economic cost: a median "
            "house-price-to-income ratio of 10x versus Germany's 7x costs the UK "
            "economy an estimated 0.8% of GDP annually through labour immobility "
            "alone. The zoning-based reform we propose (German B-Plan model, Tokyo "
            "by-right development) is exactly the supply-side deregulation that Policy "
            "Exchange has advocated, now backed by comprehensive international data. "
            "\n\n"
            "We propose a joint research paper: 'Planning for Growth — What Germany, "
            "Japan and Singapore Did That Britain Hasn't'. We bring the OECD international "
            "comparative data; Policy Exchange brings the political and planning policy "
            "analysis. This would be the most data-rich case ever made for planning "
            "deregulation — and would reach both Conservative and Labour housing audiences."
        ),
    },
]


# ── Load existing think tank data from Phase 5 ────────────────────────────────

def load_phase5_data() -> dict:
    combined_path = DATA_DIR / "combined.json"
    if not combined_path.exists():
        log.warning("Phase 5 combined.json not found at %s", combined_path)
        return {}
    try:
        data = json.loads(combined_path.read_text(encoding="utf-8"))
        return {tt["name"]: tt for tt in data.get("think_tanks", [])}
    except Exception as exc:
        log.warning("Could not load Phase 5 data: %s", exc)
        return {}


# ── Output generators ──────────────────────────────────────────────────────────

def generate_think_tank_section(phase5_data: dict) -> str:
    lines = [
        "## Think Tank Routes",
        "",
        f"*Generated: {datetime.now(timezone.utc).strftime('%d %B %Y')}*",
        "",
        "---",
        "",
    ]

    for tt in THINK_TANK_PROFILES:
        name = tt["name"]
        phase5 = phase5_data.get(name, {})
        recent_reports = phase5.get("recent_reports", [])

        lines += [
            f"### {name}",
            f"**Ideological lean:** {tt['lean']}  ",
            f"**URL:** {tt['url']}  ",
            f"**Contact:** {tt['partnership_contact']}  ",
            f"**Fellowship/submission:** {tt['fellowship_url']}",
            "",
            "#### Submission / Partnership Process",
            "",
            tt["submission_process"],
            "",
            "#### Policy Overlaps with Our Programme",
            "",
        ]
        for overlap in tt["policy_overlaps"]:
            lines.append(f"- {overlap}")

        if recent_reports:
            lines += [
                "",
                "#### Recent Relevant Reports (from Phase 5 scrape)",
                "",
            ]
            for r in recent_reports[:4]:
                title = r.get("title", "")
                date = r.get("date", "")
                url = r.get("url", "")
                date_str = f" ({date})" if date else ""
                url_str = f" — [{url}]({url})" if url else ""
                lines.append(f"- *{title}*{date_str}{url_str}")

        lines += [
            "",
            "#### Ideological Framing Guidance",
            "",
            tt["ideology_fit"],
            "",
            "#### Research Collaboration Pitch (200 words)",
            "",
        ]
        # Format pitch as a blockquote
        for para in tt["pitch"].strip().split("\n\n"):
            if para.strip():
                lines.append(f"> {para.strip()}")
                lines.append(">")
        lines += [
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


def main() -> dict:
    log.info("=" * 60)
    log.info("THINK TANK ROUTES")
    log.info("=" * 60)

    phase5_data = load_phase5_data()
    log.info("Phase 5 data loaded for %d think tanks", len(phase5_data))

    think_tank_section = generate_think_tank_section(phase5_data)

    print()
    print("=" * 60)
    print("THINK TANK ROUTES SUMMARY")
    print("=" * 60)
    print(f"  Think tanks profiled   : {len(THINK_TANK_PROFILES)}")
    for tt in THINK_TANK_PROFILES:
        n_reports = len(phase5_data.get(tt["name"], {}).get("recent_reports", []))
        print(f"  {tt['name']:<40} [{tt['lean']}]  Phase5: {n_reports} reports")
    print()

    return {
        "think_tanks": THINK_TANK_PROFILES,
        "think_tank_section_md": think_tank_section,
    }


if __name__ == "__main__":
    main()

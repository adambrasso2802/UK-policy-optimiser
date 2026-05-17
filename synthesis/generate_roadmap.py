"""
Generate a tight 2-page MP/journalist briefing note.
Output: outputs/briefing_note.md
"""

from pathlib import Path

BASE = Path(__file__).parent.parent
OUTPUT = BASE / "outputs" / "briefing_note.md"

BRIEFING = """\
# UK Economic Reform — Briefing Note

*UK Policy Optimiser Project | May 2026 | For internal circulation*

---

## HEADLINE

The UK is growing at less than a third of the OECD peer average — a sequenced \
five-reform programme can double the growth rate, lift two million people out of \
poverty, and reduce public debt as a share of GDP, all within a decade.

---

## THE PROBLEM

- **Growth gap**: UK GDP averaged 0.68%/yr (2019–2024) vs OECD peer average \
2.1%/yr — a shortfall costing every household roughly £2,500/yr in foregone \
real income.
- **Productivity gap**: UK labour productivity $55.3/hr vs Netherlands $75.4/hr \
(+36%) and Germany $67.3/hr — each percentage point of that gap is ~£10bn of \
foregone annual output and ~£3,000/worker/yr in lost wages.
- **Social gap**: Relative poverty 11.7% (Denmark 6.6%; Netherlands 7.5%); \
child poverty 29% after housing costs; social mobility IGE 0.43 vs Denmark 0.15 \
— birth is the strongest predictor of adult income in the UK among nine OECD peers.

---

## THE OPPORTUNITY

- **Growth**: Full programme projects GDP growth rising to 2.3–2.5%/yr by 2035 \
— adding ~£200bn/yr in output vs the OBR baseline of 1.2%/yr.
- **Poverty**: Relative poverty rate falls from 11.7% to ~8.5% by 2035 — \
approximately 2 million fewer people below the poverty line; child poverty \
falls below 20% for the first time since 2010.
- **Fiscal**: Public debt falls from 99.0% to 86.5% of GDP by 2035 despite \
higher investment, because growth raises the denominator faster than spending \
raises the numerator; Land Value Tax alone raises £28bn/yr by Year 5.

---

## THE PROGRAMME

1. **Universal Childcare** (9 months+, workforce paid £25k min) — \
[+1.5–2.5% GDP; +3–5pp female employment; £7bn/yr net cost]
2. **Universal Credit Reform** (taper 55%→45%, abolish 5-week wait, raise \
work allowances) — [lifts 2 million households; fastest poverty reduction \
available; £4.5bn/yr]
3. **Land Value Tax** (2%/yr on investment & second properties, replaces \
Stamp Duty over 5 years) — [£28bn/yr revenue by Y5; +1.0% GDP; cross-party \
evidence base: IFS, ASI, Resolution Foundation, IPPR]
4. **Government-Led Housing Construction** (300,000 homes/yr by Y5 incl. \
90,000 social rent) — [+0.8% GDP; house-price-to-income ratio from 10x \
toward 6–7x; £20bn/yr net capital cost]
5. **European Security & Economic Partnership** (Single Market re-entry via \
Franco-British nuclear deterrence framework) — [+2.0% GDP by Y10; NIESR \
estimates Brexit cost 4–5% of GDP vs counterfactual]

---

## THE EVIDENCE

| Country | Policy | Outcome |
|---------|--------|---------|
| **Denmark** | Universal childcare + flexicurity + land-value-adjacent \
taxation | Poverty 6.6% (UK: 11.7%), IGE 0.15 (UK: 0.43), GDP growth \
1.9%/yr, public debt 30% of GDP |
| **Singapore** | State Housing Development Board: direct public \
construction at scale, land state-owned on 99-yr leases | 90% homeownership; \
house-price-to-income ratio 5x vs UK's 10x; no speculation cycle |
| **Ireland** | Post-GFC structural reform: front-loaded consolidation + \
FDI strategy + government-led housing targets | Bond yields normalised 2015; \
GDP growth 6.28%/yr (5-yr avg); fiscal surplus by Year 5 of programme |

---

## THE ASK

**Support a Treasury Select Committee inquiry into Land Value Tax**: \
commission the OBR to publish an independent score of the £28bn revenue \
projection and quantify the economic distortion caused by Stamp Duty. \
This single step would unlock the cross-party consensus already visible \
in IFS, Resolution Foundation, Adam Smith Institute and IPPR publications — \
and give any government political cover to act.

---

## CONTACT / FURTHER READING

Full 20-policy paper with OECD evidence base, scenario modelling and \
fiscal projections: **outputs/policy_paper.md**

*UK Policy Optimiser Project — drawing on ONS, OECD, DWP, World Bank, \
IFS, Resolution Foundation, IPPR, Centre for Cities, Tony Blair Institute, \
Adam Smith Institute, Policy Exchange, Fabian Society, and the Henry Fudge \
Common Platform. Not affiliated with any political party.*
"""


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(BRIEFING, encoding="utf-8")

    word_count = len(BRIEFING.split())
    print(f"Briefing note saved to: {OUTPUT}")
    print(f"Word count: {word_count}")

    if word_count > 700:
        print(f"WARNING: {word_count} words exceeds 700-word target.")
    else:
        print(f"OK: {word_count} words — within 700-word limit.")


if __name__ == "__main__":
    main()

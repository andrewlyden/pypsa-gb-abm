"""How far the optimum, and so the gap, moves with the planner's own assumptions (foundations review,
docs/review_2026-11_foundations.md, section 2; README roadmap item 40).

One baseline agent run, then the planner re-solved under each variant; both fleets are costed by the
evaluator under the same variant. Only the investment gap changes (the agents' fleet is fixed).

    python scripts/run_planner_sensitivity.py                      # all variants, ~90 min
    python scripts/run_planner_sensitivity.py default voll_16950   # some variants

Writes results/planner_sensitivity.json and results/planner_sensitivity.md.
"""
import argparse
import json
import subprocess
import time
import warnings
from pathlib import Path

from ukabm import GBMarketModel, get_scenario
from ukabm.config import PLANNER_BUILD_MW_PER_YEAR as LIMITS, TECHS, capex_kw
from ukabm.costs import COMPONENTS, crf, present_value, total
from ukabm.planner import evaluate, plan

ROOT = Path(__file__).resolve().parents[1]
# ASSUMPTION: Green Book central carbon values, GBP 260 (2025) -> 378 (2050) per tCO2e in 2020 prices
# (BEIS 2021), moved to 2024 prices with an approximate factor of 1.19. Replace with the published deflator.
CARBON_APPRAISAL = (310.0, 450.0)
VARIANTS = {
    "default": dict(label="Default"),
    "limits_x0.5": dict(label="Build limits x 0.5", limits={k: 0.5 * v for k, v in LIMITS.items()}),
    "limits_x2": dict(label="Build limits x 2", limits={k: 2 * v for k, v in LIMITS.items()}),
    "onshore_unlimited": dict(label="Onshore limit lifted (20 GW a year)", limits={**LIMITS, "wind_onshore": 20000}),
    "vre_at_cfd_volumes": dict(label="Wind and solar limited to the CfD volumes (3.6 / 1.2 / 1.2 GW a year)",
                               limits={**LIMITS, "wind_offshore": 3600, "wind_onshore": 1200, "solar": 1200}),
    "voll_16950": dict(label="VoLL GBP 16,950/MWh", voll=16950.0),
    "carbon_appraisal": dict(label="Carbon at appraisal values (GBP 310 -> 450/t)", carbon=CARBON_APPRAISAL),
    "capital_at_7pct": dict(label="Capital at 7 % (planner and annuities; present values at 3.5 %)", rate=0.07),
}


def git_hash():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def fleet_gw(units, year):
    by = {}
    for u in units:
        if u.active(year):
            by[u.tech] = by.get(u.tech, 0.0) + u.mw / 1e3
    return {k: round(v, 1) for k, v in sorted(by.items())}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("variants", nargs="*", default=list(VARIANTS), help=f"any of {list(VARIANTS)}")
    ap.add_argument("--scenario", default="baseline")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--end", type=int, default=2050)
    a = ap.parse_args()
    warnings.simplefilter("ignore")
    t0 = time.time()
    m = GBMarketModel(get_scenario(a.scenario), seed=a.seed, start=2025, end=a.end, network_every=0)
    m.run()
    years = list(range(2025, a.end + 1, 5))
    loads = {y: m.hourly[y]["load"].values for y in years}
    agents = list(m.plants)
    base = (m.policy.voll, m.policy.carbon_price_2025, m.policy.carbon_price_2050)

    def cost_path(units, capital_rate):
        """PV (GBP bn) of the evaluator's cost of *units*; capex annuitised at capital_rate if given."""
        annual, detail = {}, {}
        for y in years:
            ev = evaluate(m, y, units, loads[y])
            c = dict(ev["costs"])
            if capital_rate is not None:
                c["capex"] = sum(capex_kw(u.tech, u.online) * 1000 * u.mw * crf(capital_rate, TECHS[u.tech].life)
                                 for u in units if m.start < u.online <= y <= u.online + TECHS[u.tech].life - 1)
            annual[y] = total(c)
            detail[y] = dict(unserved_gwh=round(ev["unserved_mwh"] / 1e3, 1), emissions_mt=round(ev["emissions_t"] / 1e6, 2),
                             **{k: round(c[k] / 1e9, 3) for k in COMPONENTS})
        return present_value(annual, base=2025, step=5) / 1e9, detail

    out = dict(provenance=dict(git=git_hash(), scenario=a.scenario, seed=a.seed, end=a.end),
               agents_last=fleet_gw(agents, years[-1]), variants={})
    for name in a.variants:
        v = VARIANTS[name]
        m.policy.voll = v.get("voll", base[0])
        m.policy.carbon_price_2025, m.policy.carbon_price_2050 = v.get("carbon", base[1:])
        rate = v.get("rate")
        p = plan(m, loads, build_limits=v.get("limits"), **({"rate": rate} if rate else {}))
        fleet = list(m.initial_fleet) + p.units
        pv_p, d_p = cost_path(fleet, rate)
        pv_a, d_a = cost_path(agents, rate)
        out["variants"][name] = dict(label=v["label"], pv_planner_bn=round(pv_p, 2), pv_agents_bn=round(pv_a, 2),
                                     gap_bn=round(pv_a - pv_p, 2), gap_pct=round(100 * (pv_a - pv_p) / pv_p, 2),
                                     planner_last=fleet_gw(fleet, years[-1]), planner=d_p, agents=d_a)
        print(f"{name}: optimum {pv_p:.1f}, agents' fleet {pv_a:.1f}, gap {pv_a - pv_p:.1f} bn "
              f"({100 * (pv_a - pv_p) / pv_p:.1f} %)  [{time.time() - t0:.0f} s]", flush=True)
    m.policy.voll, m.policy.carbon_price_2025, m.policy.carbon_price_2050 = base
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "planner_sensitivity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    (ROOT / "results" / "planner_sensitivity.md").write_text(markdown(out), encoding="utf-8")


def markdown(out):
    pr = out["provenance"]
    g = lambda d, k: d.get(k, 0.0)
    end = pr["end"] // 5 * 5
    lines = ["# Planner sensitivity: the investment gap under other values of the planner's assumptions", "",
             f"Scenario `{pr['scenario']}`, seed {pr['seed']}, 2025-{pr['end']}; code at `{pr['git']}`; "
             "`scripts/run_planner_sensitivity.py`. One agent run; the planner is re-solved under each variant "
             f"and both fleets are costed by the evaluator under the same variant. Present values 2025-{end + 4} at "
             "3.5 %, GBP bn. See [the foundations review](../docs/review_2026-11_foundations.md), section 2.", "",
             f"| variant | optimum | agents' fleet | investment gap | gap % | planner {end}, GW: offshore / onshore / solar / "
             f"battery / OCGT / CCGT / gas CCS | planner unserved {end} (GWh) | emissions {end}, planner / agents (Mt) |",
             "|---|---|---|---|---|---|---|---|"]
    for v in out["variants"].values():
        f, last = v["planner_last"], max(v["planner"], key=int)
        mix = " / ".join(f"{g(f, k):.1f}" for k in ("wind_offshore", "wind_onshore", "solar", "battery", "ocgt", "ccgt", "gas_ccs"))
        lines.append(f"| {v['label']} | {v['pv_planner_bn']:.1f} | {v['pv_agents_bn']:.1f} | {v['gap_bn']:.1f} | "
                     f"{v['gap_pct']:.1f} | {mix} | {v['planner'][last]['unserved_gwh']:.0f} | "
                     f"{v['planner'][last]['emissions_mt']:.1f} / {v['agents'][last]['emissions_mt']:.1f} |")
    a = out["agents_last"]
    if pr.get("note"):
        lines[4:4] = ["Note: " + pr["note"] + ".", ""]
    lines += ["", f"Agents' fleet in {end} (GW): " + ", ".join(f"{k} {v}" for k, v in a.items()) + ".", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()

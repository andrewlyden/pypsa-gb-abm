"""Make figures from results/ into docs/figures/."""
import pickle
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "docs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
_savefig = plt.Figure.savefig


def _save_both(self, fname, *a, **k):  # PNG for README, SVG (text) for GitHub API publishing
    _savefig(self, fname, *a, **k)
    k.pop("dpi", None)
    _savefig(self, str(fname).replace(".png", ".svg"), *a, **k)


plt.Figure.savefig = _save_both
COL = {"nuclear": "#8e44ad", "ccgt": "#7f8c8d", "ocgt": "#c0392b", "gas_ccs": "#34495e", "h2_turbine": "#16a085",
       "biomass": "#6e4b2a", "wind_onshore": "#5dade2", "wind_offshore": "#1f618d", "solar": "#f4d03f",
       "hydro": "#48c9b0", "battery": "#e67e22", "pumped_hydro": "#a3e4d7", "imports": "#bdc3c7",
       "interconnector": "#bdc3c7"}
runs = {p.stem.replace("annual_", ""): pd.read_csv(p, index_col=0) for p in sorted(RES.glob("annual_*.csv"))}
base = runs.get("baseline", next(iter(runs.values())))


def stack(df, prefix, title, ylabel, fname):
    cols = [c for c in df.columns if c.startswith(prefix) and c != "gen_total" and df[c].abs().sum() > 0]
    names = [c[len(prefix):] for c in cols]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.stackplot(df.index, df[cols].T.values, labels=names, colors=[COL.get(n, None) for n in names])
    ax.set_title(title); ax.set_ylabel(ylabel); ax.set_xlim(df.index.min(), df.index.max())
    ax.legend(loc="upper left", fontsize=7, ncol=2, bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout(); fig.savefig(FIG / fname, dpi=130); plt.close(fig)


stack(base, "cap_", "Baseline: installed capacity (GW)", "GW", "capacity_mix.png")
stack(base, "gen_", "Baseline: annual generation (TWh)", "TWh", "generation_mix.png")

fig, axs = plt.subplots(2, 2, figsize=(11, 7))
for name, df in runs.items():
    axs[0, 0].plot(df.index, df.price_twa, label=name)
    axs[0, 1].plot(df.index, df.intensity_g_kwh, label=name)
    axs[1, 0].plot(df.index, df.cfd_cost_bn + df.cm_cost_bn + df.ro_cost_bn, label=name)
    axs[1, 1].plot(df.index, df.hp_homes_m, label=name)
for ax, t in zip(axs.flat, ["Demand-weighted wholesale price (GBP/MWh)", "Carbon intensity (gCO2/kWh)",
                            "Policy cost CfD+RO+CM (GBP bn/yr)", "Homes with heat pumps (million)"]):
    ax.set_title(t, fontsize=10); ax.grid(alpha=.3)
axs[0, 0].legend(fontsize=7)
axs[0, 0].set_ylim(0, 200)
clipped = {n: d.price_twa.max() for n, d in runs.items() if d.price_twa.max() > 200}
if clipped:
    axs[0, 0].text(0.02, 0.92, "; ".join(f"{n} peaks at GBP{v:,.0f}/MWh (clipped)" for n, v in clipped.items()),
                   transform=axs[0, 0].transAxes, fontsize=7)
axs[1, 0].set_ylim(-5, 25)
fig.tight_layout(); fig.savefig(FIG / "scenario_comparison.png", dpi=130); plt.close(fig)

fig, axs = plt.subplots(1, 3, figsize=(13, 3.8))
axs[0].stackplot(base.index, base.demand_twh - base.heat_twh - base.ev_twh - base.h2_twh - base.export_twh,
                 base.heat_twh, base.ev_twh, base.h2_twh, base.export_twh,
                 labels=["base", "heat pumps", "EVs", "electrolysers", "exports"])
axs[0].set_title("Electricity demand components (TWh)", fontsize=10); axs[0].legend(fontsize=7, loc="upper left")
axs[1].plot(base.index, base.hp_homes_m, label="HP homes (m)"); axs[1].plot(base.index, base.ev_stock_m, label="EVs (m)")
axs[1].set_title("Adoption", fontsize=10); axs[1].legend(fontsize=7)
axs[2].plot(base.index, base.gas_network_tariff, label="gas network tariff"); axs[2].plot(base.index, base.gas_retail, label="gas retail")
axs[2].plot(base.index, base.elec_retail / 3, "--", label="elec retail / 3")
axs[2].set_title("Retail prices (GBP/MWh)", fontsize=10); axs[2].legend(fontsize=7)
fig.tight_layout(); fig.savefig(FIG / "multienergy.png", dpi=130); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4))
for c, l in [("cfd_cost_bn", "CfD"), ("ro_cost_bn", "RO"), ("cm_cost_bn", "Capacity Market")]:
    ax.plot(base.index, base[c], label=l)
nc = base.constraint_cost_bn.dropna()
ax.plot(nc.index, nc.values, "ko--", label="network constraint cost (BM redispatch, PyPSA-GB zones)")
ax.set_title("Baseline policy and network costs (GBP bn/yr)"); ax.legend(fontsize=8); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "policy_costs.png", dpi=130); plt.close(fig)

det_p = RES / "detail_baseline.pkl"
if det_p.exists():
    det = pickle.load(open(det_p, "rb"))
    years = sorted(det["hourly"])
    fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for y in years[::2] + [years[-1]]:
        h = det["hourly"][y].iloc[24 * 14:24 * 21]
        axs[0].plot(range(len(h)), h.price.values, label=str(y))
        axs[1].plot(range(len(h)), h.demand.values / 1e3, label=str(y))
    axs[0].set_title("Winter week (mid-January): price GBP/MWh"); axs[1].set_title("Net demand incl. flex (GW)")
    axs[0].legend(fontsize=7); axs[1].set_xlabel("hour")
    fig.tight_layout(); fig.savefig(FIG / "winter_week.png", dpi=130); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 5))
    pdc = {y: det["hourly"][y].price.sort_values(ascending=False).values for y in years}
    for y, v in pdc.items():
        ax.plot(v, label=str(y))
    ax.set_yscale("symlog"); ax.set_title("Price duration curves"); ax.legend(fontsize=7); ax.set_xlabel("hours")
    fig.tight_layout(); fig.savefig(FIG / "price_duration.png", dpi=130); plt.close(fig)
    net = det.get("network") or {}
    if "zonal_price" in net:
        b = det["buses"].set_index("name")
        zp = net["zonal_price"].reindex(b.index)
        fig, ax = plt.subplots(figsize=(5, 7))
        fl = net["flows"].abs().mean()
        for _, l in det["links"].iterrows():
            ax.plot([b.x[l.bus0], b.x[l.bus1]], [b.y[l.bus0], b.y[l.bus1]], "k-",
                    lw=0.5 + 3 * fl.get(l["name"], 0) / max(fl.max(), 1), alpha=.6)
        sc = ax.scatter(b.x, b.y, c=zp, cmap="viridis", s=90, zorder=3)
        plt.colorbar(sc, label="zonal price GBP/MWh (weighted median of sample hours)")
        ax.set_title(f"PyPSA-GB zonal redispatch, {net.get('year')}\n(line width = mean flow)")
        fig.tight_layout(); fig.savefig(FIG / "zonal_network.png", dpi=130); plt.close(fig)

ens = {p.stem.replace("ensemble_", ""): pd.read_csv(p, index_col=0) for p in sorted(RES.glob("ensemble_*.csv"))}
if ens:  # multi-seed bands: median line, shaded min-max across seeds
    from ukabm import bands
    for df in ens.values():
        df["policy_cost_bn"] = df.cfd_cost_bn + df.cm_cost_bn + df.ro_cost_bn
        df["lole_cum_h"] = df.groupby("seed").lole_h.cumsum()
    panels = [("price_twa", "Demand-weighted wholesale price (GBP/MWh)"), ("intensity_g_kwh", "Carbon intensity (gCO2/kWh)"),
              ("policy_cost_bn", "Policy cost CfD+RO+CM (GBP bn/yr)"), ("hp_homes_m", "Homes with heat pumps (million)"),
              ("cap_wind_offshore", "Offshore wind capacity (GW)"), ("lole_cum_h", "Cumulative loss-of-load hours")]
    fig, axs = plt.subplots(2, 3, figsize=(14, 7))
    for k, (name, df) in enumerate(ens.items()):
        b = bands(df, [c for c, _ in panels])
        n = df.seed.nunique()
        for ax, (c, _) in zip(axs.flat, panels):
            ax.fill_between(b.index, b[(c, "min")], b[(c, "max")], color=f"C{k}", alpha=.2, lw=0)
            ax.plot(b.index, b[(c, "median")], color=f"C{k}", label=f"{name} (median, min-max of {n} seeds)")
    for ax, (_, title) in zip(axs.flat, panels):
        ax.set_title(title, fontsize=10); ax.grid(alpha=.3)
    axs[0, 0].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "ensemble_bands.png", dpi=130); plt.close(fig)

    def cell(s, fmt="{:.0f}"):
        return f"{fmt.format(s.median())} [{fmt.format(s.min())}–{fmt.format(s.max())}]"
    # common reporting horizon so every row compares the same years; headers built from it
    y0 = max(df.index.min() for df in ens.values())
    y1 = min(df.index.max() for df in ens.values())
    if any(df.index.min() != y0 or df.index.max() != y1 for df in ens.values()):
        print(f"ensemble files cover different years; summary table restricted to {y0}-{y1}")
    ymid = 2030 if y0 < 2030 < y1 else None
    head = ["scenario", "seeds"] + ([f"price {ymid} (£/MWh)"] if ymid else []) + [
        f"price {y1} (£/MWh)", f"CI {y0} (g/kWh)", f"CI {y1} (g/kWh)", f"LOLE total {y0}-{y1} (h)",
        f"HP homes {y1} (m)", f"offshore wind {y1} (GW)"]
    rows = ["| " + " | ".join(head) + " |", "|---" * len(head) + "|"]
    for name, df in ens.items():
        df = df.loc[(df.index >= y0) & (df.index <= y1)]
        at = lambda y, c: df.loc[df.index == y, c]  # noqa: E731
        cells = [name, str(df.seed.nunique())] + ([cell(at(ymid, "price_twa"))] if ymid else []) + [
            cell(at(y1, "price_twa")), cell(at(y0, "intensity_g_kwh")), cell(at(y1, "intensity_g_kwh")),
            cell(df.groupby("seed").lole_h.sum()), cell(at(y1, "hp_homes_m"), "{:.1f}"),
            cell(at(y1, "cap_wind_offshore"))]
        rows.append("| " + " | ".join(cells) + " |")
    (RES / "ensemble_summary.md").write_text("median [min–max] across seeds\n\n" + "\n".join(rows) + "\n",
                                             encoding="utf-8")
    print("\n".join(rows))
gap_p = RES / "gap_costs.csv"
if gap_p.exists():   # optimal vs emergent (scripts/run_gap.py)
    sys.path.insert(0, str(ROOT))
    from ukabm.gap import summarise
    from ukabm.scenarios import LADDER
    OPT, EMG, INV, OPS, INK = "#111111", "#257de0", "#257de0", "#f47230", "#444444"
    gc = pd.read_csv(gap_p)
    gs = summarise(gc)
    full = LADDER[-1][0]

    # 1. the gap over time (deck slide 5, with results): planner vs agents, baseline full model
    b = gc[gc.run == full]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for kind, col, lab in (("agents_realised", EMG, "Emergent: agents (realised)"), ("planner", OPT, "Optimal: one planner")):
        piv = b[b.kind == kind].pivot_table(index="year", columns="seed", values="total")
        ax.fill_between(piv.index, piv.min(1), piv.max(1), color=col, alpha=.15, lw=0)
        ax.plot(piv.index, piv.median(1), color=col, lw=2, marker="o", ms=4, label=f"{lab}, median and range of {piv.shape[1]} seeds")
    ax.set_ylabel("System cost (GBP bn/yr)"); ax.set_ylim(bottom=0); ax.grid(alpha=.3)
    ax.set_title("Baseline: system cost of the optimal and the emergent pathway", fontsize=11)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "gap_over_time.png", dpi=130); plt.close(fig)

    # 2. where the gap comes from (deck slide 11): ladder of idealised -> full agents, PV 2025-54
    lad = [l for l, _ in LADDER if l in set(gs.run)]
    if lad:
        med = gs.groupby("run").median(numeric_only=True).reindex(lad)
        lo = gs.groupby("run").gap_total_bn.min().reindex(lad)
        hi = gs.groupby("run").gap_total_bn.max().reindex(lad)
        fig, ax = plt.subplots(figsize=(9, 4.3))
        y = range(len(lad))[::-1]
        ax.barh(y, med.gap_investment_bn, color=INV, height=.55, label="investment: what was built")
        ax.barh(y, med.gap_operation_bn, left=med.gap_investment_bn.clip(lower=0), color=OPS, height=.55,
                label="operation: how it was run")
        ax.errorbar(med.gap_total_bn, list(y), xerr=[med.gap_total_bn - lo, hi - med.gap_total_bn], fmt="none",
                    ecolor=INK, capsize=3, lw=1)
        for yy, v, pct in zip(y, med.gap_total_bn, med.gap_total_pct):
            ax.text(max(hi.max(), v) * 1.02 + 1, yy, f"GBP {v:.0f}bn ({pct:.0f} %)", va="center", fontsize=8, color=INK)
        ax.set_yticks(list(y)); ax.set_yticklabels(lad, fontsize=9)
        ax.axvline(0, color=OPT, lw=1)
        ax.set_xlim(min(0, med.gap_total_bn.min()) * 1.2 - 2, hi.max() * 1.35 + 5)
        ax.set_xlabel("Gap to the optimum, PV 2025-2054 (GBP bn, 3.5 %); bars: median, whiskers: seed range", fontsize=9)
        ax.set_title("Where the gap comes from: agent frictions added one at a time (baseline)", fontsize=11)
        ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
        ax.grid(axis="x", alpha=.3)
        fig.tight_layout(); fig.savefig(FIG / "gap_ladder.png", dpi=130); plt.close(fig)

    # 3. how to close it (deck slide 13): gap by market design / policy lever, full agents
    order = [full] + [r for r in gs.run.unique() if r not in dict(LADDER)]
    lev = gs[gs.run.isin(order)]
    if lev.run.nunique() > 1:
        fig, ax = plt.subplots(figsize=(8.5, 3.8))
        for k, r in enumerate(order[::-1]):
            v = lev[lev.run == r].gap_total_pct
            ax.plot([v.min(), v.max()], [k, k], color="#c5c5bd", lw=6, solid_capstyle="round")
            ax.plot(v.median(), k, "o", color=EMG, ms=9, mec="white", mew=1.5)
            ax.text(v.max() + 0.6, k, f"{v.median():.0f} %", va="center", fontsize=8, color=INK)
        ax.set_yticks(range(len(order))); ax.set_yticklabels([("baseline" if r == full else r) for r in order[::-1]], fontsize=9)
        ax.axvline(0, color=OPT, lw=1.5); ax.text(0, len(order) - 0.4, " optimal", fontsize=8)
        ax.set_xlabel("Gap to the optimum, % of the optimum's PV system cost (dot: median; bar: seed range)")
        ax.set_title("Gap by scenario: each scenario against its own optimum", fontsize=11)
        ax.grid(axis="x", alpha=.3); ax.set_ylim(-0.6, len(order) - 0.2)
        fig.tight_layout(); fig.savefig(FIG / "gap_levers.png", dpi=130); plt.close(fig)

    # 4. what each pathway builds: capacity, planner vs agents, baseline seed with the median gap
    cp_p = RES / "gap_capacity.csv"
    if cp_p.exists():
        cap = pd.read_csv(cp_p)
        bs = gs[gs.run == full].sort_values("gap_total_bn")
        seed = int(bs.iloc[len(bs) // 2].seed)
        c = cap[(cap.run == full) & (cap.seed == seed)]
        years = sorted(c.year.unique())[1:]
        techs = [t for t in COL if t in set(c.tech)]
        fig, ax = plt.subplots(figsize=(10, 4.6))
        x, labels = 0, []
        for yr in years:
            for path in ("planner", "agents"):
                s = c[(c.year == yr) & (c.pathway == path)].set_index("tech").gw.reindex(techs).fillna(0)
                bottom = 0
                for t, v in s.items():
                    ax.bar(x, v, bottom=bottom, color=COL[t], width=.8, edgecolor="white", lw=.6,
                           label=t if (yr, path) == (years[0], "planner") else None)
                    bottom += v
                labels.append(f"{yr}\n{'optimal' if path == 'planner' else 'agents'}")
                x += 1
            x += .5
        ax.set_xticks([i + (i // 2) * .5 for i in range(len(labels))]); ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel("GW"); ax.set_title(f"Installed capacity, optimal vs agents (baseline, seed {seed})", fontsize=11)
        ax.legend(fontsize=7, ncol=1, loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
        ax.grid(axis="y", alpha=.3)
        fig.tight_layout(); fig.savefig(FIG / "gap_capacity.png", dpi=130); plt.close(fig)

    tab = gs.groupby("run", sort=False).agg(
        seeds=("seed", "nunique"), planner=("pv_planner_bn", "median"), agents=("pv_agents_realised_bn", "median"),
        gap=("gap_total_bn", "median"), gap_min=("gap_total_bn", "min"), gap_max=("gap_total_bn", "max"),
        investment=("gap_investment_bn", "median"), operation=("gap_operation_bn", "median"),
        pct=("gap_total_pct", "median"))
    rows = ["| run | seeds | optimal PV (£bn) | agents PV (£bn) | gap (£bn) [range] | of which investment | of which operation | gap (%) |",
            "|---|---|---|---|---|---|---|---|"]
    for r, t in tab.iterrows():
        rows.append(f"| {r} | {t.seeds:.0f} | {t.planner:.0f} | {t.agents:.0f} | {t.gap:.0f} [{t.gap_min:.0f}–{t.gap_max:.0f}] | "
                    f"{t.investment:.0f} | {t.operation:.0f} | {t.pct:.1f} |")
    (RES / "gap_summary.md").write_text(
        "Present value of system cost 2025-2054 at 3.5 % (GBP bn, 2024 prices), median across seeds.\n"
        "Gap = agents' realised cost - planner's cost; investment = both fleets under the same least-cost\n"
        "dispatch; operation = agents' realised - least-cost dispatch of the agents' fleet.\n\n" + "\n".join(rows) + "\n",
        encoding="utf-8")
    print("\n".join(rows))
print("figures:", sorted(p.name for p in FIG.glob("*.png")))

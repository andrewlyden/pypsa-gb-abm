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
axs[0].stackplot(base.index, base.demand_twh - base.heat_twh - base.ev_twh - base.h2_twh,
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
print("figures:", sorted(p.name for p in FIG.glob("*.png")))

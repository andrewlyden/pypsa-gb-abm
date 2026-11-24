# ukabm model design

## Architecture
```
                 ┌───────────── Government / policy (config.Policy) ─────────────┐
                 │ carbon path · CfD rounds (pots, admin strikes) · T-4 CM · RO  │
                 └───────┬──────────────────────┬───────────────────────┬────────┘
                         │ contracts            │ levies                │ grants
 ┌──────────────┐  offers ┌──────────────────┐ prices ┌──────────────────────────────┐
 │ GenCo agents │────────▶│ Hourly market     │──────▶│ Multi-energy modules          │
 │ (5, hetero-  │◀────────│ (uniform price,   │◀──────│ HeatModule (household agents) │
 │ geneous WACC,│ dispatch│  ORDC scarcity,   │ load  │ GasNetworkModule (tariffs)    │
 │ beliefs,     │         │  storage, flex,   │       │ EVModule (smart/unmanaged)    │
 │ mark-ups)    │         │  interconnectors) │       │ HydrogenModule (electrolysers)│
 └──────┬───────┘         └────────┬─────────┘       └──────────────────────────────┘
        │ invest/retire            │ sample hours
        ▼                          ▼
  plant pipeline         PyPSA-GB zonal network (PyPSA + HiGHS): redispatch cost,
  (lead times)           zonal prices → locational siting signal
```

## Annual loop (`GBMarketModel.step`)
1. Commission pipeline / retire (end of life, 2 consecutive loss years without CM contract).
2. Demand = ESPENI-2024 shape × growth + heat-pump load (temperature-shaped) + EVs + electrolysers.
3. Market: pass 1 clears inflexible demand → storage arbitrage, smart EV valley-filling and electrolysers
   respond → pass 2 → pass 3 withdraws exports/electrolysers above their willingness-to-pay.
4. Settlement per plant: energy, CfD difference (strike – price), RO, CM; emissions; gas burn.
5. Every *k* years: PyPSA zonal redispatch on sampled hours → constraint cost, zonal prices.
6. Retail tariffs (wholesale + network + levies) → household heating decisions; gas throughput (homes +
   industry + **power-sector gas burn**) → gas network tariff.
7. Investment: forecast prices for *t+3* from the known pipeline; CfD round; T-4 CM; sequential merchant
   decisions, re-forecasting after each (agents see each other's commitments).

## Agents
| agent | decisions | heterogeneity |
|---|---|---|
| GenCo ×5 (IntegratedUtility, MerchantIPP, OilMajor, InfraFund, GreenDeveloper) | offers, CfD bids (LCOE at de-risked WACC), CM bids (net missing money), merchant NPV investment, retirement | WACC 6–10 %, myopic/adaptive/carbon-optimist beliefs, mark-ups 0–8 %, risk aversion, budgets |
| Households ×2000 (each ≈14k homes) | heating system at boiler replacement (logit on lifecycle cost + hassle) | heat demand, discount rate, hassle cost, on/off gas grid, boiler age |
| Government (Policy) | carbon path, CfD target/pots, CM target & curve, HP grant, levy rebalancing | scenario |

## Multi-energy hooks (extension points)
* `HeatModule.hourly_load` — swap synthetic temperature for PyPSA-GB atlite cutouts; add HP flexibility.
* `GasNetworkModule.update(h2_blend=…)` — hydrogen blending / network repurposing.
* `HydrogenModule` — add H2 storage and endogenous H2 price feeding `Fuels.hydrogen` for h2_turbine.
* `EVModule` — replace stock path with adoption agents; V2G as storage.
* `network.redispatch` — switch to PyPSA-GB Reduced (32-bus) / ETYS network, or call PyPSA-GB's
  `solve_balancing.py` stage directly with ABM bids.

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
  plant pipeline         PyPSA-GB zonal network (PyPSA + HiGHS), ETYS boundary capabilities by year:
  (lead times)           BM-style redispatch (bids/offers) → constraint cost, curtailment, post-BM mix/CI;
                         zonal prices → siting signal only in the locational_signal (zonal-pricing) sensitivity
```

## Annual loop (`GBMarketModel.step`)
1. Commission pipeline / retire (end of life, 2 consecutive loss years without CM contract).
2. Demand = ESPENI-2024 shape × growth + heat-pump load (temperature-shaped) + EVs + electrolysers.
3. Market: pass 1 clears inflexible demand → smart EV valley-filling and electrolysers respond → storage
   is dispatched in tranches, each on the price left by the tranches before it, skipping days on which a
   tranche's own trades lose money → pass 2 → pass 3 withdraws electrolysers above their willingness-to-pay.
   The hourly merit order is built once per market run and reused across passes (`market.merit_order`). Interconnectors
   trade inside every pass: per neighbour market (FR, NL, BE, NO2, DK1, DE, SEM) an import offer at
   foreign price + spread and an export bid at foreign price − spread (a "buy-back" block, so exports
   are curtailed exactly when the GB price is above the bid). Foreign prices = existing-CCGT SRMC ×
   market level × the observed 2024 hourly price shape of that neighbour.
4. Settlement per plant: energy, CfD difference (strike – price), RO, CM; emissions; gas burn. Batteries
   also earn `battery_services_per_mw`: ancillary and intraday/BM trading pots shared across the fleet.
   The same function enters battery investment NPVs and CM bids, at the expected fleet size.
5. Every *k* years: network stage (`network_stage`). 96 hours stratified by wind CF. Each plant's market
   schedule can be turned down at its BM bid (`bm_bids`: thermal SRMC, −ROC, −CfD top-up, nuclear −£300)
   and its headroom turned up at its offer, on the 20-zone network with year-dependent boundary
   capabilities and monthly availability (`PyPSAGBData.links_for_year`, `link_availability`). Outputs:
   annualised constraint cost, curtailment, net redispatch by technology and post-BM NESO-basis CI
   (reporting only). Interconnector flows are fixed injections at their landing zones. Zonal prices feed
   siting only in the `locational_signal` sensitivity; by default siting follows resource shares
   (GB national pricing).
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
* `network.redispatch` — add zonal (Scottish vs English) wind profiles, KVL on the PyPSA-GB Reduced
  (32-bus) network, or call PyPSA-GB's `solve_balancing.py` stage directly with ABM bids; feed
  constraint costs into BSUoS in the retail tariff.

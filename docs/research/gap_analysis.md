# Gap analysis: what a GB multi-energy ABM needs that existing tools lack

1. **Cross-sector feedback loops (biggest gap).** No reviewed electricity ABM endogenises heat-pump
   adoption, and the heat ABMs (CNZ, HP-policy ABM) take electricity prices exogenously. The GB-critical
   loops are: wholesale price + policy levies → retail tariffs → heating choice → electric heat load →
   winter peak → CM procurement & scarcity prices; and fewer gas customers → higher gas network
   tariffs per unit → further switching ("death spiral"). *ukabm implements both loops in stylised form.*
2. **GB policy instrument fidelity.** CfD allocation rounds (pots, administrative strike prices, budget),
   T-4/T-1 CM with sloping demand curve and de-rating, RO legacy, CPS; and their *interaction*
   (e.g. CfD units outside the CM still counting towards security). Existing ABMs model generic
   versions. *ukabm: implemented, simplified (no budget in £, no T-1, no non-delivery penalties).*
3. **Network constraints and locational signals.** GB's REMA debate (zonal/nodal pricing vs national price)
   needs ABM investors reacting to locational signals; ABMs are copperplate, optimisation models
   (PyPSA-GB) have no behavioural investors. *ukabm: PyPSA-GB zonal redispatch + zonal-price siting
   heuristic; TNUoS not modelled.*
4. **Balancing mechanism behaviour.** Strategic BM bidding (constraint payments for Scottish wind, CfD
   negative bids) is in PyPSA-GB as a cost-based stage, but not as learned agent behaviour. *Gap remains.*
5. **Flexibility from consumers.** EV smart charging, heat-pump thermal storage, demand turn-down
   (DFS) need behavioural participation rates, not perfect optimisation. *ukabm: smart share parameter
   with valley filling; HP flexibility not yet.*
6. **Hydrogen system coupling.** Electrolyser dispatch vs H2 value, H2 storage, H2-to-power, blending into
   gas networks; hydrogen economics are exogenous everywhere. *ukabm: hooks only.*
7. **Expectation formation & risk.** Price forecasting matters (PowerACE), and agents' carbon-price
   beliefs drive investment. *ukabm: myopic/adaptive/optimist beliefs; no learning yet.*
8. **Validation against GB outturn.** Few ABMs are validated on GB prices/dispatch. PyPSA-GB has 2020
   validation data and Elexon calibration caches. *ukabm: not yet validated — top post-workshop task.*
9. **Weather-year and uncertainty.** One profile year (2024 ESPENI) and synthetic temperature only;
   need multiple weather years (PyPSA-GB atlite cutouts) and Monte-Carlo (EMLab/ElecSim do this).

## Scope decision for ukabm v0.1 (workshop)
*In:* hourly GB wholesale clearing with agent offers; CfD, CM, carbon, RO; merchant investment with
heterogeneous expectations; PyPSA-GB zonal network stage; heat/gas/EV/H2 coupling modules.
*Out (roadmap):* strategic BM, nodal network in the loop, RL agents, T-1 CM, explicit H2 network,
multi-weather-year Monte-Carlo, calibration.

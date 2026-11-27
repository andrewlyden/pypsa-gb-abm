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

## Update, 27 November 2026: what the second review changes

The list above is about features that existing tools lack. The second review
([literature review](literature_review.md), sections 4–8;
[foundations review](../review_2026-11_foundations.md)) looked at methods and evidence, and changes
five of the nine points:

* **Point 2, policy instrument fidelity.** The instruments exist in the model but do not reproduce the
  auctions: offshore bids are £53–66/MWh against £91 in AR7, and the Capacity Market clears at its cap
  for a decade. Fidelity now means calibration to AR1–AR7 and T-4 2014–2026, not more rules (F10–F12).
* **Point 7, expectations and risk.** The gap in the literature is narrower than "no learning":
  results of investment ABMs depend above all on how future prices are projected and on the order in
  which firms move (Tao et al. 2021). This model's projection (its own market run on the true future
  paths with only the committed pipeline) is the variant that study finds most sensitive (F8, F9).
* **Point 8, validation.** Still the largest gap, here and in the field: the only investment back-cast
  found (ElecSim, GB 2013–18) is fitted in-sample. An investment hindcast from 2015 with patterns fixed
  in advance would be a contribution in its own right (F20).
* **Point 9, uncertainty.** Seeds here vary agent draws in a deterministic world; weather, fuel,
  carbon and demand are fixed. Adequacy studies use 34 weather years × 100 outage patterns (F3, F21).
* **A tenth gap: a benchmark.** No reviewed study attributes an investment gap against an optimum to
  its sources for a real market's instruments. The nearest compare operation only (Torralba-Díaz et al.
  2020), a stylised system (Jonson et al. 2020) or a learned mix without attribution (Gonzalez-Ruiz et
  al. 2025). This is the project's opening, and it is why the optimum must be robust before the gap is
  read (F1–F6, F17).

What existing tools already do and this repository does not: scenarios and parameters as data files
with a schema, tagged releases with a DOI, back-tests shipped as runnable scenarios, and a protocol
description (F26–F33).

## Scope decision for ukabm v0.1 (workshop)
*In:* hourly GB wholesale clearing with agent offers; CfD, CM, carbon, RO; merchant investment with
heterogeneous expectations; PyPSA-GB zonal network stage; heat/gas/EV/H2 coupling modules.
*Out (roadmap):* strategic BM, nodal network in the loop, RL agents, T-1 CM, explicit H2 network,
multi-weather-year Monte-Carlo, calibration.

# Capability vs UK multi-energy challenge matrix

Legend: **●** core capability · **◐** partial / via extension / stylised · **○** not covered.
Based on documentation reviewed (see [literature review](literature_review.md) for citations); verify before quoting.
Last column = this repository (*ukabm v0.1*) as built for the workshop.

| UK challenge | AMIRIS | EMLab-Gen | ASSUME | PowerACE | ElecSim | AMES | CNZ heat ABM | PyPSA-GB (opt.) | **ukabm v0.1** |
|---|---|---|---|---|---|---|---|---|---|
| Wholesale bidding & price formation | ● strategic bidding [AMIRIS] | ◐ LDC segments [EMLab] | ● RL bidding [ASSUME] | ● hourly DA [PowerACE] | ◐ | ● DA/RT [AMES] | ○ | ◐ cost-based + BM bids [PyPSA-GB] | ● hourly uniform price, agent mark-ups, ORDC scarcity |
| Long-term investment & expectations | ◐ | ● NPV, imperfect expectations [EMLab] | ◐ | ● [PowerACE-forecast] | ● [ElecSim] | ○ | ○ | ● (central planner) | ● heterogeneous WACC/expectations, re-forecast with pipeline |
| CfD auctions (pots, strike) | ◐ support schemes [AMIRIS] | ◐ | ○ | ○ | ◐ | ○ | ○ | ◐ CfD-aware bids & strike tables | ● AR-style pots, pay-as-clear by tech, 2-way CfD |
| Capacity Market (T-4 demand curve) | ○ | ● CM / strategic reserve [Bhagwat-CM] | ◐ | ◐ | ◐ | ○ | ○ | ◐ CM parameters data | ● sloping demand curve from PyPSA-GB CM params |
| Carbon policy (UK ETS + CPS) | ● | ● | ◐ | ● | ● [Kell-carbon] | ○ | ○ | ● | ● carbon trajectory; agent beliefs differ |
| Network constraints / balancing | ○ | ○ (2 zones) | ◐ | ◐ (market coupling) | ○ | ● LMP [AMES] | ○ | ● ETYS/zonal, wholesale→BM | ◐ PyPSA-GB zonal redispatch on sample hours; zonal price → siting |
| Storage & flexibility | ● storage agents | ◐ | ● | ● | ◐ [Kell-storage] | ○ | ○ | ● | ◐ heuristic daily arbitrage (battery, pumped hydro) |
| Interconnectors | ◐ | ● 2 markets | ◐ | ● multi-country | ○ | ○ | ○ | ● register + TYNDP | ◐ price-responsive tranches; exogenous continent |
| Heat electrification / heat pumps | ○ | ○ | ○ | ○ | ○ | ○ | ● household agents [CNZ-GH] | ◐ demand from FES | ● household agents, logit choice, social influence; elec load |
| Gas networks (cost recovery) | ○ | ○ | ○ | ○ | ○ | ○ | ◐ (gas prices) | ○ | ◐ allowed revenue / throughput feedback |
| Hydrogen (electrolysis, H2-to-power) | ◐ electrolysis agents | ○ | ◐ | ◐ | ○ | ○ | ○ | ● hydrogen system [PyPSA-GB] | ◐ price-responsive electrolysers; H2 turbine tech |
| Transport / EV charging | ◐ | ○ | ◐ | ○ | ○ | ○ | ○ | ◐ FES demand | ◐ stock path, unmanaged vs smart valley-filling |
| Consumer behaviour & retail bills | ○ | ○ | ○ | ○ | ○ | ○ | ● | ◐ consumer-bill layer | ◐ retail tariffs incl. levy pass-through, rebalancing |
| Decarbonisation pathways (FES/CP30) | ◐ | ● | ◐ | ● | ● | ○ | ◐ | ● FES/CP30 | ◐ endogenous pathway; FES calibration TODO |
| Open, Python, PyPSA-linkable | ◐ (Java, pyfame) | ○ (Java) | ● | ○ | ● | ◐ | ● | ● | ● (Mesa + PyPSA) |

Machine-readable version: [capability_matrix.csv](capability_matrix.csv).

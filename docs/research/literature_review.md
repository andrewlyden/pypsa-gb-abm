# Literature & framework survey: agent-based models of electricity markets

*Time-boxed review (workshop prep). Claims are taken from the cited project pages/papers; ratings in the
[capability matrix](capability_matrix.md) are the author's reading of the documentation and should be
checked against each code base before being quoted.*

## 1. Why ABM for the GB system?
Optimisation models (PyPSA-GB, ESO/NESO FES tools) answer *"what is least-cost?"*. ABMs answer
*"what will heterogeneous actors actually do under this market design and policy?"* — investment cycles,
imperfect expectations, missing money, strategic bidding, adoption dynamics and feedbacks between sectors.
EMLab-Generation's authors frame this explicitly as exploring "heterogeneity of actors, consequences of
imperfect expectations and investment behaviour outside of ideal conditions" [EMLab].

## 2. Frameworks reviewed

| Model | Owner / language | Focus | Key features | Source |
|---|---|---|---|---|
| **AMIRIS** | DLR, Java on FAME | Operation & policy | Endogenous prices from strategic bidding of prototyped actors; agent classes: plant operators, traders, marketplaces, policy providers, demand, storage; support-scheme instruments; open source | [AMIRIS-home], [AMIRIS-JOSS], [Helmholtz-RSD] |
| **EMLab-Generation** | TU Delft, Java/AgentSpring | Long-term investment | Two interconnected markets (e.g. UK vs Continent); power companies bid and invest on NPV; load-duration-curve segments; CO2 policy; capacity mechanisms & strategic reserve extensions | [EMLab], [EMLab-GH], [Bhagwat-CM] |
| **ASSUME** | Open-source Python | Operation, learning | Multi-agent deep RL bidding agents; modular market design toolbox | [ASSUME-SoftwareX], [ASSUME-docs] |
| **PowerACE** | KIT, Java | Day-ahead + investment | Hourly European day-ahead market, multi-year, endogenous conventional & storage investment, advanced price forecasting | [PowerACE], [PowerACE-forecast] |
| **ElecSim** | A. Kell, Python | Long-term UK investment | Open source, Monte-Carlo, set up with UK data, policy (carbon tax) optimisation | [ElecSim-GH], [ElecSim-arXiv], [Kell-carbon] |
| **Kell et al. 2021** | Applied Energy | Storage investment | ABM of investment in generation *and storage* in a liberalised market to 2050 | [Kell-storage] |
| **AMES** | Iowa State, Java/Python | Nodal (US RTO) | Day-ahead & real-time markets on a transmission grid, LMP congestion pricing, learning traders | [AMES], [AMES-GH] |
| **Mesa** | Python library | Generic ABM | Agents, schedulers/AgentSets, data collection, visualisation; Apache-2 | [Mesa], [Mesa-docs] |
| **CNZ domestic-heating-abm** | Centre for Net Zero, Python | Heat decarbonisation | Household agents (property type, age, tenure, off-gas-grid) choosing heating systems; policy interventions for HP targets | [CNZ-ABM], [CNZ-GH], [CNZ-BEIS] |
| **Heat-pump policy ABM (2025)** | Cardiff/Sustainable Futures | HP uptake UK | BAU projects 8.7 m HP households (30.8%) by 2050; grant sensitivity | [HP-ABM-2025] |
| **Frontier Economics heat-market ABM** | Consultancy | Heat market design | Agent architecture for a heat market (e.g. energy-plan business models) | [Frontier-heat] |
| **GB EV ABM (2026)** | Academic | EV driving & charging | Validated GB ABM of EV driving/charging with psychological & financial preferences | [EV-GB-ABM], [EV-Imperial], [EV-local] |
| **Hydrogen transition ABMs** | Argonne | H2 vehicles/infrastructure | Co-evolution of H2 supply chain and vehicle adoption | [ANL-H2], [ANL-H2-2] |
| **UK CM & balancing ABM** | Academic | GB capacity mechanism | ABM of interlinks between Capacity Mechanism and Balancing Market (CCGTs etc.) | [UK-CM-BM] |
| **MARL long-term market design (2025)** | arXiv | Investment under market design | RL GENCO agents in long-term market environment | [MARL-LT] |
| **PyPSA-GB** (comparator, not ABM) | A. Lyden et al., Python | GB network optimisation | ETYS network (~2,400 buses), reduced 32-bus and zonal versions; two-stage wholesale + balancing mechanism with CfD/RO/merchant-aware bids; FES & CP30 scenarios; hydrogen, storage, interconnectors | [PyPSA-GB] |

## 3. Observations
1. **Electricity-only is the norm.** AMIRIS, EMLab, ASSUME, PowerACE, ElecSim and AMES are electricity
   market models. Heat, EV and hydrogen behaviour live in *separate* ABMs (CNZ, EV-GB, Argonne) with
   exogenous electricity prices — the coupling is generally missing.
2. **Investment vs operation split.** AMIRIS/ASSUME are strong on short-term bidding; EMLab/ElecSim
   on long-term investment; PowerACE covers both at European scale.
3. **Networks are weak in ABMs.** Except AMES (US nodal) most ABMs are copperplate/zonal. GB's defining
   operational problem — Scotland–England boundary constraints and £bn balancing costs — needs a
   network stage, which PyPSA-GB already provides.
4. **GB-specific policy instruments** (CfD allocation rounds with pots, T-4/T-1 Capacity Market with sloping
   demand curve, RO, UK ETS + Carbon Price Support) are only partially represented (ElecSim/EMLab for
   carbon & capacity mechanisms; AMIRIS for support schemes but German-centric).
5. **Mesa is the natural Python substrate** to link to PyPSA (both Python), unlike Java-based AMIRIS/EMLab.

## References
- [AMIRIS-home] DLR, *AMIRIS*. https://dlr-ve.gitlab.io/esy/amiris/home/
- [AMIRIS-JOSS] Schimeczek et al. (2023) AMIRIS, *JOSS* 8(84) 5041. https://elib.dlr.de/194776/1/10.21105.joss.05041_AMIRIS.pdf
- [Helmholtz-RSD] https://helmholtz.software/software/amiris
- [EMLab] Chappin (2013) EMLab-Generation overview. https://emlab.tudelft.nl/generation/
- [EMLab-GH] https://github.com/EMLab/emlab-generation
- [Bhagwat-CM] Bhagwat et al., Cross-border effects of capacity mechanisms in interconnected power systems. https://www.researchgate.net/publication/315752173
- [ASSUME-SoftwareX] ASSUME (2025), *SoftwareX*. https://www.sciencedirect.com/science/article/pii/S2352711025001438
- [ASSUME-docs] https://assume.readthedocs.io/en/latest/learning.html
- [PowerACE] PowerACE – Agent-based electricity market model. https://www.researchgate.net/publication/379271153
- [PowerACE-forecast] Advanced price forecasting in agent-based electricity market simulation, *Applied Energy* (2021). https://www.sciencedirect.com/science/article/abs/pii/S0306261921002142
- [ElecSim-GH] https://github.com/alexanderkell/elecsim ; [ElecSim-arXiv] https://arxiv.org/abs/1911.01203 ; [Kell-carbon] https://arxiv.org/pdf/2006.01601
- [Kell-storage] Investing in generation and storage capacity in a liberalised electricity market: an agent based approach, *Applied Energy* (2021). https://www.sciencedirect.com/science/article/abs/pii/S0306261921003871
- [AMES] https://www2.econ.iastate.edu/tesfatsi/AMESMarketHome.htm ; [AMES-GH] https://github.com/ames-market/AMES-V5.0
- [Mesa] https://github.com/mesa/mesa ; [Mesa-docs] https://mesa.readthedocs.io/stable/
- [CNZ-ABM] https://www.centrefornetzero.org/technologies/agent-based-model ; [CNZ-GH] https://github.com/centrefornetzero/domestic-heating-abm ; [CNZ-BEIS] https://heatpumpingtechnologies.org/content/uploads/2022/11/05-beis--iea-heat-pump-research-conf-nov-2022.pdf ; https://www.centrefornetzero.org/papers/hitting-the-target-meeting-the-uk-s-heat-pump-targets
- [HP-ABM-2025] Agent-based modelling approach to explore efficacy of policies for heat pump uptake (2025). https://www.sciencedirect.com/science/article/pii/S266618882501161X
- [Frontier-heat] https://www.frontier-economics.com/media/t1qpocir/frontier-economics-agent-based-modelling-of-a-heat-market.pdf
- [EV-GB-ABM] https://www.sciencedirect.com/science/article/pii/S026427512600096X ; [EV-Imperial] https://spiral.imperial.ac.uk/server/api/core/bitstreams/dd9dd096-6813-479c-88b9-0edebd7df5ab/content ; [EV-local] https://www.sciencedirect.com/science/article/pii/S1877050921007833
- [ANL-H2] https://ceeesa.es.anl.gov/news/multiagent_hydrogen.html ; [ANL-H2-2] https://ieeexplore.ieee.org/iel5/9256/29392/01331110.pdf
- [UK-CM-BM] Balancing the UK electricity grid: interlinks between Capacity Mechanism and the Balancing Market. https://www.researchgate.net/publication/265627994
- [MARL-LT] https://arxiv.org/html/2512.17444
- [PyPSA-GB] https://github.com/andrewlyden/PyPSA-GB ; https://pypsa-gb.readthedocs.io

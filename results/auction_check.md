# Auction check: the model's first auctions against the auctions held

Baseline, seeds [1, 2, 3, 4, 5], code at 7cf345a. No model parameter was set to reproduce these results.

| auction | model, median [range] | held | difference | implied cost factor |
|---|---|---|---|---|
| CfD strike, offshore wind (£/MWh, 2024 prices) | 109.0 [108.5–109.6] | AR7 91.2 (AR6 82.0) | +20 % | 0.75 |
| CfD strike, onshore wind (£/MWh, 2024 prices) | 62.7 [62.2–62.8] | AR7 72.2 (AR6 70.9) | -13 % | 1.19 |
| CfD strike, solar (£/MWh, 2024 prices) | 65.3 [64.7–66.3] | AR7 65.2 (AR6 69.7) | +0 % | 1.00 |
| Capacity Market T-4, delivery 2029 (£/kW/yr) | 38.4 [36.6–38.9] | 27.1 | +42 % | – |

Implied cost factor: the factor on capital cost at which the model's clearing strike would equal the AR7 strike
(reference firm, the technology's hurdle rate). Below 1: winning bidders priced in lower costs, a higher yield or a
lower return than the published assumptions; above 1: the opposite.

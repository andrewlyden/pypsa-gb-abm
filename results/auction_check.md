# Auction check: the model's first auctions against the auctions held

Baseline, seeds [1, 2, 3, 4, 5], code at 399535c. No model parameter was set to reproduce these results.

| auction | model, median [range] | held | difference | implied cost factor |
|---|---|---|---|---|
| CfD strike, offshore wind (£/MWh, 2024 prices) | 105.1 [104.3–106.7] | AR7 91.2 (AR6 82.0) | +15 % | 0.80 |
| CfD strike, onshore wind (£/MWh, 2024 prices) | 57.2 [55.5–57.9] | AR7 72.2 (AR6 70.9) | -21 % | 1.29 |
| CfD strike, solar (£/MWh, 2024 prices) | 66.2 [65.7–66.5] | AR7 65.2 (AR6 69.7) | +2 % | 0.98 |
| Capacity Market T-4, delivery 2029 (£/kW/yr) | 15.0 [13.2–15.4] | 27.1 | -45 % | – |

Implied cost factor: the factor on capital cost at which the model's clearing strike would equal the AR7 strike
(reference firm, the technology's hurdle rate). Below 1: winning bidders priced in lower costs, a higher yield or a
lower return than the published assumptions; above 1: the opposite.

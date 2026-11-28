# Published pathways

| File | Content | Used by |
|---|---|---|
| `fes2025_drivers.csv` | NESO Future Energy Scenarios 2025, Data Workbook V005: 34 annual series 2025–2050 for the four pathways and the Ten Year Forecast (system demand and three of its components, battery electric vehicles, residential heat pumps, peak demand, capacity by technology). One row per pathway, year and series, with the workbook sheet | `ukabm/drivers.py` (exogenous drivers and the government's targets) |
| `published_pathways.csv` | 1,765 values for 2025–2050 from twelve sources: FES 2025, the CCC's Seventh Carbon Budget, the Clean Power 2030 Action Plan and NESO's advice for it, DESNZ projections and carbon values, and four independent studies. One row per source, pathway, year, metric and technology, with the definition, the URL and a `verified` tag | `scripts/compare_pathways.py` |
| `NOTES.md` | how the values were read: sheet and page per source, definitions that matter for a comparison, and what could not be found. It was written for the full extraction (called `pathways.csv` and a drivers file of 152 series there); `fes2025_drivers.csv` here is the subset of those series that the model or the comparison uses | — |

Every value was read from the source's own workbook or tables on 27–28 November 2026; nothing is
interpolated. The licence of the FES workbook and of the other sources is an open question for the
maintainer: see [docs/data.md](../../docs/data.md).

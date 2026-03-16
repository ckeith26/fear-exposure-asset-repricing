# FEAR: Flood Exposure and Asset Repricing

**Evidence from FEMA LOMRs and ZIP-Code Home Values**

This repository contains the data pipeline, econometric estimation, and companion website for a research paper studying how FEMA flood zone reclassifications affect residential property values across US coastal communities.

Companion website: [fear.camkeith.me](https://fear.camkeith.me)

## Research Design

I exploit Letters of Map Revision (LOMRs), official FEMA documents that revise flood zone boundaries, as quasi-exogenous shocks to flood risk information. Using a **staggered difference-in-differences** event study with ZIP and county-by-year fixed effects, I compare home values in ZIP codes that receive their first in-window LOMR against never-treated and not-yet-treated ZIP codes.

**Sample**: 4,272 coastal ZIP codes (398 single-LOMR treated, 3,711 never-treated, 163 post-window) across the contiguous US (excluding Alaska and Hawaii), 2009-2022.

**Primary outcome**: Log real Zillow Home Value Index (`ln_real_zhvi`), deflated to December 2022 dollars.

### Key Findings

- Home values show **near-zero response at impact** but decline by approximately **2.8 percent** four or more years after a LOMR (baseline specification).
- The decline is **larger when weighted by pre-treatment NFIP policy intensity** (policies per capita), with an implied effect of about 4.2 percent at the sample mean.
- The effect is **concentrated in Democratic-leaning counties**; Republican-leaning counties show no statistically meaningful response, though this interaction fails the pre-trend test and is treated as descriptive.
- The Callaway and Sant'Anna heterogeneity-robust estimator does not reproduce the baseline pattern cleanly, and the result is sensitive to the inclusion of Florida. These limitations are discussed in the paper.

### Hypotheses

| # | Hypothesis | Test | Do-file Section |
|---|-----------|------|-----------------|
| H1 | LOMRs are associated with lower home values | Baseline event study | s04, s05 |
| H2 | Response emerges gradually (market frictions) | Dynamic event-study coefficients | s05 |
| H3 | Higher pre-treatment NFIP exposure strengthens repricing (salience) | Policy intensity interaction; insurance outcomes | s06, s06b, s08, s09d |
| H4 | Political beliefs shape attention to flood-risk information (exploratory) | Republican vote share interaction | s09c |

## Repository Structure

```
flood-exposure-asset-repricing/
├── paper/                 # LaTeX paper, figures, and tables
│   ├── econ66-fear.tex    # Main paper source
│   ├── econ66-fear.pdf    # Compiled paper
│   ├── references_honors.bib
│   ├── figures/           # Event study plots and maps
│   └── tables/            # Regression output tables
├── src/scripts/           # Data pipeline and estimation scripts
│   ├── download_*.py      # Data acquisition (FEMA, BLS, Census, elections)
│   ├── clean_*.py         # Geographic filtering and data cleaning
│   ├── overlay_lomr_zcta.py   # LOMR-ZCTA spatial overlay
│   ├── aggregate_nfip_policies.py  # NFIP insurance aggregation
│   ├── compute_summary_stats.py    # Regression panel construction
│   ├── export_website_data.py      # Website data exports
│   └── event_study.do     # Stata estimation (all specifications)
├── output/                # Stata regression output (CSVs, figures, TeX)
│   ├── results/           # Main specification
│   ├── results_1000p/     # Population >= 1,000 robustness
│   └── results_density1000/  # Density >= 1,000/sq mi robustness
├── website/               # Next.js companion website
├── Makefile               # Full pipeline DAG with incremental rebuilds
├── setup.sh               # Environment setup
└── requirements.txt       # Python dependencies
```

## Quick Start

### Prerequisites

- Python 3.9+
- [Stata](https://www.stata.com/) (for estimation only)
- ~35 GB disk space for raw data

Required Stata packages: `reghdfe`, `ftools`, `estout`, `bacondecomp`, `drdid`, `csdid`. Install via `ssc install <pkg>, replace`.

### Setup

```bash
# Create virtual environment and install dependencies
bash setup.sh
source .venv/bin/activate
```

### Build the Regression Panel

The `Makefile` encodes the full data pipeline DAG. Before running, you need to manually download several large datasets (see [Data Sources](#data-sources) below).

```bash
make check-data           # Verify required raw files exist
make                      # Build regression panel (default target)
make download -j4         # Download scriptable sources in parallel
make estimate             # Run Stata event study (requires Stata on PATH)
make website              # Export data for companion website
```

Override configuration defaults:

```bash
make panel THRESHOLD=50k START_YEAR=2010 END_YEAR=2021
```

### Run Individual Scripts

Each pipeline stage can be run independently:

```bash
# Data acquisition
python src/scripts/download_FEMA.py              # FEMA LOMR polygons (~180 MB)
python src/scripts/download_bls_laus.py           # BLS county unemployment (~200 MB)
python src/scripts/download_election_returns.py   # MIT Election Lab returns (~75 MB)
python src/scripts/download_census_population.py  # 2010 Census ZCTA population
python src/scripts/download_acs_population.py     # ACS 2007-2011 ZCTA population

# Data cleaning
python src/scripts/clean_coastal_counties.py      # Geographic filtering -> coastal zips
python src/scripts/overlay_lomr_zcta.py           # LOMR-ZCTA spatial overlay

# NFIP aggregation
python src/scripts/aggregate_nfip_policies.py --start-year 2009 --end-year 2022

# Panel construction
python src/scripts/compute_summary_stats.py --save-panel
```

## Data Pipeline

```
FEMA ArcGIS API ──> download_FEMA.py ──> s_lomr_national.gpkg
                                              │
NOAA Coastal Counties ─┐                      │
Census ZCTA Boundaries ├> clean_coastal_counties.py ──> coastal_zipcodes.csv
SimpleMaps Zip Codes ──┘                      │              │
                                              │              │
                                    overlay_lomr_zcta.py <───┘
                                              │
                              lomr_zcta_overlay.csv + treatment timing CSVs
                                              │
NFIP Policies (30 GB) ─┐                      │
NFIP Claims (2.3 GB) ──┤> aggregate_nfip_policies.py ──> nfip_zip_month_panel.csv
                        │                                  nfip_lomr_deltas.csv
                        │                                        │
Zillow ZHVI ────────────┤                                        │
BLS Unemployment ───────┤> compute_summary_stats.py ──> regression_panel.csv
Election Returns ───────┤                                        │
                        │                                        │
Disclosure Laws ────────┘> event_study.do ──> tables, figures, coefficient CSVs
```

## Data Sources

### Scripted Downloads

| Dataset | Source | Size | Script |
|---------|--------|------|--------|
| FEMA LOMR Polygons | [NFHL ArcGIS REST API](https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/1) | ~180 MB | `download_FEMA.py` |
| BLS LAUS Unemployment | [Bureau of Labor Statistics](https://www.bls.gov/lau/) | ~200 MB | `download_bls_laus.py` |
| Presidential Election Returns | [MIT Election Data + Science Lab](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/VOQCHQ) | ~75 MB | `download_election_returns.py` |
| 2010 Census Population | [US Census Bureau](https://www.census.gov/) | ~5 MB | `download_census_population.py` |
| ACS 2007-2011 Population | [US Census Bureau](https://www.census.gov/) | ~5 MB | `download_acs_population.py` |

### Manual Downloads

These datasets must be obtained directly from their providers before running the pipeline:

| Dataset | Source | Size |
|---------|--------|------|
| NFIP Policies | [OpenFEMA](https://www.fema.gov/openfema-data-page/fima-nfip-redacted-policies-v2) | ~30 GB |
| NFIP Claims | [OpenFEMA](https://www.fema.gov/openfema-data-page/fima-nfip-redacted-claims-v2) | ~2.3 GB |
| Zillow ZHVI (Zip) | [Zillow Research](https://www.zillow.com/research/data/) | ~95 MB |
| ZCTA Boundaries (TIGER/Line 2020) | [US Census Bureau](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.2020.html) | ~830 MB |
| US Zip Code Database | [SimpleMaps](https://simplemaps.com/data/us-zips) | ~9 MB |

### Hand-Curated

| Dataset | Description |
|---------|-------------|
| [State Disclosure Laws](data/raw/state-disclosure-laws/disclosure_laws_sources.md) | 9 states with verified mandatory flood zone seller disclosure, with full statutory citations |

## Stata Estimation

The main estimation script (`src/scripts/event_study.do`) produces all tables and figures.

Key specifications:

| Section | Specification | Outcome |
|---------|--------------|---------|
| s05 | Main binary event study | `ln_real_zhvi` |
| s06 | Policy intensity interaction (NFIP policies/population) | `ln_real_zhvi` |
| s06b | Intensity quartile interactions | `ln_real_zhvi` |
| s08 | Insurance market outcomes | `ln_policies`, `ln_claims` |
| s09 | Up/down zoned decomposition | `ln_real_zhvi` |
| s09b | Disclosure law interaction | `ln_real_zhvi` |
| s09c | Republican vote share interaction (exploratory) | `ln_real_zhvi` |
| s09d | SFHA-crossing subsample | `ln_real_zhvi` |
| s12 | Bacon decomposition | diagnostic |
| s13 | Callaway and Sant'Anna | `ln_real_zhvi` |
| s14 | Placebo (unemployment outcome) | `unemployment_rate` |
| s15 | Leave-one-out by state | `ln_real_zhvi` |
| s16 | Alternative clustering (state level) | `ln_real_zhvi` |

## Companion Website

The `website/` directory contains a Next.js application that presents interactive results:

```bash
cd website
npm install
npm run dev        # Development server at localhost:3000
npm run build      # Production build (static export)
```

The website displays event study plots, regression tables, summary statistics, an interactive treatment map, and downloadable replication data. Deployed at [fear.camkeith.me](https://fear.camkeith.me).

## License

This repository is provided for academic replication and research purposes.

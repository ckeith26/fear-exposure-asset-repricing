# ==============================================================================
# FEAR: Flood Exposure Asset Repricing — Data Pipeline
# ==============================================================================
#
# Full DAG from raw data acquisition through regression panel construction.
#
# Usage:
#     make                  # build regression panel (default)
#     make panel            # same as above
#     make download         # download all external data sources
#     make estimate         # run Stata event study (requires Stata)
#     make website          # build website data exports
#     make check-data       # verify required raw files exist
#     make clean            # remove processed data
#     make help             # show all targets
#
# Parallel execution:
#     make -j4 download     # download sources concurrently
#     make -j4 panel        # parallelize independent processing steps
#
# Override defaults:
#     make panel THRESHOLD=50k START_YEAR=2010 END_YEAR=2021
#
# ==============================================================================

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

# === CONFIGURATION ===

THRESHOLD  ?= 25k
START_YEAR ?= 2009
END_YEAR   ?= 2022
PYTHON     ?= python
STATA      ?= stata

# Derived paths
WINDOW       := $(START_YEAR)-$(END_YEAR)
RAW          := data/raw
CLEAN        := data/clean
SCRIPTS      := src/scripts
OUTPUT       := output
RESULTS      := $(OUTPUT)/results
WEBSITE_DATA := website/public/data

# Key intermediate files
COASTAL_SENTINEL   := $(CLEAN)/coastal-counties/.done
OVERLAY_SENTINEL   := $(CLEAN)/.overlay.done
NFIP_SENTINEL      := $(CLEAN)/.nfip.done
TREATMENT_CSV      := $(CLEAN)/coastal_zipcodes_lomr_tr_$(THRESHOLD)_$(WINDOW).csv
REGRESSION_PANEL   := $(CLEAN)/regression_panel.csv

# Raw data paths (manual downloads — not produced by pipeline scripts)
ZHVI_CSV       := $(RAW)/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv
NFIP_POLICIES  := $(RAW)/FEMA/nfip/FimaNfipPoliciesV2.csv
NFIP_CLAIMS    := $(RAW)/FEMA/nfip/FimaNfipClaimsV2.csv
ZCTA_SHP       := $(RAW)/tiger-census/tl_2025_us_zcta520.shp
USZIPS_CSV     := $(RAW)/us-zips/uszips.csv
NOAA_COUNTIES  := $(RAW)/coastal-counties/noaa-counties.geojson
DISCLOSURE_CSV := $(RAW)/state-disclosure-laws/disclosure_laws.csv
BLS_DATA       := $(RAW)/bls-laus/la.data.64.County

# Raw data paths (produced by download scripts)
LOMR_GPKG      := $(RAW)/FEMA/lomr/s_lomr_national.gpkg
CENSUS_POP     := $(RAW)/census-2010/census_2010_zcta_population.csv
ELECTION_RAW   := $(RAW)/election-returns/countypres_2000-2024.tab
ACS_POP        := $(RAW)/census-acs/acs_2007_2011_zcta_population.csv

# Download sentinel files
DL_FEMA     := $(RAW)/FEMA/lomr/.downloaded
DL_BLS      := $(RAW)/bls-laus/.downloaded
DL_ELECTION := $(RAW)/election-returns/.downloaded
DL_ACS      := $(RAW)/census-acs/.downloaded
DL_CENSUS   := $(RAW)/census-2010/.downloaded

# Election clean output
ELECTION_CLEAN := $(CLEAN)/election_county_year.csv


# ==============================================================================
# DEFAULT TARGET
# ==============================================================================

.DEFAULT_GOAL := all

.PHONY: all panel download estimate website check-data help
.PHONY: clean clean-downloads distclean
.PHONY: download-fema download-bls download-election download-acs download-census

all: panel ## Build regression panel (default target)

panel: $(REGRESSION_PANEL) ## Build regression panel from raw data


# ==============================================================================
# HELP
# ==============================================================================

help: ## Show available targets with descriptions
	@echo "FEAR Pipeline — Available Targets"
	@echo "================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk -F ':.*## ' '{printf "  %-22s %s\n", $$1, $$2}'
	@echo ""
	@echo "Configuration (override with VAR=value):"
	@echo "  THRESHOLD   = $(THRESHOLD)"
	@echo "  START_YEAR  = $(START_YEAR)"
	@echo "  END_YEAR    = $(END_YEAR)"
	@echo "  PYTHON      = $(PYTHON)"
	@echo "  STATA       = $(STATA)"


# ==============================================================================
# DOWNLOAD TARGETS
# ==============================================================================

download: download-fema download-bls download-election download-acs download-census ## Download all external data sources

download-fema: $(DL_FEMA) ## Download FEMA LOMR polygons (interactive)
$(DL_FEMA): $(SCRIPTS)/download_FEMA.py
	$(PYTHON) $<
	touch $@

download-bls: $(DL_BLS) ## Download BLS county unemployment
$(DL_BLS): $(SCRIPTS)/download_bls_laus.py
	$(PYTHON) $<
	touch $@

download-election: $(DL_ELECTION) ## Download MIT election returns
$(DL_ELECTION): $(SCRIPTS)/download_election_returns.py
	$(PYTHON) $<
	touch $@

download-acs: $(DL_ACS) ## Download ACS 2007-2011 population
$(DL_ACS): $(SCRIPTS)/download_acs_population.py $(ZCTA_SHP)
	$(PYTHON) $<
	touch $@

download-census: $(DL_CENSUS) ## Download 2010 Census population
$(DL_CENSUS): $(SCRIPTS)/download_census_population.py $(ZCTA_SHP)
	$(PYTHON) $<
	touch $@



# ==============================================================================
# CHECK DATA — verify required manual downloads exist
# ==============================================================================

MANUAL_FILES := $(ZHVI_CSV) $(NFIP_POLICIES) $(NFIP_CLAIMS) $(ZCTA_SHP) \
                $(USZIPS_CSV) $(NOAA_COUNTIES) $(DISCLOSURE_CSV)

check-data: ## Verify all required raw data files exist
	@echo "Checking required raw data files..."
	@missing=0; \
	for f in $(MANUAL_FILES); do \
		if [ ! -f "$$f" ]; then \
			echo "  MISSING: $$f"; \
			missing=$$((missing + 1)); \
		else \
			echo "  OK:      $$f"; \
		fi; \
	done; \
	echo ""; \
	if [ "$$missing" -gt 0 ]; then \
		echo "$$missing file(s) missing. These must be obtained manually:"; \
		echo "  - ZHVI:         Download from https://www.zillow.com/research/data/"; \
		echo "  - NFIP:         Download from https://www.fema.gov/about/openfema/data-sets"; \
		echo "  - ZCTA:         Download from https://www.census.gov/cgi-bin/geo/shapefiles/"; \
		echo "  - uszips.csv:   Download from https://simplemaps.com/data/us-zips"; \
		echo "  - NOAA:         Download from https://coast.noaa.gov/htdata/SocioEconomic/"; \
		echo "  - Disclosure:   Hand-coded CSV in data/raw/state-disclosure-laws/"; \
		exit 1; \
	else \
		echo "All required files present."; \
	fi


# ==============================================================================
# CLEAN & PROCESS TARGETS
# ==============================================================================

# --- Step 1: Clean Coastal Counties ---
# Outputs: coastal_zipcodes.csv, .geojson, noaa-coastal-counties.geojson
$(COASTAL_SENTINEL): $(SCRIPTS)/clean_coastal_counties.py \
                     $(NOAA_COUNTIES) $(USZIPS_CSV) $(ZCTA_SHP) $(CENSUS_POP)
	$(PYTHON) $< --threshold $(THRESHOLD)
	touch $@

# --- Step 2: Clean Election Returns ---
$(ELECTION_CLEAN): $(SCRIPTS)/clean_election_returns.py $(ELECTION_RAW)
	$(PYTHON) $<

# --- Step 3: Overlay LOMRs onto ZCTAs ---
# Outputs: lomr_zcta_overlay.csv, coastal_zipcodes_lomr_tr_*.csv
$(OVERLAY_SENTINEL): $(SCRIPTS)/overlay_lomr_zcta.py \
                     $(COASTAL_SENTINEL) $(LOMR_GPKG) $(ZCTA_SHP) \
                     $(USZIPS_CSV) $(CENSUS_POP)
	$(PYTHON) $< --threshold $(THRESHOLD) --start-year $(START_YEAR) --end-year $(END_YEAR)
	touch $@

# --- Step 4: Aggregate NFIP Policies/Claims ---
# Outputs: nfip_zip_month_panel.csv, nfip_lomr_deltas.csv
$(NFIP_SENTINEL): $(SCRIPTS)/aggregate_nfip_policies.py \
                  $(OVERLAY_SENTINEL) $(NFIP_POLICIES) $(NFIP_CLAIMS) \
                  $(COASTAL_SENTINEL)
	$(PYTHON) $< --threshold $(THRESHOLD) --start-year $(START_YEAR) --end-year $(END_YEAR)
	touch $@

# --- Step 5: Build Regression Panel ---
$(REGRESSION_PANEL): $(SCRIPTS)/compute_summary_stats.py \
                     $(NFIP_SENTINEL) $(ZHVI_CSV) $(BLS_DATA) $(OVERLAY_SENTINEL)
	$(PYTHON) $< --save-panel --threshold $(THRESHOLD) \
		--start-year $(START_YEAR) --end-year $(END_YEAR)


# ==============================================================================
# ESTIMATION (Stata — opt-in)
# ==============================================================================

estimate: $(REGRESSION_PANEL) $(ELECTION_CLEAN) ## Run Stata event study (requires Stata on PATH)
	@command -v $(STATA) >/dev/null 2>&1 || \
		{ echo "ERROR: $(STATA) not found on PATH. Install Stata or set STATA=/path/to/stata"; exit 1; }
	cd $(OUTPUT) && $(STATA) -b do ../$(SCRIPTS)/event_study.do


# ==============================================================================
# WEBSITE OUTPUTS
# ==============================================================================

website: $(WEBSITE_DATA)/.export.done $(WEBSITE_DATA)/coastal_zips.json ## Build website data exports

$(WEBSITE_DATA)/.export.done: $(SCRIPTS)/export_website_data.py
	$(PYTHON) $<
	touch $@

$(WEBSITE_DATA)/coastal_zips.json: $(SCRIPTS)/build_website_topojson.py \
                                    $(REGRESSION_PANEL) $(ZCTA_SHP)
	$(PYTHON) $<


# ==============================================================================
# CLEAN TARGETS
# ==============================================================================

clean: ## Remove processed data (data/clean/) and sentinel files
	rm -rf $(CLEAN)/*
	rm -f $(CLEAN)/.overlay.done $(CLEAN)/.nfip.done
	@echo "Cleaned data/clean/"

clean-downloads: ## Remove downloaded raw data (data/raw/ contents)
	@echo "WARNING: This will delete all raw data in $(RAW)/"
	@echo "  Large files (NFIP ~30 GB) will need to be re-obtained manually."
	@echo "  Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	rm -rf $(RAW)/*
	@echo "Cleaned data/raw/"

distclean: clean clean-downloads ## Remove all data (raw + processed)

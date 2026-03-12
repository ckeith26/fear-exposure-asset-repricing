#!/usr/bin/env bash
#
# Full data pipeline: from raw data → regression_panel.csv for Stata
#
# Usage:
#     bash run_pipeline.sh              # full pipeline (default: 25k threshold, 2009-2022)
#     bash run_pipeline.sh --skip-nfip  # skip NFIP aggregation (uses cached panel)
#
# Steps:
#   0. Download ACS 2007-2011 historical population (if not cached)
#   1. Clean coastal counties & classify treatment/control zips
#   2. Overlay LOMRs onto ZCTAs for treatment timing
#   3. Aggregate NFIP policies/claims to zip × month panel
#   4. Build regression panel (merge ZHVI + treatment + BLS + NFIP + CPI)

set -euo pipefail

# === CONFIGURATION ===
THRESHOLD="25k"
START_YEAR=2009
END_YEAR=2022

# Parse flags
SKIP_NFIP=""
for arg in "$@"; do
    case $arg in
        --skip-nfip) SKIP_NFIP="--skip-panel" ;;
        *) echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

# Activate virtual environment
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
source .venv/bin/activate

echo "============================================================"
echo "FEAR Pipeline — Full Rebuild"
echo "  Threshold:  $THRESHOLD"
echo "  Window:     $START_YEAR-$END_YEAR"
echo "  Skip NFIP:  ${SKIP_NFIP:-no}"
echo "============================================================"
echo ""

# --- Step 0: 2010 Census Population ---
echo ">>> Step 0/4: Download 2010 Decennial Census population"
python src/scripts/download_census_population.py
echo ""

# --- Step 1: Clean Coastal Counties ---
echo ">>> Step 1/4: Clean coastal counties & classify zips"
python src/scripts/clean_coastal_counties.py --threshold "$THRESHOLD"
echo ""

# --- Step 2: LOMR-ZCTA Overlay ---
echo ">>> Step 2/4: Overlay LOMRs onto ZCTAs"
python src/scripts/overlay_lomr_zcta.py \
    --threshold "$THRESHOLD" \
    --start-year "$START_YEAR" \
    --end-year "$END_YEAR"
echo ""

# --- Step 3: NFIP Aggregation ---
echo ">>> Step 3/4: Aggregate NFIP policies/claims"
python src/scripts/aggregate_nfip_policies.py \
    --threshold "$THRESHOLD" \
    --start-year "$START_YEAR" \
    --end-year "$END_YEAR" \
    $SKIP_NFIP
echo ""

# --- Step 4: Build Regression Panel ---
echo ">>> Step 4/4: Build regression panel"
python src/scripts/compute_summary_stats.py \
    --threshold "$THRESHOLD" \
    --start-year "$START_YEAR" \
    --end-year "$END_YEAR" \
    --save-panel
echo ""

echo "============================================================"
echo "Pipeline complete."
echo "  Regression panel: data/clean/regression_panel.csv"
echo "  Summary stats:    data/clean/summary_statistics.csv"
echo "  Ready for Stata:  src/scripts/event_study.do"
echo "============================================================"

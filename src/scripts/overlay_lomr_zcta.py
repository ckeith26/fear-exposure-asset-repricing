"""
Spatially overlay FEMA LOMR polygons onto ZCTA boundaries for DiD treatment timing.

Inputs:
    data/clean/coastal-counties/coastal_zipcodes.csv   (zip universe from clean script)
    data/raw/FEMA/lomr/s_lomr_national.gpkg            (LOMR polygons, EPSG:4326)
    data/raw/tiger-census/tl_2025_us_zcta520.shp       (ZCTA boundaries, EPSG:4269)

Outputs:
    data/clean/lomr_zcta_overlay.csv                        (one row per LOMR-zip pair)
    data/clean/coastal_zipcodes_lomr_tr_{label}.csv          (one row per zip, with treatment vars)

Usage:
    python src/scripts/overlay_lomr_zcta.py
    python src/scripts/overlay_lomr_zcta.py --threshold 25k
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict

import geopandas as gpd
import pandas as pd

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")

# Inputs
COASTAL_ZIPS_PATH = os.path.join(PROJECT_ROOT, "data", "clean", "coastal-counties", "coastal_zipcodes.csv")
LOMR_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "FEMA", "lomr", "s_lomr_national.gpkg")
ZCTA_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "tiger-census", "tl_2025_us_zcta520.shp")
RAW_ZIPS_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "us-zips", "uszips.csv")
CENSUS_POP_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "census-2010", "census_2010_zcta_population.csv")

# Outputs
CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "clean")
OVERLAY_PATH = os.path.join(CLEAN_DIR, "lomr_zcta_overlay.csv")
# Treatment CSV path uses threshold label, set in main()


# ==============================================================================
# POPULATION FILTER (same logic as clean_coastal_counties.py)
# ==============================================================================

def load_census_population(census_path):
    """
    Load 2010 Census historical population by ZCTA.

    Returns dict: zip_code → {"population": int, "density": float or None}.
    """
    if not os.path.exists(census_path):
        print(f"  WARNING: ACS population file not found: {census_path}")
        print("  Run: python src/scripts/download_census_population.py")
        return None

    lookup = {}
    with open(census_path, newline="") as f:
        for row in csv.DictReader(f):
            z = row.get("zip", "").strip()
            pop = row.get("population", "")
            density = row.get("density", "")
            if z and pop:
                try:
                    entry = {"population": int(float(pop))}
                    entry["density"] = float(density) if density else None
                    lookup[z] = entry
                except ValueError:
                    pass

    print(f"  Loaded ACS population for {len(lookup):,} ZCTAs from: {census_path}")
    return lookup


def filter_by_county_population(zip_df, zips_path, census_lookup, threshold):
    """
    Filter zip DataFrame to only those in counties above the population threshold.

    Uses 2010 Census population when available, with uszips.csv county_fips
    crosswalk for zip-to-county mapping. Falls back to SimpleMaps population
    for zips missing from ACS.
    """
    if threshold <= 0:
        return zip_df

    print(f"\nApplying county population filter (>= {threshold:,}) ...")

    county_pop = defaultdict(int)
    with open(zips_path, newline="") as f:
        for row in csv.DictReader(f):
            fips = row.get("county_fips", "").strip()
            z = row.get("zip", "").strip()
            if not fips:
                continue
            if census_lookup and z in census_lookup:
                county_pop[fips] += census_lookup[z]["population"]
            else:
                pop = row.get("population", "")
                if pop:
                    try:
                        county_pop[fips] += int(float(pop))
                    except ValueError:
                        pass

    before = len(zip_df)
    mask = zip_df["county_fips"].map(lambda fips: county_pop.get(str(fips).strip(), 0) >= threshold)
    zip_df = zip_df[mask].copy()

    print(f"  Before: {before:,} zips")
    print(f"  After:  {len(zip_df):,} zips")
    print(f"  Dropped: {before - len(zip_df):,} zips in counties < {threshold:,} pop")

    return zip_df


def threshold_label(threshold):
    """Convert threshold int to filename label: 0 -> 'full', 25000 -> '25k', etc."""
    if threshold <= 0:
        return "full"
    if threshold % 1000 == 0:
        return f"{threshold // 1000}k"
    return str(threshold)


# ==============================================================================
# LOAD LOMR
# ==============================================================================

def load_lomr(path):
    """
    Load LOMR polygons from GeoPackage, filter to Effective status.

    Converts EFF_DATE from epoch milliseconds to datetime, extracts county_fips
    from DFIRM_ID (first 5 chars), and fixes invalid geometries with buffer(0).
    """
    print(f"\nLoading LOMR polygons from: {path}")

    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    lomr = gpd.read_file(path)
    print(f"  Loaded {len(lomr):,} total LOMR polygons (CRS: {lomr.crs})")

    # Filter to Effective only
    lomr = lomr[lomr["STATUS"] == "Effective"].copy()
    print(f"  Filtered to {len(lomr):,} Effective LOMRs")

    # Convert EFF_DATE from epoch milliseconds to datetime
    lomr["eff_date"] = pd.to_datetime(lomr["EFF_DATE"], unit="ms")
    print(f"  Date range: {lomr['eff_date'].min().date()} to {lomr['eff_date'].max().date()}")

    # Extract county_fips from DFIRM_ID (e.g. "12086C" -> "12086")
    lomr["county_fips"] = lomr["DFIRM_ID"].str[:5]

    # Fix invalid geometries
    n_invalid = (~lomr.geometry.is_valid).sum()
    if n_invalid > 0:
        print(f"  Fixing {n_invalid} invalid geometries with buffer(0)")
        lomr["geometry"] = lomr.geometry.buffer(0)
        # Log and drop any that remain invalid
        still_invalid_mask = ~lomr.geometry.is_valid
        still_invalid = still_invalid_mask.sum()
        if still_invalid > 0:
            dropped = lomr[still_invalid_mask][["LOMR_ID", "CASE_NO", "DFIRM_ID", "eff_date", "county_fips"]].copy()
            log_path = os.path.join(CLEAN_DIR, "lomr_dropped_invalid_geom.csv")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            dropped.to_csv(log_path, index=False)
            print(f"  Dropping {still_invalid} geometries that remain invalid")
            print(f"  Logged dropped LOMRs to: {log_path}")
            lomr = lomr[~still_invalid_mask].copy()

    return lomr


# ==============================================================================
# LOAD COASTAL ZCTA
# ==============================================================================

def load_coastal_zcta(zcta_path, coastal_zips):
    """
    Load ZCTA shapefile, filter to coastal zip set, reproject to EPSG:4326.

    The TIGER/Line ZCTA shapefile uses EPSG:4269 (NAD83). We reproject to
    EPSG:4326 (WGS84) to match the LOMR layer and project convention.
    """
    print(f"\nLoading ZCTA boundaries from: {zcta_path}")

    if not os.path.exists(zcta_path):
        print(f"ERROR: File not found: {zcta_path}")
        sys.exit(1)

    zcta = gpd.read_file(zcta_path)
    print(f"  Loaded {len(zcta):,} total ZCTAs (CRS: {zcta.crs})")

    # Filter to coastal zips only
    zcta = zcta[zcta["ZCTA5CE20"].isin(coastal_zips)].copy()
    print(f"  Filtered to {len(zcta):,} coastal ZCTAs")

    n_missing = len(coastal_zips) - len(zcta)
    if n_missing > 0:
        print(f"  ({n_missing} coastal zips without ZCTA match)")

    # Reproject to EPSG:4326
    if zcta.crs and zcta.crs.to_epsg() != 4326:
        zcta = zcta.to_crs("EPSG:4326")
        print(f"  Reprojected to EPSG:4326")

    # Fix invalid geometries
    n_invalid = (~zcta.geometry.is_valid).sum()
    if n_invalid > 0:
        print(f"  Fixing {n_invalid} invalid ZCTA geometries with buffer(0)")
        zcta["geometry"] = zcta.geometry.buffer(0)

    return zcta


# ==============================================================================
# SPATIAL OVERLAY
# ==============================================================================

def overlay(lomr, zcta):
    """
    Spatial join + intersection: find all LOMR-zip pairs and compute overlap area.

    Uses sjoin for fast matching, then gpd.overlay (intersection) to compute the
    actual overlap area for treatment intensity = LOMR_area_in_zip / ZCTA_area.
    Areas computed in ESRI:102003 (Albers Equal Area) for accuracy.
    """
    print(f"\nRunning spatial overlay ({len(lomr):,} LOMRs x {len(zcta):,} ZCTAs) ...")

    # --- Step 1: sjoin for LOMR-zip pairs ---
    joined = gpd.sjoin(lomr, zcta, how="inner", predicate="intersects")
    print(f"  Raw join result: {len(joined):,} LOMR-zip pairs")

    # Deduplicate: same LOMR_ID + zip should appear only once
    joined["zip"] = joined["ZCTA5CE20"]
    dedup_cols = ["LOMR_ID", "zip"]
    before = len(joined)
    joined = joined.drop_duplicates(subset=dedup_cols)
    n_dupes = before - len(joined)
    if n_dupes > 0:
        print(f"  Removed {n_dupes} duplicate LOMR-zip pairs")

    print(f"  Final overlay: {len(joined):,} unique LOMR-zip pairs")

    # Select output columns (non-spatial)
    overlay_df = joined[["zip", "LOMR_ID", "CASE_NO", "eff_date", "DFIRM_ID", "county_fips"]].copy()
    overlay_df = overlay_df.sort_values(["zip", "eff_date"]).reset_index(drop=True)

    # --- Step 2: Compute treatment intensity (overlap area / ZCTA area) ---
    print(f"\n  Computing treatment intensity (overlap areas) ...")

    # Reproject to equal-area CRS for accurate area calculation
    albers = "ESRI:102003"
    lomr_ea = lomr.to_crs(albers)
    zcta_ea = zcta.to_crs(albers)

    # Compute ZCTA total area (sq meters)
    zcta_ea["zcta_area_m2"] = zcta_ea.geometry.area
    zcta_areas = zcta_ea.set_index("ZCTA5CE20")["zcta_area_m2"]

    # Compute intersection polygons (LOMR ∩ ZCTA)
    print(f"    Running polygon intersection (this may take a few minutes) ...")
    intersection = gpd.overlay(lomr_ea, zcta_ea, how="intersection", keep_geom_type=True)
    intersection["overlap_area_m2"] = intersection.geometry.area
    intersection["zip"] = intersection["ZCTA5CE20"]
    print(f"    Intersection result: {len(intersection):,} polygons")

    # Aggregate overlap area per zip (sum across all LOMRs in each zip)
    zip_overlap = intersection.groupby("zip")["overlap_area_m2"].sum().reset_index()
    zip_overlap.columns = ["zip", "lomr_overlap_m2"]

    # Join ZCTA area and compute intensity
    zip_overlap["zcta_area_m2"] = zip_overlap["zip"].map(zcta_areas)
    zip_overlap["treatment_intensity"] = (
        zip_overlap["lomr_overlap_m2"] / zip_overlap["zcta_area_m2"]
    ).clip(upper=1.0)  # cap at 1.0 in case of geometry quirks

    print(f"    Treatment intensity computed for {len(zip_overlap):,} zips")
    print(f"    Mean: {zip_overlap['treatment_intensity'].mean():.4f}")
    print(f"    Median: {zip_overlap['treatment_intensity'].median():.4f}")
    print(f"    Max: {zip_overlap['treatment_intensity'].max():.4f}")

    return overlay_df, zip_overlap


# ==============================================================================
# AGGREGATE TO ZIP
# ==============================================================================

def aggregate_to_zip(overlay_df, zip_overlap, start_year=None, end_year=None):
    """
    Aggregate LOMR overlay to one row per zip with treatment timing variables.

    When start_year/end_year are set, computes window-aware columns:
      - n_lomrs, first_lomr_date, last_lomr_date: from ALL LOMRs
      - ever_treated: 1 if any LOMR at all
      - already_treated: 1 if first LOMR is BEFORE start_year (pre-window treatment)
      - treated_in_window: 1 if first LOMR falls within [start_year, end_year]
      - treatment_intensity: LOMR overlap area / ZCTA area (0-1)
    """
    print(f"\nAggregating to zip level ...")

    agg = overlay_df.groupby("zip").agg(
        n_lomrs=("LOMR_ID", "count"),
        first_lomr_date=("eff_date", "min"),
        last_lomr_date=("eff_date", "max"),
    ).reset_index()
    agg["ever_treated"] = 1

    # Merge treatment intensity
    agg = agg.merge(zip_overlap[["zip", "treatment_intensity"]], on="zip", how="left")
    agg["treatment_intensity"] = agg["treatment_intensity"].fillna(0)

    if start_year or end_year:
        first_dates = pd.to_datetime(agg["first_lomr_date"])

        # already_treated: first LOMR before the analysis window
        if start_year:
            agg["already_treated"] = (first_dates.dt.year < start_year).astype(int)
            n_already = agg["already_treated"].sum()
            print(f"  {n_already:,} zips already treated before {start_year}")

        # treated_in_window: first LOMR within [start_year, end_year]
        in_window = pd.Series(True, index=agg.index)
        if start_year:
            in_window &= first_dates.dt.year >= start_year
        if end_year:
            in_window &= first_dates.dt.year <= end_year
        agg["treated_in_window"] = in_window.astype(int)

        n_in_window = agg["treated_in_window"].sum()
        print(f"  {n_in_window:,} zips first treated within analysis window")

    print(f"  {len(agg):,} zips with at least one LOMR")

    return agg


# ==============================================================================
# MERGE AND SAVE
# ==============================================================================

def merge_and_save(coastal_df, zip_agg, overlay_df, treatment_path, overlay_path):
    """
    Left-join all coastal zips with LOMR treatment info.

    Zips without any LOMR get n_lomrs=0, ever_treated=0, dates=NaT.
    """
    print(f"\nMerging treatment info onto coastal zips ...")

    # Ensure zip columns are strings for join
    coastal_df["zip"] = coastal_df["zip"].astype(str)
    zip_agg["zip"] = zip_agg["zip"].astype(str)

    merged = coastal_df.merge(zip_agg, on="zip", how="left")

    # Fill controls
    merged["n_lomrs"] = merged["n_lomrs"].fillna(0).astype(int)
    merged["ever_treated"] = merged["ever_treated"].fillna(0).astype(int)
    merged["treatment_intensity"] = merged["treatment_intensity"].fillna(0)
    for col in ["already_treated", "treated_in_window"]:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0).astype(int)

    # Save overlay CSV
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    overlay_df.to_csv(overlay_path, index=False)
    size_mb = os.path.getsize(overlay_path) / 1e6
    print(f"  Saved overlay: {overlay_path} ({size_mb:.2f} MB, {len(overlay_df):,} rows)")

    # Save treatment CSV
    merged.to_csv(treatment_path, index=False)
    size_mb = os.path.getsize(treatment_path) / 1e6
    print(f"  Saved treatment: {treatment_path} ({size_mb:.2f} MB, {len(merged):,} rows)")

    return merged


# ==============================================================================
# SUMMARY
# ==============================================================================

def print_summary(merged, overlay_df):
    """Print summary statistics for verification."""

    n_treated = (merged["ever_treated"] == 1).sum()
    n_control = (merged["ever_treated"] == 0).sum()

    print(f"\n{'=' * 60}")
    print(f"LOMR-ZCTA OVERLAY SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total coastal zips:    {len(merged):,}")
    print(f"  Treated (any LOMR):    {n_treated:,}")
    print(f"  Control (no LOMR):     {n_control:,}")
    if "already_treated" in merged.columns:
        n_already = (merged["already_treated"] == 1).sum()
        n_in_window = (merged["treated_in_window"] == 1).sum()
        print(f"    Already treated (pre-window): {n_already:,}")
        print(f"    Treated in window:            {n_in_window:,}")
        print(f"    Never treated (control):      {n_control:,}")
    print(f"  LOMR-zip pairs:        {len(overlay_df):,}")
    print(f"  Unique LOMRs matched:  {overlay_df['LOMR_ID'].nunique():,}")

    # Date distribution
    treated = merged[merged["ever_treated"] == 1]
    if len(treated) > 0:
        print(f"\n  First LOMR date range:")
        print(f"    Earliest: {treated['first_lomr_date'].min()}")
        print(f"    Latest:   {treated['first_lomr_date'].max()}")

        # LOMRs per zip distribution
        print(f"\n  LOMRs per treated zip:")
        print(f"    Mean:   {treated['n_lomrs'].mean():.1f}")
        print(f"    Median: {treated['n_lomrs'].median():.0f}")
        print(f"    Max:    {treated['n_lomrs'].max()}")

        # Treatment intensity distribution
        ti = treated["treatment_intensity"]
        print(f"\n  Treatment intensity (LOMR area / ZCTA area):")
        print(f"    Mean:   {ti.mean():.4f}")
        print(f"    Median: {ti.median():.4f}")
        print(f"    P75:    {ti.quantile(0.75):.4f}")
        print(f"    P90:    {ti.quantile(0.90):.4f}")
        print(f"    Max:    {ti.max():.4f}")

    # Year distribution of first_lomr_date
    if len(treated) > 0:
        years = pd.to_datetime(treated["first_lomr_date"]).dt.year
        year_counts = years.value_counts().sort_index()
        print(f"\n  First LOMR date by year (top 10):")
        for year, count in year_counts.head(10).items():
            print(f"    {year}: {count:,} zips")

    # Top states by treated zips
    if len(treated) > 0:
        state_counts = treated["state_id"].value_counts()
        print(f"\n  Top 10 states by treated zips:")
        for state, count in state_counts.head(10).items():
            print(f"    {state}: {count:,}")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Spatially overlay FEMA LOMR polygons onto ZCTA boundaries for DiD treatment timing"
    )
    parser.add_argument(
        "--threshold", type=str, default="full",
        help="Min county population threshold: 'full' (no filter), '10k', '25k', '50k', or a number"
    )
    parser.add_argument(
        "--start-year", type=int, default=None,
        help="Start of analysis window (e.g. 2009). LOMRs before this year flag zips as already_treated."
    )
    parser.add_argument(
        "--end-year", type=int, default=None,
        help="End of analysis window (e.g. 2022). LOMRs after this year are excluded."
    )
    args = parser.parse_args()

    # Parse threshold value
    thresh_str = args.threshold.lower().strip()
    if thresh_str == "full":
        pop_threshold = 0
    elif thresh_str.endswith("k"):
        pop_threshold = int(thresh_str[:-1]) * 1000
    else:
        pop_threshold = int(thresh_str)

    label = threshold_label(pop_threshold)
    start_year = args.start_year
    end_year = args.end_year

    # Build output filename with window suffix
    window_suffix = ""
    if start_year or end_year:
        window_suffix = f"_{start_year or 'x'}-{end_year or 'x'}"
    treatment_path = os.path.join(CLEAN_DIR, f"coastal_zipcodes_lomr_tr_{label}{window_suffix}.csv")

    print("LOMR-ZCTA Spatial Overlay")
    print(f"Population threshold: {label} ({pop_threshold:,})")
    if start_year or end_year:
        print(f"Analysis window: {start_year or '...'}-{end_year or '...'}")
    print("=" * 60)

    # 1. Load coastal zip universe
    print(f"\nLoading coastal zips from: {COASTAL_ZIPS_PATH}")
    if not os.path.exists(COASTAL_ZIPS_PATH):
        print(f"ERROR: File not found: {COASTAL_ZIPS_PATH}")
        sys.exit(1)
    coastal_df = pd.read_csv(COASTAL_ZIPS_PATH, dtype={"zip": str, "county_fips": str})
    print(f"  Loaded {len(coastal_df):,} coastal zips")

    # 1b. Load 2010 Census historical population
    print("\nLoading 2010 Census historical population ...")
    census_lookup = load_census_population(CENSUS_POP_PATH)

    # 2. Apply population filter
    coastal_df = filter_by_county_population(coastal_df, RAW_ZIPS_PATH, census_lookup, pop_threshold)
    coastal_zip_set = set(coastal_df["zip"])

    # 3. Load LOMR polygons
    lomr = load_lomr(LOMR_PATH)

    # 4. Load ZCTA boundaries (filtered to coastal zips)
    zcta = load_coastal_zcta(ZCTA_PATH, coastal_zip_set)

    # 5. Spatial overlay + treatment intensity
    overlay_df, zip_overlap = overlay(lomr, zcta)

    # 6. Aggregate to zip level
    zip_agg = aggregate_to_zip(overlay_df, zip_overlap, start_year=start_year, end_year=end_year)

    # 7. Merge and save
    merged = merge_and_save(coastal_df, zip_agg, overlay_df, treatment_path, OVERLAY_PATH)

    # 8. Summary
    print_summary(merged, overlay_df)

    print(f"\nDone. Outputs:")
    print(f"  {OVERLAY_PATH}")
    print(f"  {treatment_path}")

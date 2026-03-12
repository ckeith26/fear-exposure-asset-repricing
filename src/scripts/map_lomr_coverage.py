"""
Map S_LOMR attributes to US county boundaries for geographic coverage visualization.

Inputs:
    data/raw/fema/lomr/s_lomr_attributes.csv

Outputs:
    data/clean/fema/lomr/lomr_county_coverage.geojson  (county polygons with LOMR counts)

Steps:
    1. Extracts county FIPS from DFIRM_ID (first 5 characters)
    2. Aggregates LOMR counts, date ranges, and status breakdown per county
    3. Downloads Census TIGER/Line county boundaries (cached locally)
    4. Joins aggregated LOMR stats to county polygons
    5. Exports GeoJSON for visualization (e.g., in QGIS, kepler.gl, mapshaper)

Usage:
    python src/scripts/map_lomr_coverage.py
"""

import os
import tempfile
import zipfile

import geopandas as gpd
import pandas as pd
import requests

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")

LOMR_CSV = os.path.join(PROJECT_ROOT, "data", "raw", "fema", "lomr", "s_lomr_attributes.csv")
COUNTY_SHP_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "tiger-census")
COUNTY_SHP_ZIP = os.path.join(COUNTY_SHP_DIR, "tl_2020_us_county.zip")
COUNTY_SHP_FILE = os.path.join(COUNTY_SHP_DIR, "tl_2020_us_county.shp")

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "clean", "fema", "lomr")
OUTPUT_GEOJSON = os.path.join(OUTPUT_DIR, "lomr_county_coverage.geojson")

# Census TIGER/Line county boundaries (2020 vintage, matches FIPS codes in DFIRM_ID)
COUNTY_SHP_URL = "https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/tl_2020_us_county.zip"

# Exclude US territories
TERRITORY_FIPS = {"60", "66", "69", "72", "78"}

# ==============================================================================
# STEP 1: Load and aggregate LOMR attributes
# ==============================================================================

def load_and_aggregate_lomrs():
    """Read LOMR CSV, extract county FIPS, aggregate stats per county."""
    print("=" * 60)
    print("STEP 1: Loading LOMR attributes...")
    print("=" * 60)

    df = pd.read_csv(LOMR_CSV)
    print(f"  Loaded {len(df):,} LOMR records")

    # Extract county FIPS from DFIRM_ID (first 5 chars = state + county FIPS)
    df["county_fips"] = df["DFIRM_ID"].str[:5]
    df["state_fips"] = df["DFIRM_ID"].str[:2]

    # Parse effective dates (stored as epoch milliseconds)
    df["eff_date"] = pd.to_datetime(df["EFF_DATE"], unit="ms", errors="coerce")

    # Filter to US states + DC only
    df = df[~df["state_fips"].isin(TERRITORY_FIPS)]
    print(f"  After excluding territories: {len(df):,} records")

    # Aggregate by county
    agg = df.groupby("county_fips").agg(
        lomr_count=("OBJECTID", "count"),
        earliest_lomr=("eff_date", "min"),
        latest_lomr=("eff_date", "max"),
        effective_count=("STATUS", lambda x: (x == "Effective").sum()),
        superseded_count=("STATUS", lambda x: x.isin(["Superseded", "Superceded"]).sum()),
        unique_cases=("CASE_NO", "nunique"),
    ).reset_index()

    # Format dates as strings for GeoJSON compatibility
    agg["earliest_lomr"] = agg["earliest_lomr"].dt.strftime("%Y-%m-%d")
    agg["latest_lomr"] = agg["latest_lomr"].dt.strftime("%Y-%m-%d")

    print(f"  Aggregated to {len(agg):,} counties with LOMR activity")
    print(f"  LOMR count range: {agg['lomr_count'].min()} - {agg['lomr_count'].max()}")

    return agg


# ==============================================================================
# STEP 2: Download county boundaries
# ==============================================================================

def download_county_boundaries():
    """Download Census TIGER/Line county shapefile if not cached."""
    print("\n" + "=" * 60)
    print("STEP 2: Loading county boundaries...")
    print("=" * 60)

    if os.path.exists(COUNTY_SHP_FILE):
        print(f"  Using cached shapefile: {COUNTY_SHP_FILE}")
    else:
        print(f"  Downloading county boundaries from Census...")
        os.makedirs(COUNTY_SHP_DIR, exist_ok=True)

        r = requests.get(COUNTY_SHP_URL, timeout=120, stream=True)
        r.raise_for_status()

        with open(COUNTY_SHP_ZIP, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  Downloaded: {os.path.getsize(COUNTY_SHP_ZIP) / 1e6:.1f} MB")

        with zipfile.ZipFile(COUNTY_SHP_ZIP, "r") as zf:
            zf.extractall(COUNTY_SHP_DIR)
        print(f"  Extracted to {COUNTY_SHP_DIR}")

    counties = gpd.read_file(COUNTY_SHP_FILE)
    print(f"  Loaded {len(counties):,} county polygons")

    # Detect column naming convention (some vintages use '20' suffix, others don't)
    statefp_col = "STATEFP20" if "STATEFP20" in counties.columns else "STATEFP"
    geoid_col = "GEOID20" if "GEOID20" in counties.columns else "GEOID"
    name_col = "NAME20" if "NAME20" in counties.columns else "NAME"

    # Filter to US states + DC
    counties = counties[~counties[statefp_col].isin(TERRITORY_FIPS)]
    print(f"  After excluding territories: {len(counties):,} counties")

    # Keep only needed columns
    counties = counties[[geoid_col, name_col, statefp_col, "geometry"]]
    counties = counties.rename(columns={geoid_col: "county_fips", name_col: "county_name", statefp_col: "state_fips"})

    return counties


# ==============================================================================
# STEP 3: Join and export
# ==============================================================================

def join_and_export(lomr_agg, counties):
    """Join LOMR aggregates to county polygons and export GeoJSON."""
    print("\n" + "=" * 60)
    print("STEP 3: Joining LOMR data to county boundaries...")
    print("=" * 60)

    merged = counties.merge(lomr_agg, on="county_fips", how="left")

    # Fill counties with no LOMRs
    merged["lomr_count"] = merged["lomr_count"].fillna(0).astype(int)
    merged["effective_count"] = merged["effective_count"].fillna(0).astype(int)
    merged["superseded_count"] = merged["superseded_count"].fillna(0).astype(int)
    merged["unique_cases"] = merged["unique_cases"].fillna(0).astype(int)

    counties_with = (merged["lomr_count"] > 0).sum()
    counties_without = (merged["lomr_count"] == 0).sum()
    print(f"  Counties with LOMR activity: {counties_with:,}")
    print(f"  Counties without: {counties_without:,}")

    # Ensure WGS84 for GeoJSON
    merged = merged.to_crs("EPSG:4326")

    # Simplify geometries to reduce file size (~200 MB → ~15 MB)
    # Tolerance 0.005 degrees ≈ 500m — fine for county-level choropleth
    merged["geometry"] = merged["geometry"].simplify(tolerance=0.005, preserve_topology=True)
    print(f"  Simplified geometries (tolerance=0.005°)")

    # Export
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    merged.to_file(OUTPUT_GEOJSON, driver="GeoJSON")
    size_mb = os.path.getsize(OUTPUT_GEOJSON) / 1e6
    print(f"\n  Saved: {OUTPUT_GEOJSON}")
    print(f"  Size: {size_mb:.1f} MB")

    return merged


# ==============================================================================
# STEP 4: Summary
# ==============================================================================

def print_summary(merged):
    """Print top counties and state-level summary."""
    print("\n" + "=" * 60)
    print("STEP 4: Coverage summary")
    print("=" * 60)

    # Top 15 counties by LOMR count
    top = merged.nlargest(15, "lomr_count")[["county_name", "state_fips", "county_fips", "lomr_count"]]
    print("\nTop 15 counties by LOMR count:")
    for _, row in top.iterrows():
        print(f"  {row['county_name']:25s} (FIPS {row['county_fips']}): {row['lomr_count']:,} LOMRs")

    # State-level totals
    state_totals = merged.groupby("state_fips")["lomr_count"].sum().sort_values(ascending=False)
    print(f"\nTop 10 states by total LOMRs:")
    for fips, count in state_totals.head(10).items():
        print(f"  State FIPS {fips}: {count:,}")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print("LOMR Geographic Coverage Mapping")
    print("=" * 60)

    lomr_agg = load_and_aggregate_lomrs()
    counties = download_county_boundaries()
    merged = join_and_export(lomr_agg, counties)
    print_summary(merged)

    print("\n" + "=" * 60)
    print("DONE!")
    print(f"  Output: {OUTPUT_GEOJSON}")
    print("  Open in QGIS, kepler.gl, or mapshaper.org to visualize")
    print("  Color by 'lomr_count' for coverage heatmap")
    print("=" * 60)

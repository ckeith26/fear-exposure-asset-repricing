"""
Download S_LOMR (Letter of Map Revision) data from FEMA's National Flood Hazard Layer
via the ArcGIS REST API, and perform initial exploratory analysis.

Requirements:
    pip install requests geopandas pandas matplotlib

Usage:
    python download_FEMA.py              # download all records (prompts first)
    python download_FEMA.py --limit 500  # download only 500 records

This script:
    1. Queries FEMA's NFHL MapServer Layer 1 (LOMRs) via REST API
    2. Paginates through all records nationally
    3. Saves the full dataset as a GeoPackage
    4. Produces summary statistics to assess feasibility for DiD/event study design
"""

import argparse
import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
import json
import time
import os

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# FEMA NFHL MapServer - Layer 1 is "LOMRs" (S_LOMR polygons)
BASE_URL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/1"

# Output paths
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "FEMA", "lomr")
OUTPUT_GPKG = os.path.join(OUTPUT_DIR, "s_lomr_national.gpkg")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "s_lomr_attributes.csv")  # attributes only, no geometry

# Pagination settings
# ArcGIS REST APIs typically cap at 1000-2000 features per request
BATCH_SIZE = 1000

# ==============================================================================
# STEP 1: Inspect the layer metadata
# ==============================================================================

def get_layer_info():
    """Fetch layer metadata to understand available fields and record count."""
    print("=" * 60)
    print("STEP 1: Fetching layer metadata...")
    print("=" * 60)
    
    # Get layer info
    params = {"f": "json"}
    r = requests.get(BASE_URL, params=params, timeout=60)
    r.raise_for_status()
    info = r.json()
    
    print(f"\nLayer name: {info.get('name', 'N/A')}")
    print(f"Layer type: {info.get('type', 'N/A')}")
    print(f"Geometry type: {info.get('geometryType', 'N/A')}")
    
    # Print fields
    print(f"\nAvailable fields:")
    fields = info.get("fields", [])
    for f in fields:
        print(f"  - {f['name']:30s} ({f['type']})")
    
    # Check max record count
    max_count = info.get("maxRecordCount", "unknown")
    print(f"\nMax records per query: {max_count}")
    
    return info


def get_total_count():
    """Get total number of S_LOMR features nationally."""
    params = {
        "where": "1=1",          # all records
        "returnCountOnly": "true",
        "f": "json"
    }
    r = requests.get(f"{BASE_URL}/query", params=params, timeout=60)
    r.raise_for_status()
    result = r.json()
    count = result.get("count", 0)
    print(f"\nTotal S_LOMR records nationally: {count:,}")
    return count


# ==============================================================================
# STEP 2: Download all features with pagination
# ==============================================================================

def download_all_features(total_count, limit=None):
    """
    Download S_LOMR features using pagination.
    If limit is set, stops after that many records.
    Returns a GeoDataFrame.
    """
    target = min(total_count, limit) if limit else total_count

    print("\n" + "=" * 60)
    if limit:
        print(f"STEP 2: Downloading {target:,} of {total_count:,} S_LOMR features...")
    else:
        print("STEP 2: Downloading all S_LOMR features...")
    print("=" * 60)

    all_features = []
    offset = 0
    batch_num = 0

    while offset < target:
        batch_num += 1
        print(f"  Batch {batch_num}: records {offset:,} - {min(offset + BATCH_SIZE, target):,} "
              f"({offset/target*100:.0f}% complete)")
        
        params = {
            "where": "1=1",
            "outFields": "*",           # all fields
            "returnGeometry": "true",
            "outSR": "4326",            # WGS84 lat/lon
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": BATCH_SIZE,
        }
        
        # Retry logic for network issues
        for attempt in range(3):
            try:
                r = requests.get(f"{BASE_URL}/query", params=params, timeout=120)
                r.raise_for_status()
                data = r.json()
                break
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                if attempt < 2:
                    print(f"    Retry {attempt + 1} after error: {e}")
                    time.sleep(5 * (attempt + 1))
                else:
                    raise
        
        features = data.get("features", [])
        if not features:
            print("  No more features returned. Done.")
            break
        
        all_features.extend(features)
        offset += BATCH_SIZE
        
        # Be polite to the server
        time.sleep(0.5)
    
    print(f"\n  Downloaded {len(all_features):,} features total.")
    
    # Convert to GeoDataFrame
    if all_features:
        geojson_collection = {
            "type": "FeatureCollection",
            "features": all_features
        }
        gdf = gpd.GeoDataFrame.from_features(geojson_collection, crs="EPSG:4326")
        return gdf
    else:
        print("WARNING: No features downloaded!")
        return gpd.GeoDataFrame()


# ==============================================================================
# STEP 3: Save the data
# ==============================================================================

def save_data(gdf):
    """Save GeoDataFrame to GeoPackage and CSV."""
    print("\n" + "=" * 60)
    print("STEP 3: Saving data...")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Save with geometry
    gdf.to_file(OUTPUT_GPKG, driver="GPKG")
    print(f"  Saved GeoPackage: {OUTPUT_GPKG} ({os.path.getsize(OUTPUT_GPKG) / 1e6:.1f} MB)")
    
    # Save attributes only (easier to work with in Stata later)
    df = gdf.drop(columns="geometry")
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"  Saved CSV:        {OUTPUT_CSV}")


# ==============================================================================
# STEP 4: Exploratory analysis for research feasibility
# ==============================================================================

def explore_data(gdf):
    """
    Produce summary statistics critical for assessing whether this
    DiD/event study design is feasible.
    """
    print("\n" + "=" * 60)
    print("STEP 4: Exploratory analysis")
    print("=" * 60)
    
    print(f"\nTotal records: {len(gdf):,}")
    print(f"\nColumn names:\n  {list(gdf.columns)}")
    
    # --- Effective dates ---
    # S_LOMR typically has EFF_DATE or similar date field
    # Let's find date columns
    date_cols = [c for c in gdf.columns if 'DATE' in c.upper() or 'EFF' in c.upper()]
    print(f"\nDate-related columns: {date_cols}")
    
    for col in date_cols:
        print(f"\n  {col}:")
        print(f"    Sample values: {gdf[col].dropna().head(5).tolist()}")
        
        # Try to parse dates
        try:
            dates = pd.to_datetime(gdf[col], errors='coerce')
            valid = dates.dropna()
            if len(valid) > 0:
                print(f"    Earliest: {valid.min()}")
                print(f"    Latest:   {valid.max()}")
                print(f"    Non-null: {len(valid):,} / {len(gdf):,}")
                
                # Distribution by year
                year_counts = valid.dt.year.value_counts().sort_index()
                print(f"\n    LOMRs by year:")
                for year, count in year_counts.items():
                    bar = "█" * (count // max(1, max(year_counts) // 40))
                    print(f"      {int(year)}: {count:5d}  {bar}")
        except Exception as e:
            print(f"    Could not parse as dates: {e}")
    
    # --- Geographic distribution ---
    # DFIRM_ID typically encodes state + county FIPS
    fips_cols = [c for c in gdf.columns if 'DFIRM' in c.upper() or 'FIPS' in c.upper() 
                 or 'STATE' in c.upper() or 'COUNTY' in c.upper()]
    print(f"\nGeographic ID columns: {fips_cols}")
    
    for col in fips_cols:
        if gdf[col].dtype == object:
            nunique = gdf[col].nunique()
            print(f"\n  {col}: {nunique} unique values")
            if nunique <= 60:  # likely state-level
                print(f"    Top 15:")
                for val, cnt in gdf[col].value_counts().head(15).items():
                    print(f"      {val}: {cnt:,}")
    
    # --- Case numbers ---
    case_cols = [c for c in gdf.columns if 'CASE' in c.upper() or 'LOMR' in c.upper()]
    print(f"\nCase-related columns: {case_cols}")
    for col in case_cols:
        print(f"  {col}: {gdf[col].nunique():,} unique values")
    
    # --- Geometry stats ---
    print(f"\nGeometry statistics:")
    print(f"  Geometry types: {gdf.geometry.geom_type.value_counts().to_dict()}")
    
    # Area in square km (approximate, since in WGS84)
    # For a rough estimate, reproject to equal area
    try:
        gdf_proj = gdf.to_crs("ESRI:102003")  # USA Contiguous Albers Equal Area
        areas_km2 = gdf_proj.geometry.area / 1e6
        print(f"  Area (km²): min={areas_km2.min():.4f}, "
              f"median={areas_km2.median():.4f}, "
              f"mean={areas_km2.mean():.4f}, "
              f"max={areas_km2.max():.4f}")
    except Exception as e:
        print(f"  Could not compute areas: {e}")
    
    # --- First few records ---
    print(f"\nFirst 3 records (attributes only):")
    print(gdf.drop(columns="geometry").head(3).to_string())


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download FEMA S_LOMR data")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of records to download (default: all)")
    args = parser.parse_args()

    print("FEMA S_LOMR Data Download & Exploration")
    print("For: Flood Risk Capitalization Research Project")
    print("=" * 60)

    # Step 1: Inspect layer
    try:
        info = get_layer_info()
    except Exception as e:
        print(f"\nERROR fetching layer info: {e}")
        print("Check your internet connection and that the FEMA API is accessible.")
        print(f"Try opening this URL in your browser: {BASE_URL}?f=json")
        exit(1)

    # Get count
    total = get_total_count()

    if total == 0:
        print("No records found. Exiting.")
        exit(0)

    download_count = min(total, args.limit) if args.limit else total

    # Confirm before large download
    est_time_min = (download_count / BATCH_SIZE) * 1.5 / 60  # rough estimate
    if args.limit:
        print(f"\nWill download {download_count:,} of {total:,} records (--limit {args.limit})")
    print(f"Estimated download time: ~{max(est_time_min, 1):.0f} minutes")

    proceed = input("Proceed with download? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Aborted. You can rerun to just get the count.")
        exit(0)

    # Step 2: Download
    gdf = download_all_features(total, limit=args.limit)
    
    if gdf.empty:
        print("No data downloaded. Exiting.")
        exit(1)
    
    # Step 3: Save
    save_data(gdf)
    
    # Step 4: Explore
    explore_data(gdf)
    
    print("\n" + "=" * 60)
    print("DONE! Key files:")
    print(f"  {OUTPUT_GPKG}  — full spatial data (use in Python/QGIS)")
    print(f"  {OUTPUT_CSV}          — attributes only (can import to Stata)")
    print("=" * 60)

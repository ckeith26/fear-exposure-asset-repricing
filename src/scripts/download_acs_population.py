"""
Download ACS 2007-2011 5-year population estimates by ZCTA from the Census API,
then compute population density using ZCTA land area from the TIGER/Line shapefile.

Pipeline step: Acquisition (historical pre-treatment population & density)

Why 2007-2011: The earliest ACS 5-year vintage with ZCTA geography available
via the Census API. Centered on ~2009, this provides pre-treatment population
for the DiD design. Using contemporaneous population avoids endogeneity from
post-treatment migration responses to flood risk reclassification.

Note: ACS 2007-2011 exists but lacks ZCTA geography in the API (only available
at county level and above). The 2007-2011 vintage is the earliest with ZCTAs.

Requirements:
    pip install requests geopandas

Usage:
    python src/scripts/download_acs_population.py
    python src/scripts/download_acs_population.py --force   # re-download even if cached

Inputs:
    Census API: ACS 2011 5-year (2007-2011), table B01003 (Total Population) by ZCTA
    data/raw/tiger-census/tl_2025_us_zcta520.shp  (for ALAND20 land area)

Outputs:
    data/raw/census-acs/acs_2007_2011_zcta_population_raw.json  (cached API response)
    data/raw/census-acs/acs_2007_2011_zcta_population.csv       (zip, population, density)
"""

import argparse
import json
import os
import sys

import requests

# ==============================================================================
# CONFIGURATION
# ==============================================================================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Census API endpoint — ACS 2011 5-year (covers 2007-2011), no API key required
# ZCTA geography requires state parameter (wildcard * fetches all states)
ACS_URL = (
    "https://api.census.gov/data/2011/acs/acs5"
    "?get=B01003_001E,NAME"
    "&for=zip%20code%20tabulation%20area:*"
    "&in=state:*"
)

# ZCTA shapefile (for land area → density calculation)
ZCTA_SHP_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "tiger-census", "tl_2025_us_zcta520.shp")

# Output paths
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "census-acs")
RAW_JSON_PATH = os.path.join(OUTPUT_DIR, "acs_2007_2011_zcta_population_raw.json")
OUTPUT_CSV_PATH = os.path.join(OUTPUT_DIR, "acs_2007_2011_zcta_population.csv")

# Conversion: square meters → square miles
SQ_METERS_PER_SQ_MILE = 2_589_988.11


# ==============================================================================
# DOWNLOAD
# ==============================================================================

def download_acs(url, cache_path, force=False):
    """
    Fetch ACS population data from Census API.

    Returns list of [population, name, state, zcta] rows (header row excluded).
    """
    if os.path.exists(cache_path) and not force:
        print(f"  Using cached API response: {cache_path}")
        with open(cache_path) as f:
            data = json.load(f)
        print(f"  {len(data) - 1:,} ZCTAs in cache")
        return data[1:]  # skip header row

    print(f"  Requesting: {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(data, f)

    print(f"  Downloaded {len(data) - 1:,} ZCTAs")
    return data[1:]  # skip header row


# ==============================================================================
# DENSITY COMPUTATION
# ==============================================================================

def load_zcta_areas(shp_path):
    """
    Load ZCTA land areas from the TIGER/Line shapefile.

    Returns dict: zcta_code → land_area_sq_miles.
    """
    import geopandas as gpd

    if not os.path.exists(shp_path):
        print(f"  WARNING: ZCTA shapefile not found: {shp_path}")
        print("  Density will not be computed. Download the shapefile first.")
        return None

    print(f"  Loading ZCTA land areas from: {shp_path}")
    zcta = gpd.read_file(shp_path, columns=["ZCTA5CE20", "ALAND20"])
    areas = {}
    for _, row in zcta.iterrows():
        code = row["ZCTA5CE20"]
        area_m2 = row["ALAND20"]
        if area_m2 and area_m2 > 0:
            areas[code] = area_m2 / SQ_METERS_PER_SQ_MILE
    print(f"  Loaded areas for {len(areas):,} ZCTAs")
    return areas


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Download ACS 2007-2011 ZCTA population")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args()

    print("=" * 60)
    print("ACS 2007-2011 ZCTA Population Download")
    print("=" * 60)

    # 1. Download from Census API
    print("\n1. Downloading ACS 2007-2011 population by ZCTA ...")
    rows = download_acs(ACS_URL, RAW_JSON_PATH, force=args.force)

    # 2. Parse into {zcta: population}
    pop_data = {}
    n_null = 0
    for row in rows:
        # row = [B01003_001E, NAME, state, zcta]
        pop_str, name, state, zcta = row
        if pop_str is None or pop_str == "":
            n_null += 1
            continue
        try:
            pop = int(pop_str)
        except (ValueError, TypeError):
            n_null += 1
            continue
        pop_data[zcta] = pop

    print(f"  Parsed {len(pop_data):,} ZCTAs with valid population ({n_null} null/invalid)")

    # 3. Load ZCTA land areas for density
    print("\n2. Computing density from ZCTA land areas ...")
    areas = load_zcta_areas(ZCTA_SHP_PATH)

    # 4. Write output CSV
    print(f"\n3. Writing output to: {OUTPUT_CSV_PATH}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    n_with_density = 0
    n_without_density = 0

    with open(OUTPUT_CSV_PATH, "w") as f:
        f.write("zip,population,density\n")
        for zcta in sorted(pop_data.keys()):
            pop = pop_data[zcta]
            if areas and zcta in areas and areas[zcta] > 0:
                density = round(pop / areas[zcta], 1)
                n_with_density += 1
            else:
                density = ""
                n_without_density += 1
            f.write(f"{zcta},{pop},{density}\n")

    print(f"  Wrote {len(pop_data):,} rows")
    print(f"  With density: {n_with_density:,}")
    print(f"  Without density (no ZCTA area match): {n_without_density:,}")

    # 5. Summary stats
    pops = list(pop_data.values())
    pops.sort()
    print(f"\n  Population summary:")
    print(f"    Total ZCTAs: {len(pops):,}")
    print(f"    Total pop:   {sum(pops):,}")
    print(f"    Median:      {pops[len(pops)//2]:,}")
    print(f"    Min:         {pops[0]:,}")
    print(f"    Max:         {pops[-1]:,}")

    print("\nDone.")


if __name__ == "__main__":
    main()

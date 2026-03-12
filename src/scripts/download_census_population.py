"""
Download 2010 Decennial Census population by ZCTA from the Census API,
then compute population density using ZCTA land area from the TIGER/Line shapefile.

Pipeline step: Acquisition (historical pre-treatment population & density)

Why 2010 Decennial: The decennial census is a complete enumeration (not a survey
estimate), so it has zero sampling error — unlike the ACS which has margins of error,
especially for small ZCTAs. April 1, 2010 is right at the start of the 2009-2022
analysis window, providing clean pre-treatment population weights for the DiD design.

Requirements:
    pip install requests geopandas

Usage:
    python src/scripts/download_census_population.py
    python src/scripts/download_census_population.py --force   # re-download even if cached

Inputs:
    Census API: 2010 Decennial SF1, table P001001 (Total Population) by ZCTA
    data/raw/tiger-census/tl_2025_us_zcta520.shp  (for ALAND20 land area)

Outputs:
    data/raw/census-2010/census_2010_zcta_population_raw.json  (cached API response)
    data/raw/census-2010/census_2010_zcta_population.csv       (zip, population, density)
"""

import argparse
import json
import os

import requests

# ==============================================================================
# CONFIGURATION
# ==============================================================================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Census API endpoint — 2010 Decennial SF1, no API key required
# P001001 = Total Population; ZCTA available without state parameter
CENSUS_URL = (
    "https://api.census.gov/data/2010/dec/sf1"
    "?get=P001001,NAME"
    "&for=zip%20code%20tabulation%20area:*"
)

# ZCTA shapefile (for land area → density calculation)
ZCTA_SHP_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "tiger-census", "tl_2025_us_zcta520.shp")

# Output paths
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "census-2010")
RAW_JSON_PATH = os.path.join(OUTPUT_DIR, "census_2010_zcta_population_raw.json")
OUTPUT_CSV_PATH = os.path.join(OUTPUT_DIR, "census_2010_zcta_population.csv")

# Conversion: square meters → square miles
SQ_METERS_PER_SQ_MILE = 2_589_988.11


# ==============================================================================
# DOWNLOAD
# ==============================================================================

def download_census(url, cache_path, force=False):
    """
    Fetch 2010 decennial population data from Census API.

    Returns list of [population, name, zcta] rows (header row excluded).
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
    parser = argparse.ArgumentParser(description="Download 2010 Decennial Census ZCTA population")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args()

    print("=" * 60)
    print("2010 Decennial Census — ZCTA Population Download")
    print("=" * 60)

    # 1. Download from Census API
    print("\n1. Downloading 2010 Census population by ZCTA ...")
    rows = download_census(CENSUS_URL, RAW_JSON_PATH, force=args.force)

    # 2. Parse into {zcta: population}
    pop_data = {}
    n_null = 0
    for row in rows:
        # row = [P001001, NAME, zcta]
        pop_str, name, zcta = row
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

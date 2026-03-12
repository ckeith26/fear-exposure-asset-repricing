"""
Clean NOAA coastal counties GeoJSON and extract zip codes within those counties.

Inputs:
    data/raw/coastal-counties/noaa-counties.geojson
    data/raw/us-zips/uszips.csv
    data/raw/tiger-census/tl_2025_us_zcta520.shp  (for zip code boundaries)

Outputs:
    data/clean/coastal-counties/noaa-coastal-counties.geojson  (filtered counties)
    data/clean/coastal-counties/coastal_zipcodes.csv           (zip codes in those counties)
    data/clean/coastal-counties/coastal_zipcodes.geojson       (zip code boundaries)

Filters applied:
    1. Remove US territories (PR, AS, GU, VI, CNMI)
    2. Keep only valid geometries
    3. Standardize property types (FIPS as strings, population as int)
    4. Ocean boundary filter — remove inland watershed-only counties
    5. Join zip codes using county_fips_all (+ spatial fallback for CT)

Usage:
    python src/scripts/clean_coastal_counties.py
"""

import argparse
import csv
import json
import os
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict

import geopandas as gpd
import requests
from shapely.geometry import Point, shape

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")

RAW_COUNTIES_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "coastal-counties", "noaa-counties.geojson")
RAW_ZIPS_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "us-zips", "uszips.csv")
RAW_ZCTA_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "tiger-census", "tl_2025_us_zcta520.shp")
CENSUS_POP_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "census-2010", "census_2010_zcta_population.csv")

CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "clean", "coastal-counties")
CLEAN_COUNTIES_PATH = os.path.join(CLEAN_DIR, "noaa-coastal-counties.geojson")
CLEAN_ZIPS_PATH = os.path.join(CLEAN_DIR, "coastal_zipcodes.csv")
CLEAN_ZIPS_GEOJSON_PATH = os.path.join(CLEAN_DIR, "coastal_zipcodes.geojson")

# Exclude US territories + Alaska + Hawaii (too remote for comparable housing market analysis)
EXCLUDED_STATES = {"PR", "AS", "GU", "VI", "MP", "AK", "HI"}

# Ocean boundary filter config
OCEAN_URL = "https://naciscdn.org/naturalearth/10m/physical/ne_10m_ocean.zip"
OCEAN_CACHE_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "natural-earth")
OCEAN_CACHE_PATH = os.path.join(OCEAN_CACHE_DIR, "ne_10m_ocean.zip")
OCEAN_BUFFER_DEG = 0.005  # ~500m buffer for coastline precision mismatches


# ==============================================================================
# LOAD
# ==============================================================================

def load_raw(path):
    """Load raw GeoJSON and return the parsed dict."""
    print(f"Loading raw data from: {path}")

    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    n = len(data.get("features", []))
    print(f"  Loaded {n:,} features")
    return data


# ==============================================================================
# FILTER
# ==============================================================================

def filter_us_coastal(data):
    """
    Filter to US states + DC only (remove territories).

    NOAA's coastal county definition includes counties bordering the ocean
    as well as counties with significant tidal influence (e.g. Chesapeake Bay).
    All NOAA-designated coastal counties are retained here.
    """
    raw_features = data["features"]

    # 1. Remove territories
    us_features = [
        f for f in raw_features
        if f["properties"].get("stateusps") not in EXCLUDED_STATES
    ]
    n_territories = len(raw_features) - len(us_features)
    print(f"  Removed {n_territories} excluded features (territories + AK)")

    # 2. Drop features with null or empty geometry
    valid_features = [
        f for f in us_features
        if f.get("geometry") is not None
    ]
    n_invalid = len(us_features) - len(valid_features)
    if n_invalid > 0:
        print(f"  Removed {n_invalid} features with null geometry")

    # 3. Standardize property types
    for f in valid_features:
        props = f["properties"]
        # Ensure FIPS codes are zero-padded strings
        props["statefips"] = str(props.get("statefips", "")).zfill(2)
        props["countyfips"] = str(props.get("countyfips", "")).zfill(5)
        # Ensure numeric fields are int (handle None)
        for col in ("totalpopulation", "totalhousingunit", "medianhouseholdincome"):
            val = props.get(col)
            props[col] = int(val) if val is not None else None

    print(f"  Retained {len(valid_features)} US coastal counties")
    return valid_features


# ==============================================================================
# OCEAN BOUNDARY FILTER
# ==============================================================================

def download_ocean_polygon(url, cache_path):
    """Download Natural Earth ocean shapefile zip, skip if already cached."""
    if os.path.exists(cache_path):
        print(f"  Ocean data cached: {cache_path}")
        return

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    print(f"  Downloading ocean polygon from {url} ...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(cache_path, "wb") as f:
        f.write(resp.content)
    size_mb = len(resp.content) / 1e6
    print(f"  Downloaded {size_mb:.1f} MB → {cache_path}")


def load_ocean_polygon(zip_path):
    """Read ocean shapefile from zip, dissolve to single geometry."""
    gdf = gpd.read_file(f"zip://{zip_path}")
    ocean = gdf.dissolve().geometry.iloc[0]
    return ocean


def filter_ocean_bordering(features, ocean_geom, buffer_deg):
    """
    Keep only counties whose geometry intersects the ocean polygon.

    A small buffer on counties handles coastline digitization mismatches
    between NOAA and Natural Earth datasets.
    """
    print(f"\n  Ocean boundary filter (buffer={buffer_deg} deg) ...")

    # Build GeoDataFrame from feature geometries
    geometries = [shape(f["geometry"]) for f in features]
    gdf = gpd.GeoDataFrame(
        {"idx": range(len(features))},
        geometry=geometries,
        crs="EPSG:4326",
    )

    # Buffer counties slightly to handle precision gaps
    gdf_buffered = gdf.copy()
    gdf_buffered["geometry"] = gdf.geometry.buffer(buffer_deg)

    # Create ocean GeoDataFrame for spatial join
    ocean_gdf = gpd.GeoDataFrame(geometry=[ocean_geom], crs="EPSG:4326")

    # Spatial join: find counties that intersect the ocean
    joined = gpd.sjoin(gdf_buffered, ocean_gdf, how="inner", predicate="intersects")
    matching_indices = set(joined["idx"])

    # Collect kept and removed features
    kept = []
    removed_by_state = defaultdict(list)
    for i, f in enumerate(features):
        if i in matching_indices:
            kept.append(f)
        else:
            state = f["properties"].get("statename", "Unknown")
            name = f["properties"].get("countyname", "Unknown")
            removed_by_state[state].append(name)

    # Report removals
    n_removed = len(features) - len(kept)
    print(f"  Removed {n_removed} inland/watershed-only counties")
    for state in sorted(removed_by_state):
        counties = removed_by_state[state]
        print(f"    {state}: {', '.join(sorted(counties))}")

    print(f"  Retained {len(kept)} ocean-bordering counties")
    return kept


# ==============================================================================
# ZIP CODE FILTERING
# ==============================================================================

def filter_coastal_zipcodes(coastal_features, zips_path):
    """
    Filter uszips.csv to only zip codes within the cleaned coastal counties.

    Uses county_fips_all (pipe-delimited) so zip codes that span multiple
    counties are included if ANY of their counties is coastal.

    For Connecticut, uses a spatial point-in-polygon fallback because NOAA
    uses old county FIPS (09001-09011) while uszips.csv uses new planning
    region FIPS (09110+), causing zero FIPS matches.
    """
    print(f"\nLoading zip codes from: {zips_path}")

    if not os.path.exists(zips_path):
        print(f"ERROR: File not found: {zips_path}")
        sys.exit(1)

    # Build set of coastal county FIPS from the cleaned features
    coastal_fips = {f["properties"]["countyfips"] for f in coastal_features}

    with open(zips_path, newline="") as f:
        reader = csv.DictReader(f)
        all_zips = list(reader)

    print(f"  Loaded {len(all_zips):,} total zip codes")

    # Separate CT zips from all others
    ct_zips = [r for r in all_zips if r.get("state_id") == "CT"]
    non_ct_zips = [r for r in all_zips if r.get("state_id") != "CT"]

    # Standard FIPS join for non-CT states
    coastal_zips = []
    for row in non_ct_zips:
        fips_all = row.get("county_fips_all", "")
        zip_fips = {fip.strip() for fip in fips_all.split("|") if fip.strip()}
        if zip_fips & coastal_fips:
            coastal_zips.append(row)

    print(f"  Matched {len(coastal_zips):,} zip codes via FIPS join (excl. CT)")

    # --- Connecticut spatial fallback ---
    ct_features = [f for f in coastal_features if f["properties"].get("statefips") == "09"]
    if ct_features and ct_zips:
        ct_coastal = _ct_spatial_match(ct_zips, ct_features)
        coastal_zips.extend(ct_coastal)
        print(f"  Matched {len(ct_coastal):,} CT zip codes via spatial fallback")
    elif ct_features:
        print("  WARNING: CT counties found but no CT zip codes in uszips.csv")

    print(f"  Total coastal zip codes: {len(coastal_zips):,}")
    return coastal_zips


def _ct_spatial_match(ct_zips, ct_features):
    """
    Match Connecticut zip codes to coastal counties using point-in-polygon.

    Builds Point geometries from zip lat/lng and tests containment against
    CT county polygons from the NOAA data.
    """
    # Build CT county polygons
    ct_geoms = [shape(f["geometry"]) for f in ct_features]
    ct_gdf = gpd.GeoDataFrame(geometry=ct_geoms, crs="EPSG:4326")
    ct_union = ct_gdf.dissolve().geometry.iloc[0]

    matched = []
    for row in ct_zips:
        try:
            lat = float(row["lat"])
            lng = float(row["lng"])
        except (ValueError, KeyError):
            continue
        if ct_union.contains(Point(lng, lat)):
            matched.append(row)

    return matched


def classify_treatment_control(zip_rows, zcta_path, ocean_geom):
    """
    Classify coastal zip codes as treatment or adjacent-control, drop the rest.

    Treatment: ZCTA polygon intersects the ocean.
    Control:   ZCTA polygon is adjacent to (shares a boundary with) a treatment
               ZCTA, but does NOT itself touch the ocean.
    Dropped:   All other zips (deep inland) are removed from the dataset.

    Adds 'coastal_treatment' key to each kept zip row dict: "1" or "0".
    Returns (filtered_zip_rows, filtered_zcta_gdf) — only treatment + control.
    """
    if not zip_rows:
        print("  WARNING: No zip codes to classify")
        return zip_rows, None

    if not os.path.exists(zcta_path):
        print(f"  WARNING: ZCTA shapefile not found: {zcta_path}")
        print("  Skipping treatment/control classification")
        for row in zip_rows:
            row["coastal_treatment"] = ""
        return zip_rows, None

    print(f"\nClassifying treatment/control from: {zcta_path}")

    coastal_zip_set = {row["zip"] for row in zip_rows}

    # Load and filter ZCTA shapefile to coastal zips only
    zcta = gpd.read_file(zcta_path)
    zcta_filtered = zcta[zcta["ZCTA5CE20"].isin(coastal_zip_set)].copy()

    n_matched = len(zcta_filtered)
    n_missing = len(coastal_zip_set) - n_matched
    print(f"  Matched {n_matched:,} ZCTA polygons ({n_missing:,} zips without ZCTA match)")

    # Step 1: Identify treatment ZCTAs (intersect ocean)
    ocean_gdf = gpd.GeoDataFrame(geometry=[ocean_geom], crs="EPSG:4326")
    ocean_joined = gpd.sjoin(zcta_filtered, ocean_gdf, how="inner", predicate="intersects")
    treatment_zips = set(ocean_joined["ZCTA5CE20"])

    # Step 2: Split into treatment and non-treatment GeoDataFrames
    treatment_gdf = zcta_filtered[zcta_filtered["ZCTA5CE20"].isin(treatment_zips)]
    non_treatment_gdf = zcta_filtered[~zcta_filtered["ZCTA5CE20"].isin(treatment_zips)]

    # Step 3: Find non-treatment ZCTAs adjacent to any treatment ZCTA
    if len(non_treatment_gdf) > 0 and len(treatment_gdf) > 0:
        adj_joined = gpd.sjoin(
            non_treatment_gdf, treatment_gdf, how="inner", predicate="intersects"
        )
        # Deduplicate — a non-treatment ZCTA may border multiple treatment ZCTAs
        control_zips = set(adj_joined["ZCTA5CE20_left"])
    else:
        control_zips = set()

    # Step 4: Build the kept set (treatment + adjacent control)
    kept_zips = treatment_zips | control_zips

    # Step 5: Tag zip rows and filter to kept zips only
    filtered_zip_rows = []
    for row in zip_rows:
        if row["zip"] in treatment_zips:
            row["coastal_treatment"] = "1"
            filtered_zip_rows.append(row)
        elif row["zip"] in control_zips:
            row["coastal_treatment"] = "0"
            filtered_zip_rows.append(row)
        # else: deep-inland zip — dropped

    # Step 6: Filter ZCTA GeoDataFrame to kept zips
    zcta_kept = zcta_filtered[zcta_filtered["ZCTA5CE20"].isin(kept_zips)].copy()

    n_treatment = sum(1 for r in filtered_zip_rows if r["coastal_treatment"] == "1")
    n_control = sum(1 for r in filtered_zip_rows if r["coastal_treatment"] == "0")
    n_dropped = len(zip_rows) - len(filtered_zip_rows)
    print(f"  Treatment (touches ocean):     {n_treatment:,}")
    print(f"  Control (adjacent to treatment): {n_control:,}")
    print(f"  Dropped (deep inland):         {n_dropped:,}")

    return filtered_zip_rows, zcta_kept


# ==============================================================================
# POPULATION FILTER
# ==============================================================================

def load_census_population(census_path):
    """
    Load 2010 Census historical population and density by ZCTA.

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


def overlay_census_population(zip_rows, census_lookup):
    """
    Replace population and density in zip rows with 2010 Census values.

    Drops zips without census data to avoid mixing historical and modern population.
    """
    if census_lookup is None:
        print("  WARNING: No census data — keeping SimpleMaps population/density")
        return zip_rows

    matched = []
    n_dropped = 0
    for row in zip_rows:
        z = row.get("zip", "").strip()
        if z in census_lookup:
            row["population"] = str(census_lookup[z]["population"])
            density = census_lookup[z]["density"]
            row["density"] = str(density) if density is not None else ""
            matched.append(row)
        else:
            n_dropped += 1

    print(f"  ACS population overlay: {len(matched):,} matched, {n_dropped:,} dropped (no census data)")
    return matched


def filter_by_county_population(zip_rows, zips_path, census_lookup, threshold):
    """
    Filter zip rows to only those in counties above the population threshold.

    Uses 2010 Census population when available, with uszips.csv county_fips
    crosswalk for zip-to-county mapping. Falls back to SimpleMaps population
    for zips missing from ACS.

    Returns filtered zip_rows list.
    """
    if threshold <= 0:
        return zip_rows

    print(f"\nApplying county population filter (>= {threshold:,}) ...")

    # Aggregate zip populations to county level using uszips.csv crosswalk + ACS pop
    county_pop = defaultdict(int)
    with open(zips_path, newline="") as f:
        for row in csv.DictReader(f):
            fips = row.get("county_fips", "").strip()
            z = row.get("zip", "").strip()
            if not fips:
                continue
            # Prefer ACS population, fall back to SimpleMaps
            if census_lookup and z in census_lookup:
                county_pop[fips] += census_lookup[z]["population"]
            else:
                pop = row.get("population", "")
                if pop:
                    try:
                        county_pop[fips] += int(float(pop))
                    except ValueError:
                        pass

    # Filter zip rows — use county_fips from each zip row
    before = len(zip_rows)
    filtered = []
    for row in zip_rows:
        fips = row.get("county_fips", "").strip()
        if county_pop.get(fips, 0) >= threshold:
            filtered.append(row)

    n_treatment = sum(1 for r in filtered if r.get("coastal_treatment") == "1")
    n_control = sum(1 for r in filtered if r.get("coastal_treatment") == "0")
    print(f"  Before: {before:,} zips")
    print(f"  After:  {len(filtered):,} zips ({n_treatment:,} treatment, {n_control:,} control)")
    print(f"  Dropped: {before - len(filtered):,} zips in counties < {threshold:,} pop")

    return filtered


def threshold_label(threshold):
    """Convert threshold int to filename label: 0 -> 'full', 25000 -> '25k', etc."""
    if threshold <= 0:
        return "full"
    if threshold % 1000 == 0:
        return f"{threshold // 1000}k"
    return str(threshold)


def save_zipcodes(zip_rows, path):
    """Write filtered zip codes to CSV."""
    if not zip_rows:
        print("  WARNING: No zip codes to save")
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)

    fieldnames = zip_rows[0].keys()
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(zip_rows)

    size_mb = os.path.getsize(path) / 1e6
    print(f"  Saved: {path} ({size_mb:.1f} MB)")


# ==============================================================================
# ZIP CODE GEOJSON OUTPUT
# ==============================================================================

def save_zipcodes_geojson(zip_rows, zcta_filtered, output_path):
    """
    Create GeoJSON of coastal zip code boundaries with treatment classification.

    Uses the pre-filtered ZCTA GeoDataFrame from classify_treatment_control
    to avoid loading the shapefile twice. Joins the coastal_treatment column
    from zip_rows before writing.
    """
    if not zip_rows:
        print("  WARNING: No zip codes — skipping GeoJSON output")
        return

    if zcta_filtered is None or zcta_filtered.empty:
        print("  WARNING: No ZCTA data — skipping GeoJSON output")
        return

    print(f"\nBuilding zip code GeoJSON ...")

    # Build treatment lookup from zip_rows
    treatment_map = {row["zip"]: row.get("coastal_treatment", "") for row in zip_rows}
    zcta_filtered["coastal_treatment"] = zcta_filtered["ZCTA5CE20"].map(treatment_map).fillna("")

    print(f"  Writing {len(zcta_filtered):,} ZCTA polygons with treatment classification")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    zcta_filtered.to_file(output_path, driver="GeoJSON")

    size_mb = os.path.getsize(output_path) / 1e6
    print(f"  Saved: {output_path} ({size_mb:.1f} MB)")


# ==============================================================================
# SAVE
# ==============================================================================

def save_clean(features, path):
    """Write filtered features as a GeoJSON FeatureCollection."""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(path, "w") as f:
        json.dump(collection, f)

    size_mb = os.path.getsize(path) / 1e6
    print(f"  Saved: {path} ({size_mb:.1f} MB)")


# ==============================================================================
# SUMMARY
# ==============================================================================

def print_summary(features, zip_rows):
    """Print a summary of the cleaned dataset with treatment/control breakdown."""

    state_counts = Counter(f["properties"]["statename"] for f in features)
    zip_state_counts = Counter(r["state_name"] for r in zip_rows)

    # Treatment/control counts per state
    treatment_by_state = Counter(
        r["state_name"] for r in zip_rows if r.get("coastal_treatment") == "1"
    )
    control_by_state = Counter(
        r["state_name"] for r in zip_rows if r.get("coastal_treatment") == "0"
    )

    n_treatment = sum(treatment_by_state.values())
    n_control = sum(control_by_state.values())

    print(f"\n{'=' * 50}")
    print(f"CLEANED DATASET SUMMARY")
    print(f"{'=' * 50}")
    print(f"  Coastal counties:   {len(features)}")
    print(f"  Coastal zip codes:  {len(zip_rows)}")
    print(f"    Treatment (ocean):    {n_treatment:,}")
    print(f"    Control (adjacent):   {n_control:,}")
    print(f"  States + DC:        {len(state_counts)}")
    print(f"\n  Counties / Zip codes per state:")
    for state, count in state_counts.most_common():
        zips = zip_state_counts.get(state, 0)
        t = treatment_by_state.get(state, 0)
        c = control_by_state.get(state, 0)
        print(f"    {state}: {count} counties, {zips} zips ({t} treatment, {c} control)")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean NOAA coastal counties and classify zip codes as treatment/control"
    )
    parser.add_argument(
        "--threshold", type=str, default="full",
        help="Min county population threshold: 'full' (no filter), '10k', '25k', '50k', or a number"
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

    print("NOAA Coastal Counties — Clean & Filter")
    print(f"Population threshold: {label} ({pop_threshold:,})")
    print("=" * 50)

    # 1. Load & filter to US states
    data = load_raw(RAW_COUNTIES_PATH)
    features = filter_us_coastal(data)

    # 2. Ocean boundary filter
    print(f"\nApplying ocean boundary filter ...")
    download_ocean_polygon(OCEAN_URL, OCEAN_CACHE_PATH)
    ocean_geom = load_ocean_polygon(OCEAN_CACHE_PATH)
    features = filter_ocean_bordering(features, ocean_geom, OCEAN_BUFFER_DEG)

    # 3. Save cleaned counties
    save_clean(features, CLEAN_COUNTIES_PATH)

    # 4. Filter zip codes (FIPS join + CT spatial fallback)
    zip_rows = filter_coastal_zipcodes(features, RAW_ZIPS_PATH)

    # 4a. Load 2010 Census historical population and overlay onto zip rows
    print("\nLoading 2010 Census historical population ...")
    census_lookup = load_census_population(CENSUS_POP_PATH)
    zip_rows = overlay_census_population(zip_rows, census_lookup)

    # 4b. Save full coastal zip universe (before treatment/control classification)
    save_zipcodes(zip_rows, CLEAN_ZIPS_PATH)

    # 5. Classify treatment (touches ocean) vs control (adjacent to treatment)
    zip_rows, zcta_filtered = classify_treatment_control(zip_rows, RAW_ZCTA_PATH, ocean_geom)

    # 6. Apply population threshold (pair first, then filter)
    zip_rows = filter_by_county_population(zip_rows, RAW_ZIPS_PATH, census_lookup, pop_threshold)

    # 7. Save paired zip codes with threshold label
    paired_csv_path = os.path.join(CLEAN_DIR, f"coastal_zipcodes_paired_tr_{label}.csv")
    save_zipcodes(zip_rows, paired_csv_path)

    # 8. Create zip code boundary GeoJSON (filter ZCTA to surviving zips)
    if zcta_filtered is not None:
        kept_zips = {row["zip"] for row in zip_rows}
        zcta_filtered = zcta_filtered[zcta_filtered["ZCTA5CE20"].isin(kept_zips)].copy()
    save_zipcodes_geojson(zip_rows, zcta_filtered, CLEAN_ZIPS_GEOJSON_PATH)

    # 10. Summary
    print_summary(features, zip_rows)

    print(f"\nDone. Outputs:")
    print(f"  {CLEAN_COUNTIES_PATH}")
    print(f"  {paired_csv_path}")
    print(f"  {CLEAN_ZIPS_GEOJSON_PATH}")

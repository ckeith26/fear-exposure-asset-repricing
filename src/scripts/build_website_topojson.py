"""
Build TopoJSON for the website TreatmentMap component.

Reads the regression panel CSV, applies the same sample filters as event_study.do,
then joins to ZCTA shapefile geometries. Outputs a compact TopoJSON with properties
matching what TreatmentMap.tsx expects.

Inputs:
    data/clean/regression_panel.csv
    data/raw/tiger-census/tl_2025_us_zcta520.shp
    data/raw/us-zips/uszips.csv                      (for city/state/county names)

Outputs:
    website/public/data/coastal_zips.json

Usage:
    python src/scripts/build_website_topojson.py
"""

import json
import os

import geopandas as gpd
import pandas as pd
import topojson as tp

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")

REGRESSION_PANEL_PATH = os.path.join(PROJECT_ROOT, "data", "clean", "regression_panel.csv")
ZCTA_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "tiger-census", "tl_2025_us_zcta520.shp")
USZIPS_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "us-zips", "uszips.csv")
ELECTION_PATH = os.path.join(PROJECT_ROOT, "data", "clean", "election_county_year.csv")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "website", "public", "data", "coastal_zips.json")

SIMPLIFY_TOLERANCE = 0.002  # ~200m, matches build_treatment_map.py


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    # 1. Load regression panel and apply do-file sample filters
    print("Loading regression panel ...")
    df = pd.read_csv(REGRESSION_PANEL_PATH, dtype={"zip": str, "county_fips": str, "state_id": str})
    print(f"  {len(df):,} rows, {df['zip'].nunique():,} unique zips")

    df = df[df["already_treated"] != 1]
    df = df[df["n_lomrs"] <= 1]
    df = df[df["population"] > 0]
    df = df.dropna(subset=["population"])

    # Drop treated zips whose LOMR is after the panel ends (never actually treated)
    lomr_dates = pd.to_datetime(df["first_lomr_date"])
    panel_end = df["year_month"].max()  # e.g. "2022-12"
    panel_end_year = int(panel_end[:4])
    post_panel = (df["ever_treated"] == 1) & (lomr_dates.dt.year > panel_end_year)
    post_panel_zips = df.loc[post_panel, "zip"].unique()
    df = df[~df["zip"].isin(post_panel_zips)]
    print(f"  Dropped {len(post_panel_zips)} treated zips with LOMR after {panel_end_year}")
    print(f"  After filters: {len(df):,} rows, {df['zip'].nunique():,} unique zips")

    # 2a. Compute annual median ZHVI per zip (for map home-value mode)
    print("Computing annual median ZHVI per zip ...")
    df["year"] = df["year_month"].astype(str).str[:4].astype(int)
    zhvi_annual = (
        df.dropna(subset=["zhvi"])
        .groupby(["zip", "year"])["zhvi"]
        .median()
        .reset_index()
    )
    # Pivot to wide: one row per zip, columns = years
    zhvi_wide = zhvi_annual.pivot(index="zip", columns="year", values="zhvi")
    # Build lookup: zip → {year_int: median_zhvi_rounded}
    zhvi_by_zip = {}
    for z, row in zhvi_wide.iterrows():
        yearly = {}
        for yr_col in row.index:
            if pd.notna(row[yr_col]):
                yearly[int(yr_col)] = round(float(row[yr_col]))
        zhvi_by_zip[z] = yearly
    print(f"  {len(zhvi_by_zip):,} zips with ZHVI data")

    # 2b. Collapse to one row per zip (take first non-null values)
    zip_df = (
        df.sort_values("year_month")
        .groupby("zip", as_index=False)
        .agg({
            "ever_treated": "first",
            "n_lomrs": "first",
            "first_lomr_date": "first",
            "population": "first",
            "density": "first",
            "county_fips": "first",
            "state_id": "first",
        })
    )

    # Compute LOMR year for treated zips
    zip_df["first_lomr_date"] = pd.to_datetime(zip_df["first_lomr_date"])
    zip_df["lomr_year"] = zip_df["first_lomr_date"].dt.year

    treated = zip_df["ever_treated"].sum()
    control = (zip_df["ever_treated"] == 0).sum()
    print(f"  Sample: {int(treated)} treated + {int(control)} control = {len(zip_df)} zips")

    # 3. Load city/state/county names from uszips
    print(f"Loading zip metadata: {USZIPS_PATH}")
    uszips = pd.read_csv(USZIPS_PATH, dtype=str, usecols=["zip", "city", "state_id", "county_name"])
    zip_meta = uszips.set_index("zip")[["city", "state_id", "county_name"]].to_dict("index")

    # 3b. Load 2020 election data (county-level Republican vote share)
    print(f"Loading election data: {ELECTION_PATH}")
    election = pd.read_csv(ELECTION_PATH, dtype={"county_fips": str})
    e2020 = election[election["year"] == 2020][["county_fips", "rep_share"]].set_index("county_fips")
    rep_lookup = e2020["rep_share"].to_dict()
    print(f"  {len(rep_lookup)} counties with 2020 election data")

    # 4. Load ZCTA shapefile, filter to sample zips
    print(f"Loading ZCTA shapefile: {ZCTA_PATH}")
    sample_zips = set(zip_df["zip"])
    zcta = gpd.read_file(ZCTA_PATH)
    zcta = zcta[zcta["ZCTA5CE20"].isin(sample_zips)].copy()
    zcta = zcta.to_crs("EPSG:4326")
    print(f"  {len(zcta):,} ZCTA polygons matched out of {len(sample_zips):,} sample zips")

    missing = sample_zips - set(zcta["ZCTA5CE20"])
    if missing:
        print(f"  {len(missing)} zips without ZCTA geometry (will be absent from map)")

    # 5. Simplify geometries
    print(f"Simplifying (tolerance={SIMPLIFY_TOLERANCE}) ...")
    zcta["geometry"] = zcta.geometry.simplify(SIMPLIFY_TOLERANCE)

    # 6. Build properties lookup
    zip_props = {}
    for _, row in zip_df.iterrows():
        z = row["zip"]
        meta = zip_meta.get(z, {})
        zip_props[z] = {
            "z": z,
            "ct": int(row["ever_treated"]),  # coastal_treatment (1=treated, 0=control)
            "tr": int(row["ever_treated"]),
            "yr": int(row["lomr_year"]) if pd.notna(row["lomr_year"]) else None,
            "pop": int(row["population"]) if pd.notna(row["population"]) else None,
            "den": round(float(row["density"]), 1) if pd.notna(row["density"]) else None,
            "nl": int(row["n_lomrs"]) if pd.notna(row["n_lomrs"]) else 0,
            "is": 1,  # all zips in this file are in-sample by definition
            "ci": meta.get("city", ""),
            "st": meta.get("state_id", ""),
            "co": meta.get("county_name", ""),
            "rep": round(rep_lookup.get(row["county_fips"], float("nan")), 3)
                   if pd.notna(rep_lookup.get(row["county_fips"])) else None,
            "hv": zhvi_by_zip.get(z, {}),       # yearly ZHVI dict {2009: val, ..., 2022: val}
            "hv22": zhvi_by_zip.get(z, {}).get(2022),  # 2022 median ZHVI (for filter)
        }

    # 7. Assign properties to GeoDataFrame
    prop_cols = ["z", "ct", "tr", "yr", "pop", "den", "nl", "is", "ci", "st", "co", "rep", "hv", "hv22"]
    for col in prop_cols:
        zcta[col] = zcta["ZCTA5CE20"].map(lambda zc, c=col: zip_props.get(zc, {}).get(c))

    # Drop rows without property match (shouldn't happen, but safety)
    zcta = zcta[zcta["z"].notna()].copy()

    # Keep only the columns we need
    zcta = zcta[["geometry"] + prop_cols]

    # 8. Convert to TopoJSON
    print("Converting to TopoJSON ...")
    topo = tp.Topology(zcta, toposimplify=0, object_name="coastal_zips_filtered")

    # 9. Export
    topo_dict = topo.to_dict()

    # Clean up property types (topojson library may convert ints to floats)
    for geom in topo_dict["objects"]["coastal_zips_filtered"]["geometries"]:
        props = geom.get("properties", {})
        # Fix yr: NaN → None, float → int
        yr = props.get("yr")
        if yr is not None:
            if pd.isna(yr):
                props["yr"] = None
            else:
                props["yr"] = int(yr)
        # Fix pop: float → int
        pop = props.get("pop")
        if pop is not None and not pd.isna(pop):
            props["pop"] = int(pop)
        # Fix other numeric fields
        for key in ("ct", "tr", "nl", "is"):
            val = props.get(key)
            if val is not None and not pd.isna(val):
                props[key] = int(val)
        # Fix rep: NaN → None
        rep = props.get("rep")
        if rep is not None and pd.isna(rep):
            props["rep"] = None
        # Fix hv22: NaN → None, float → int
        hv22 = props.get("hv22")
        if hv22 is not None:
            if pd.isna(hv22):
                props["hv22"] = None
            else:
                props["hv22"] = int(hv22)
        # Fix hv: ensure dict with int keys → string keys (JSON requires string keys)
        hv = props.get("hv")
        if hv is not None and isinstance(hv, dict):
            props["hv"] = {str(k): int(v) for k, v in hv.items() if pd.notna(v)}

    # Write compact JSON
    output_str = json.dumps(topo_dict, separators=(",", ":"), allow_nan=False, default=str)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(output_str)

    size_mb = len(output_str) / 1024 / 1024
    n_geoms = len(topo_dict["objects"]["coastal_zips_filtered"]["geometries"])
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"  {n_geoms:,} geometries, {size_mb:.1f} MB")

    # Count treated/control in output
    t = sum(1 for g in topo_dict["objects"]["coastal_zips_filtered"]["geometries"]
            if g.get("properties", {}).get("tr") == 1)
    c = n_geoms - t
    print(f"  {t} treated + {c} control = {n_geoms} total")

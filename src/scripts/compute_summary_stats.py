"""
Compute summary statistics for the staggered event study regression panel.

Regression:
    ln(ZHVI_z,t) = α_z + δ_t + Σ β_τ · 1[t − E_z = τ] + γ X_z,t + ε_z,t

Builds the full regression panel by merging:
    1. ZHVI zip-month panel (dependent variable)
    2. LOMR treatment timing (treatment indicators)
    3. BLS county unemployment (control)
    4. NFIP policies/claims (controls + treatment heterogeneity)

Outputs:
    data/clean/regression_panel.csv          (full zip × month panel for Stata)
    data/clean/summary_statistics.csv        (Table 1 for paper)
    Prints formatted summary table to console

Usage:
    python src/scripts/compute_summary_stats.py
    python src/scripts/compute_summary_stats.py --start-year 2009 --end-year 2022
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import requests

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")

# Inputs
ZHVI_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "zhvi",
                         "Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv")
TREATMENT_PATH_TEMPLATE = os.path.join(PROJECT_ROOT, "data", "clean",
                                       "coastal_zipcodes_lomr_tr_{label}{window}.csv")
BLS_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "bls-laus", "la.data.64.County")
NFIP_PANEL_PATH = os.path.join(PROJECT_ROOT, "data", "clean", "nfip_zip_month_panel.csv")
NFIP_DELTAS_PATH = os.path.join(PROJECT_ROOT, "data", "clean", "nfip_lomr_deltas.csv")
DISCLOSURE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "state-disclosure-laws",
                               "disclosure_laws.csv")

# Outputs
CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "clean")
PANEL_PATH = os.path.join(CLEAN_DIR, "regression_panel.csv")
STATS_PATH = os.path.join(CLEAN_DIR, "summary_statistics.csv")


# ==============================================================================
# LOAD ZHVI (DEPENDENT VARIABLE)
# ==============================================================================

def load_zhvi(path, coastal_zips, start_year, end_year):
    """
    Load Zillow ZHVI zip-level data, melt from wide to long format,
    filter to coastal zips and analysis window.

    Wide format: rows = zips, columns = monthly dates (2000-01-31 ... 2025-12-31)
    Long format: zip × year_month with ZHVI value
    """
    print("\n--- Loading ZHVI (dependent variable) ---")
    print(f"  Source: {path}")

    df = pd.read_csv(path, dtype={"RegionName": str})
    print(f"  Loaded {len(df):,} zips × {len(df.columns) - 9} months")

    # Identify date columns (format: YYYY-MM-DD)
    meta_cols = ["RegionID", "SizeRank", "RegionName", "RegionType",
                 "StateName", "State", "City", "Metro", "CountyName"]
    date_cols = [c for c in df.columns if c not in meta_cols]

    # Pad zip codes to 5 digits
    df["zip"] = df["RegionName"].str.zfill(5)

    # Filter to coastal zips
    df = df[df["zip"].isin(coastal_zips)].copy()
    print(f"  Filtered to {len(df):,} coastal zips")

    # Melt to long format
    zhvi_long = df.melt(
        id_vars=["zip"],
        value_vars=date_cols,
        var_name="date",
        value_name="zhvi",
    )
    zhvi_long["date"] = pd.to_datetime(zhvi_long["date"])
    zhvi_long["year_month"] = zhvi_long["date"].dt.to_period("M")

    # Filter to analysis window
    if start_year:
        zhvi_long = zhvi_long[zhvi_long["date"].dt.year >= start_year]
    if end_year:
        zhvi_long = zhvi_long[zhvi_long["date"].dt.year <= end_year]

    # Drop missing ZHVI
    before = len(zhvi_long)
    zhvi_long = zhvi_long.dropna(subset=["zhvi"])
    after = len(zhvi_long)
    print(f"  Long format: {after:,} zip-months ({before - after:,} missing ZHVI dropped)")

    # Compute log ZHVI
    zhvi_long["ln_zhvi"] = np.log(zhvi_long["zhvi"])

    zhvi_long = zhvi_long[["zip", "year_month", "date", "zhvi", "ln_zhvi"]].copy()
    print(f"  Date range: {zhvi_long['year_month'].min()} to {zhvi_long['year_month'].max()}")
    print(f"  Unique zips: {zhvi_long['zip'].nunique():,}")

    return zhvi_long


# ==============================================================================
# LOAD TREATMENT TIMING
# ==============================================================================

def load_treatment(treatment_path):
    """
    Load treatment CSV with LOMR timing and zip characteristics.

    Key columns: zip, first_lomr_date, ever_treated, already_treated,
    treated_in_window, population, density, state_id, county_fips.
    """
    print(f"\n--- Loading treatment timing ---")
    print(f"  Source: {treatment_path}")

    df = pd.read_csv(treatment_path, dtype={"zip": str, "county_fips": str})
    df["first_lomr_date"] = pd.to_datetime(df["first_lomr_date"], errors="coerce")

    n_treated = (df["ever_treated"] == 1).sum()
    n_control = (df["ever_treated"] == 0).sum()
    print(f"  {len(df):,} zips ({n_treated:,} treated, {n_control:,} control)")

    return df


# ==============================================================================
# LOAD BLS UNEMPLOYMENT
# ==============================================================================

def load_bls_unemployment(data_path, coastal_fips, start_year, end_year):
    """
    Load BLS LAUS county unemployment rate (measure 03).

    Series ID structure: LAUCN{5-digit FIPS}{7-char pad}{2-digit measure}
    e.g., LAUCN010010000000003 → FIPS 01001, measure 03 (unemployment rate)
    """
    print(f"\n--- Loading BLS county unemployment ---")
    print(f"  Source: {data_path}")

    df = pd.read_csv(data_path, sep="\t", dtype=str)
    df.columns = df.columns.str.strip()
    df["series_id"] = df["series_id"].str.strip()
    print(f"  Loaded {len(df):,} rows")

    # Filter to unemployment rate (measure code 03 = last char '3' with specific pattern)
    df = df[df["series_id"].str.endswith("3")].copy()
    # Verify it's measure 03 by checking the series_id pattern
    df = df[df["series_id"].str.startswith("LAUCN")].copy()
    print(f"  Filtered to {len(df):,} unemployment rate observations")

    # Extract county FIPS
    df["county_fips"] = df["series_id"].str[5:10]

    # Filter to coastal counties
    df = df[df["county_fips"].isin(coastal_fips)].copy()
    print(f"  Filtered to {len(df):,} coastal county observations")

    # Parse year and period
    df["year"] = pd.to_numeric(df["year"].str.strip(), errors="coerce")
    df["period"] = df["period"].str.strip()
    # Filter to monthly data (M01-M12), exclude annual (M13)
    df = df[df["period"].str.startswith("M") & (df["period"] != "M13")].copy()
    df["month"] = df["period"].str[1:].astype(int)

    # Filter to analysis window
    if start_year:
        df = df[df["year"] >= start_year]
    if end_year:
        df = df[df["year"] <= end_year]

    # Parse unemployment rate
    df["unemployment_rate"] = pd.to_numeric(df["value"].str.strip(), errors="coerce")

    # Create year_month
    df["year_month"] = pd.to_datetime(
        df["year"].astype(int).astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    ).dt.to_period("M")

    bls = df[["county_fips", "year_month", "unemployment_rate"]].copy()
    bls = bls.dropna(subset=["unemployment_rate"])
    print(f"  Final: {len(bls):,} county-month observations")
    print(f"  Unique counties: {bls['county_fips'].nunique():,}")

    return bls


# ==============================================================================
# LOAD NFIP PANEL
# ==============================================================================

def load_nfip_panel(path, coastal_zips, start_year, end_year):
    """Load NFIP zip × month panel (policies, premiums, claims)."""
    print(f"\n--- Loading NFIP panel ---")
    print(f"  Source: {path}")

    df = pd.read_csv(path, dtype={"zip": str})
    df["year_month"] = pd.PeriodIndex(df["year_month"], freq="M")
    print(f"  Loaded {len(df):,} zip-month rows")

    # Filter to coastal zips and window
    df = df[df["zip"].isin(coastal_zips)].copy()
    if start_year:
        df = df[df["year_month"].dt.year >= start_year]
    if end_year:
        df = df[df["year_month"].dt.year <= end_year]

    print(f"  Filtered: {len(df):,} zip-month rows, {df['zip'].nunique():,} zips")

    return df


# ==============================================================================
# LOAD CPI FOR DEFLATION
# ==============================================================================

CPI_CACHE_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "cpi_monthly.csv")

def load_cpi(start_year, end_year):
    """
    Download monthly CPI-U (All Urban Consumers, seasonally adjusted) from FRED.
    Deflates to constant dollars using December of end_year as base period.

    Source: FRED series CPIAUCSL
    """
    print(f"\n--- Loading CPI-U for deflation ---")

    # Download and cache
    if os.path.exists(CPI_CACHE_PATH):
        print(f"  Using cached: {CPI_CACHE_PATH}")
    else:
        print("  Downloading CPI-U from FRED...")
        url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv"
               f"?id=CPIAUCSL&cosd={start_year}-01-01&coed={end_year}-12-31")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(CPI_CACHE_PATH), exist_ok=True)
        with open(CPI_CACHE_PATH, "w") as f:
            f.write(resp.text)
        print(f"  Saved: {CPI_CACHE_PATH}")

    cpi = pd.read_csv(CPI_CACHE_PATH, parse_dates=["observation_date"])
    cpi.columns = ["date", "cpi"]
    cpi["year_month"] = cpi["date"].dt.to_period("M")

    # Base period: December of end year
    base_row = cpi[(cpi["date"].dt.year == end_year) & (cpi["date"].dt.month == 12)]
    if base_row.empty:
        base_row = cpi.iloc[[-1]]
    base_cpi = base_row["cpi"].values[0]
    cpi["cpi_deflator"] = base_cpi / cpi["cpi"]

    print(f"  CPI range: {cpi['cpi'].min():.1f} to {cpi['cpi'].max():.1f}")
    print(f"  Base period: Dec {end_year} (CPI = {base_cpi:.1f})")
    print(f"  Deflator range: {cpi['cpi_deflator'].min():.3f} to {cpi['cpi_deflator'].max():.3f}")

    return cpi[["year_month", "cpi", "cpi_deflator"]]


# ==============================================================================
# BUILD PANEL
# ==============================================================================

def build_panel(zhvi, treatment, bls, nfip, cpi, start_year, end_year):
    """
    Merge all datasets into a single zip × month regression panel.

    The ZHVI panel is the backbone — we only keep zip-months that have ZHVI data.
    Treatment, BLS, NFIP, and CPI are left-joined onto it.
    """
    print(f"\n{'=' * 60}")
    print("Building regression panel")
    print(f"{'=' * 60}")

    # Start with ZHVI as backbone
    panel = zhvi.copy()

    # Merge treatment info (zip-level, time-invariant)
    treatment_cols = ["zip", "county_fips", "state_id", "state_name",
                      "population", "density", "n_lomrs",
                      "first_lomr_date", "ever_treated"]
    if "already_treated" in treatment.columns:
        treatment_cols += ["already_treated", "treated_in_window"]
    if "treatment_intensity" in treatment.columns:
        treatment_cols += ["treatment_intensity"]

    panel = panel.merge(treatment[treatment_cols], on="zip", how="left")
    print(f"  After treatment merge: {len(panel):,} rows")

    # Construct event time (months since LOMR)
    lomr_period = panel["first_lomr_date"].dt.to_period("M")
    panel["event_time"] = np.where(
        panel["first_lomr_date"].notna(),
        (panel["year_month"] - lomr_period).apply(lambda x: x.n if pd.notna(x) else np.nan),
        np.nan,
    )

    # Construct treatment indicator: treated_z,t = 1 if zip has LOMR by month t
    panel["treated"] = np.where(
        panel["first_lomr_date"].notna() & (panel["date"] >= panel["first_lomr_date"]),
        1, 0
    )

    # Merge BLS unemployment (via county_fips)
    panel = panel.merge(bls, on=["county_fips", "year_month"], how="left")
    n_bls_matched = panel["unemployment_rate"].notna().sum()
    print(f"  BLS unemployment matched: {n_bls_matched:,}/{len(panel):,} "
          f"({n_bls_matched/len(panel)*100:.1f}%)")

    # Merge NFIP panel
    nfip_cols = ["zip", "year_month", "n_policies", "total_premium",
                 "avg_premium", "sfha_share", "n_claims", "total_paid"]
    nfip_merge = nfip[[c for c in nfip_cols if c in nfip.columns]].copy()
    panel = panel.merge(nfip_merge, on=["zip", "year_month"], how="left")
    n_nfip_matched = panel["n_policies"].notna().sum()
    print(f"  NFIP data matched: {n_nfip_matched:,}/{len(panel):,} "
          f"({n_nfip_matched/len(panel)*100:.1f}%)")

    # Fill missing NFIP with 0 (zip-months with no policies/claims)
    for col in ["n_policies", "total_premium", "avg_premium", "sfha_share",
                "n_claims", "total_paid"]:
        if col in panel.columns:
            panel[col] = panel[col].fillna(0)

    # Deflate ZHVI to constant dollars
    if cpi is not None:
        panel = panel.merge(cpi[["year_month", "cpi_deflator"]], on="year_month", how="left")
        panel["real_zhvi"] = panel["zhvi"] * panel["cpi_deflator"]
        panel["ln_real_zhvi"] = np.log(panel["real_zhvi"])
        n_deflated = panel["real_zhvi"].notna().sum()
        print(f"  CPI deflation applied: {n_deflated:,}/{len(panel):,} rows")
        panel = panel.drop(columns=["cpi_deflator"])

    # Compute policy intensity: pre-LOMR avg policies / population (matches Stata)
    pre_mask = (panel["event_time"] < 0) | (panel["ever_treated"] == 0)
    pre_policies = panel.loc[pre_mask].groupby("zip")["n_policies"].mean()
    pre_policies.name = "_pre_policies"
    panel = panel.merge(pre_policies, on="zip", how="left")
    panel["policy_intensity"] = panel["_pre_policies"] / panel["population"]
    panel.loc[panel["policy_intensity"].isna(), "policy_intensity"] = 0
    panel = panel.drop(columns=["_pre_policies"])

    # Sort
    panel = panel.sort_values(["zip", "year_month"]).reset_index(drop=True)

    print(f"\n  Final panel: {len(panel):,} zip-month observations")
    print(f"  Unique zips: {panel['zip'].nunique():,}")
    print(f"  Date range: {panel['year_month'].min()} to {panel['year_month'].max()}")

    return panel


# ==============================================================================
# COMPUTE SUMMARY STATISTICS
# ==============================================================================

def compute_summary_stats(panel):
    """
    Compute Table 1 summary statistics for all regression variables.

    Reports: N, Mean, Std Dev, Min, P25, Median, P75, Max
    Split by: Full sample, Treated zips, Control zips
    """
    print(f"\n{'=' * 60}")
    print("SUMMARY STATISTICS")
    print(f"{'=' * 60}")

    # Define variables and labels
    variables = [
        ("real_zhvi", "Home Value Index (Dec 2022 $)"),
        ("ln_real_zhvi", "ln(Real ZHVI)"),
        ("zhvi", "Home Value Index (nominal $)"),
        ("ln_zhvi", "ln(Nominal ZHVI)"),
        ("treated", "Treated (post-LOMR)"),
        ("ever_treated", "Ever Treated"),
        ("event_time", "Event Time (months since LOMR)"),
        ("n_lomrs", "Number of LOMRs in Zip"),
        ("unemployment_rate", "County Unemployment Rate (%)"),
        ("n_policies", "NFIP Policies (monthly)"),
        ("avg_premium", "NFIP Avg Premium ($)"),
        ("sfha_share", "SFHA Zone Share"),
        ("n_claims", "NFIP Claims (monthly)"),
        ("total_paid", "NFIP Claims Paid ($)"),
        ("policy_intensity", "Policy Intensity (pre-LOMR policies/pop)"),
        ("population", "Zip Population"),
        ("density", "Zip Population Density"),
    ]

    def stats_for_series(s):
        s = s.dropna()
        if len(s) == 0:
            return {k: np.nan for k in ["N", "Mean", "Std Dev", "Min", "P25", "Median", "P75", "Max"]}
        return {
            "N": int(len(s)),
            "Mean": s.mean(),
            "Std Dev": s.std(),
            "Min": s.min(),
            "P25": s.quantile(0.25),
            "Median": s.median(),
            "P75": s.quantile(0.75),
            "Max": s.max(),
        }

    # Full sample
    rows = []
    for col, label in variables:
        if col not in panel.columns:
            continue
        s = stats_for_series(panel[col])
        s["Variable"] = label
        rows.append(s)

    stats_df = pd.DataFrame(rows)
    cols_order = ["Variable", "N", "Mean", "Std Dev", "Min", "P25", "Median", "P75", "Max"]
    stats_df = stats_df[cols_order]

    # Print formatted table
    print(f"\n{'Panel A: Full Sample':^100}")
    print(f"  Zips: {panel['zip'].nunique():,}  |  Zip-months: {len(panel):,}")
    print(f"  Period: {panel['year_month'].min()} to {panel['year_month'].max()}")
    print("-" * 115)
    print(f"{'Variable':<35} {'N':>10} {'Mean':>12} {'Std Dev':>12} {'Min':>12} {'P25':>12} {'Median':>12} {'P75':>12} {'Max':>12}")
    print("-" * 115)
    for _, row in stats_df.iterrows():
        n_str = f"{int(row['N']):,}" if pd.notna(row['N']) else ""
        print(f"{row['Variable']:<35} {n_str:>10} {row['Mean']:>12,.2f} {row['Std Dev']:>12,.2f} "
              f"{row['Min']:>12,.2f} {row['P25']:>12,.2f} {row['Median']:>12,.2f} "
              f"{row['P75']:>12,.2f} {row['Max']:>12,.2f}")
    print("-" * 115)

    # Panel B: By treatment status (ever_treated)
    for group_label, mask in [("Panel B: Ever-Treated Zips", panel["ever_treated"] == 1),
                               ("Panel C: Never-Treated Zips (Control)", panel["ever_treated"] == 0)]:
        sub = panel[mask]
        print(f"\n{group_label:^100}")
        print(f"  Zips: {sub['zip'].nunique():,}  |  Zip-months: {len(sub):,}")
        print("-" * 115)
        print(f"{'Variable':<35} {'N':>10} {'Mean':>12} {'Std Dev':>12} {'Min':>12} {'P25':>12} {'Median':>12} {'P75':>12} {'Max':>12}")
        print("-" * 115)
        for col, label in variables:
            if col not in sub.columns:
                continue
            s = stats_for_series(sub[col])
            n_str = f"{int(s['N']):,}" if pd.notna(s['N']) else ""
            print(f"{label:<35} {n_str:>10} {s['Mean']:>12,.2f} {s['Std Dev']:>12,.2f} "
                  f"{s['Min']:>12,.2f} {s['P25']:>12,.2f} {s['Median']:>12,.2f} "
                  f"{s['P75']:>12,.2f} {s['Max']:>12,.2f}")
        print("-" * 115)

    # Panel D: Treatment timing
    treated_zips = panel[panel["ever_treated"] == 1].drop_duplicates("zip")
    print(f"\n{'Panel D: Treatment Timing':^100}")
    print(f"  Treated zips: {len(treated_zips):,}")
    if len(treated_zips) > 0:
        year_dist = treated_zips["first_lomr_date"].dt.year.value_counts().sort_index()
        print(f"  LOMR year range: {int(year_dist.index.min())} - {int(year_dist.index.max())}")
        print(f"  LOMRs per zip: mean={treated_zips['n_lomrs'].mean():.1f}, "
              f"median={treated_zips['n_lomrs'].median():.0f}")
        print(f"\n  Year distribution of first LOMR:")
        for year, count in year_dist.items():
            bar = "█" * int(count / year_dist.max() * 30)
            print(f"    {int(year)}: {count:>4}  {bar}")

    # Panel E: Fixed effects dimensions
    print(f"\n{'Panel E: Fixed Effects Dimensions':^100}")
    print(f"  Zip fixed effects (α_z):           {panel['zip'].nunique():,} groups")
    print(f"  Calendar-month fixed effects (δ_t): {panel['year_month'].nunique():,} periods")
    if "state_id" in panel.columns:
        print(f"  States represented:                 {panel['state_id'].nunique():,}")
    if "county_fips" in panel.columns:
        print(f"  Counties represented:               {panel['county_fips'].dropna().nunique():,}")

    return stats_df


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute summary statistics for the staggered event study regression"
    )
    parser.add_argument("--start-year", type=int, default=2009)
    parser.add_argument("--end-year", type=int, default=2022)
    parser.add_argument("--threshold", type=str, default="full")
    parser.add_argument("--save-panel", action="store_true",
                        help="Save the merged regression panel to CSV")
    args = parser.parse_args()

    start_year = args.start_year
    end_year = args.end_year

    # Build treatment path
    thresh_str = args.threshold.lower().strip()
    if thresh_str == "full":
        label = "full"
    elif thresh_str.endswith("k"):
        label = thresh_str
    else:
        label = thresh_str
    window = f"_{start_year}-{end_year}"
    treatment_path = TREATMENT_PATH_TEMPLATE.format(label=label, window=window)

    print("Staggered Event Study — Summary Statistics")
    print(f"  Analysis window: {start_year}-{end_year}")
    print(f"  Threshold: {label}")
    print("=" * 60)

    # Check inputs
    for path, name in [(ZHVI_PATH, "ZHVI"), (treatment_path, "Treatment CSV"),
                       (BLS_DATA_PATH, "BLS LAUS"), (NFIP_PANEL_PATH, "NFIP Panel")]:
        if not os.path.exists(path):
            print(f"ERROR: {name} not found: {path}")
            sys.exit(1)

    # Load treatment first (defines zip universe and county FIPS)
    treatment = load_treatment(treatment_path)
    coastal_zips = set(treatment["zip"])
    coastal_fips = set(treatment["county_fips"].dropna())

    # Load all data sources
    zhvi = load_zhvi(ZHVI_PATH, coastal_zips, start_year, end_year)
    bls = load_bls_unemployment(BLS_DATA_PATH, coastal_fips, start_year, end_year)
    nfip = load_nfip_panel(NFIP_PANEL_PATH, coastal_zips, start_year, end_year)

    # Load CPI for deflation
    try:
        cpi = load_cpi(start_year, end_year)
    except Exception as e:
        print(f"  WARNING: Could not load CPI data: {e}")
        print("  Proceeding without deflation.")
        cpi = None

    # Build panel
    panel = build_panel(zhvi, treatment, bls, nfip, cpi, start_year, end_year)

    # Compute and display summary statistics
    stats_df = compute_summary_stats(panel)

    # Save summary stats
    os.makedirs(CLEAN_DIR, exist_ok=True)
    stats_df.to_csv(STATS_PATH, index=False)
    print(f"\nSaved summary statistics: {STATS_PATH}")

    # Optionally save full panel
    if args.save_panel:
        save_panel = panel.copy()
        save_panel["year_month"] = save_panel["year_month"].astype(str)
        save_panel["first_lomr_date"] = save_panel["first_lomr_date"].astype(str)
        save_panel["date"] = save_panel["date"].astype(str)
        save_panel.to_csv(PANEL_PATH, index=False)
        size_mb = os.path.getsize(PANEL_PATH) / 1e6
        print(f"Saved regression panel: {PANEL_PATH} ({size_mb:.1f} MB, {len(panel):,} rows)")

    print("\nDone.")

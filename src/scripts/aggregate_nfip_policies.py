"""
Aggregate NFIP policies and claims to zip x year-month panel, then compute
pre/post LOMR deltas as a proxy for flood risk direction change.

Inputs:
    data/raw/FEMA/nfip/FimaNfipPoliciesV2.csv     (72M rows, 29 GB — chunked read)
    data/raw/FEMA/nfip/FimaNfipClaimsV2.csv        (2.7M rows, 1 GB)
    data/clean/coastal-counties/coastal_zipcodes.csv (coastal zip universe)
    data/clean/coastal_zipcodes_lomr_tr_{label}_{window}.csv (treatment timing)

Outputs:
    data/clean/nfip_zip_month_panel.csv     (zip x year-month: policies, premiums, claims)
    data/clean/nfip_lomr_deltas.csv         (one row per treated zip: pre/post risk proxy)

Usage:
    python src/scripts/aggregate_nfip_policies.py
    python src/scripts/aggregate_nfip_policies.py --threshold 25k --start-year 2009 --end-year 2022
    python src/scripts/aggregate_nfip_policies.py --delta-window 12  # months before/after LOMR
"""

import argparse
import os
import sys
import time

import warnings

import numpy as np
import pandas as pd

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")

# Inputs
POLICIES_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "FEMA", "nfip", "FimaNfipPoliciesV2.csv")
CLAIMS_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "FEMA", "nfip", "FimaNfipClaimsV2.csv")
COASTAL_ZIPS_PATH = os.path.join(PROJECT_ROOT, "data", "clean", "coastal-counties", "coastal_zipcodes.csv")

# Outputs
CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "clean")
PANEL_PATH = os.path.join(CLEAN_DIR, "nfip_zip_month_panel.csv")
DELTAS_PATH = os.path.join(CLEAN_DIR, "nfip_lomr_deltas.csv")

# Processing
CHUNK_SIZE = 500_000

# SFHA flood zones (Special Flood Hazard Area) — mandatory purchase required
# Zones starting with A or V indicate high-risk areas
SFHA_PREFIXES = ("A", "V")


def threshold_label(threshold):
    if threshold <= 0:
        return "full"
    if threshold % 1000 == 0:
        return f"{threshold // 1000}k"
    return str(threshold)


def is_sfha(zone):
    """Return True if flood zone is in a Special Flood Hazard Area (A or V zones)."""
    if not isinstance(zone, str) or not zone.strip():
        return False
    return zone.strip().upper().startswith(SFHA_PREFIXES)


# Top NFIP flood zone categories for zone-level breakdowns
ZONE_BUCKETS = ["AE", "X", "VE", "A", "AH", "AO"]


def classify_zone(zone):
    """Classify a ratedFloodZone string into one of the top zone buckets.

    Bucketing rules:
      - AE: exact "AE"
      - X: "X", "X500", "B", "C" (all minimal-risk designations)
      - VE: exact "VE"
      - A: "A" or numbered A zones (A01-A30, A99)
      - AH: "AH", "AHB"
      - AO: "AO", "AOB"
      - other: everything else (D, AR, V, etc.)

    Returns one of: "AE", "X", "VE", "A", "AH", "AO", "other"
    """
    if not isinstance(zone, str) or not zone.strip():
        return "other"
    z = zone.strip().upper()
    if z == "AE":
        return "AE"
    if z in ("X", "X500", "B", "C"):
        return "X"
    if z == "VE":
        return "VE"
    if z.startswith("AH"):
        return "AH"
    if z.startswith("AO"):
        return "AO"
    # Numbered A zones: A, A01-A30, A99
    if z == "A" or (z.startswith("A") and len(z) <= 3 and z[1:].isdigit()):
        return "A"
    return "other"


# ==============================================================================
# STAGE 1: AGGREGATE POLICIES TO ZIP x MONTH
# ==============================================================================

def aggregate_policies(policies_path, coastal_zips):
    """
    Chunked read of 29 GB NFIP policies file. For each chunk:
      1. Filter to coastal zips
      2. Parse date to year-month
      3. Classify SFHA vs non-SFHA zone
      4. Accumulate zip x month aggregates

    Returns DataFrame with columns: zip, year_month, n_policies, total_premium,
    n_sfha, n_mandatory.
    """
    print(f"\n{'=' * 60}")
    print("STAGE 1: Aggregating NFIP policies (chunked read)")
    print(f"{'=' * 60}")
    print(f"  Source: {policies_path}")
    print(f"  Chunk size: {CHUNK_SIZE:,} rows")
    print(f"  Coastal zips to filter: {len(coastal_zips):,}")

    usecols = [
        "reportedZipCode",
        "policyEffectiveDate",
        "policyCount",
        "totalInsurancePremiumOfThePolicy",
        "ratedFloodZone",
        "mandatoryPurchaseFlag",
    ]

    accum = []
    total_rows = 0
    kept_rows = 0
    n_chunks = 0
    t0 = time.time()

    reader = pd.read_csv(
        policies_path,
        usecols=usecols,
        dtype={"reportedZipCode": str, "ratedFloodZone": str},
        chunksize=CHUNK_SIZE,
    )

    for chunk in reader:
        n_chunks += 1
        total_rows += len(chunk)

        # Filter to coastal zips (drop "Currently Unavailable" and non-coastal)
        chunk = chunk[chunk["reportedZipCode"].isin(coastal_zips)].copy()
        if len(chunk) == 0:
            if n_chunks % 20 == 0:
                elapsed = time.time() - t0
                print(f"  Chunk {n_chunks}: {total_rows:,} rows read, {kept_rows:,} kept ({elapsed:.0f}s)")
            continue

        kept_rows += len(chunk)

        # Parse date to year-month period
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Converting to PeriodArray")
            chunk["year_month"] = pd.to_datetime(
                chunk["policyEffectiveDate"], format="ISO8601", errors="coerce"
            ).dt.to_period("M")
        chunk = chunk.dropna(subset=["year_month"])

        # Classify SFHA
        chunk["is_sfha"] = chunk["ratedFloodZone"].apply(is_sfha).astype(int)

        # Classify into zone buckets (AE, X, VE, A, AH, AO)
        chunk["zone_bucket"] = chunk["ratedFloodZone"].apply(classify_zone)
        for zb in ZONE_BUCKETS:
            chunk[f"is_{zb}"] = (chunk["zone_bucket"] == zb).astype(int)

        # Coerce numeric columns
        chunk["policyCount"] = pd.to_numeric(chunk["policyCount"], errors="coerce").fillna(0).astype(int)
        chunk["totalInsurancePremiumOfThePolicy"] = pd.to_numeric(
            chunk["totalInsurancePremiumOfThePolicy"], errors="coerce"
        ).fillna(0)
        chunk["mandatoryPurchaseFlag"] = pd.to_numeric(
            chunk["mandatoryPurchaseFlag"], errors="coerce"
        ).fillna(0).astype(int)

        # Aggregate this chunk
        agg_dict = {
            "n_policies": ("policyCount", "sum"),
            "total_premium": ("totalInsurancePremiumOfThePolicy", "sum"),
            "n_sfha": ("is_sfha", "sum"),
            "n_mandatory": ("mandatoryPurchaseFlag", "sum"),
        }
        for zb in ZONE_BUCKETS:
            agg_dict[f"n_{zb}"] = (f"is_{zb}", "sum")
        grp = chunk.groupby(["reportedZipCode", "year_month"]).agg(**agg_dict).reset_index()
        accum.append(grp)

        if n_chunks % 20 == 0:
            elapsed = time.time() - t0
            print(f"  Chunk {n_chunks}: {total_rows:,} rows read, {kept_rows:,} kept ({elapsed:.0f}s)")

    elapsed = time.time() - t0
    print(f"\n  Finished: {n_chunks} chunks, {total_rows:,} total rows, {kept_rows:,} coastal rows ({elapsed:.0f}s)")

    # Combine all chunk aggregates and re-aggregate (a zip-month may span chunks)
    print("  Combining chunk aggregates ...")
    combined = pd.concat(accum, ignore_index=True)
    reagg_dict = {
        "n_policies": ("n_policies", "sum"),
        "total_premium": ("total_premium", "sum"),
        "n_sfha": ("n_sfha", "sum"),
        "n_mandatory": ("n_mandatory", "sum"),
    }
    for zb in ZONE_BUCKETS:
        reagg_dict[f"n_{zb}"] = (f"n_{zb}", "sum")
    panel = combined.groupby(["reportedZipCode", "year_month"]).agg(**reagg_dict).reset_index()

    panel = panel.rename(columns={"reportedZipCode": "zip"})
    panel = panel.sort_values(["zip", "year_month"]).reset_index(drop=True)

    # Compute derived columns
    panel["avg_premium"] = np.where(
        panel["n_policies"] > 0,
        panel["total_premium"] / panel["n_policies"],
        0,
    )
    panel["sfha_share"] = np.where(
        panel["n_policies"] > 0,
        panel["n_sfha"] / panel["n_policies"],
        0,
    )
    # Per-zone shares (top 3 zones only — AE, X, VE)
    for zb in ["AE", "X", "VE"]:
        panel[f"share_{zb}"] = np.where(
            panel["n_policies"] > 0,
            panel[f"n_{zb}"] / panel["n_policies"],
            0,
        )

    print(f"  Panel: {len(panel):,} zip-month observations")
    print(f"  Unique zips: {panel['zip'].nunique():,}")
    print(f"  Date range: {panel['year_month'].min()} to {panel['year_month'].max()}")

    return panel


# ==============================================================================
# STAGE 2: AGGREGATE CLAIMS TO ZIP x MONTH
# ==============================================================================

def aggregate_claims(claims_path, coastal_zips):
    """
    Read NFIP claims (2.7M rows, fits in memory) and aggregate to zip x year-month.

    Returns DataFrame with columns: zip, year_month, n_claims, total_paid.
    """
    print(f"\n{'=' * 60}")
    print("STAGE 2: Aggregating NFIP claims")
    print(f"{'=' * 60}")
    print(f"  Source: {claims_path}")

    usecols = [
        "reportedZipCode",
        "dateOfLoss",
        "policyCount",
        "amountPaidOnBuildingClaim",
        "amountPaidOnContentsClaim",
    ]

    claims = pd.read_csv(claims_path, usecols=usecols, dtype={"reportedZipCode": str})
    print(f"  Loaded {len(claims):,} claims")

    # Filter to coastal zips
    claims = claims[claims["reportedZipCode"].isin(coastal_zips)].copy()
    print(f"  Filtered to {len(claims):,} coastal claims")

    # Parse date
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Converting to PeriodArray")
        claims["year_month"] = pd.to_datetime(
            claims["dateOfLoss"], format="ISO8601", errors="coerce"
        ).dt.to_period("M")
    claims = claims.dropna(subset=["year_month"])

    # Coerce numeric
    claims["policyCount"] = pd.to_numeric(claims["policyCount"], errors="coerce").fillna(0).astype(int)
    for col in ["amountPaidOnBuildingClaim", "amountPaidOnContentsClaim"]:
        claims[col] = pd.to_numeric(claims[col], errors="coerce").fillna(0)
    claims["total_paid"] = claims["amountPaidOnBuildingClaim"] + claims["amountPaidOnContentsClaim"]

    # Aggregate
    panel = claims.groupby(["reportedZipCode", "year_month"]).agg(
        n_claims=("policyCount", "sum"),
        total_paid=("total_paid", "sum"),
    ).reset_index()

    panel = panel.rename(columns={"reportedZipCode": "zip"})
    panel = panel.sort_values(["zip", "year_month"]).reset_index(drop=True)

    print(f"  Claims panel: {len(panel):,} zip-month observations")
    print(f"  Unique zips: {panel['zip'].nunique():,}")
    print(f"  Date range: {panel['year_month'].min()} to {panel['year_month'].max()}")

    return panel


# ==============================================================================
# STAGE 3: MERGE PANELS
# ==============================================================================

def merge_panels(policy_panel, claims_panel):
    """Outer-join policy and claims panels on zip x year_month."""
    print(f"\nMerging policy and claims panels ...")

    panel = policy_panel.merge(claims_panel, on=["zip", "year_month"], how="outer")

    # Fill NaN with 0 for missing months
    zone_count_cols = [f"n_{zb}" for zb in ZONE_BUCKETS]
    zone_share_cols = [f"share_{zb}" for zb in ["AE", "X", "VE"]]
    fill_cols = ["n_policies", "total_premium", "n_sfha", "n_mandatory",
                 "avg_premium", "sfha_share", "n_claims", "total_paid"] + \
                zone_count_cols + zone_share_cols
    for col in fill_cols:
        if col in panel.columns:
            panel[col] = panel[col].fillna(0)

    panel = panel.sort_values(["zip", "year_month"]).reset_index(drop=True)
    print(f"  Merged panel: {len(panel):,} zip-month observations, {panel['zip'].nunique():,} zips")

    return panel


# ==============================================================================
# STAGE 4: COMPUTE LOMR DELTAS
# ==============================================================================

def compute_lomr_deltas(panel, treatment_df, delta_window_months=12):
    """
    For each treated zip, compute pre/post LOMR deltas as risk direction proxy.

    For each zip with a LOMR effective date:
      - Pre window: [lomr_date - delta_window, lomr_date)
      - Post window: (lomr_date, lomr_date + delta_window]
      - Delta = mean(post) - mean(pre) for policies, premium, SFHA share, claims

    Positive delta_policies → more people buying insurance → risk likely increased
    Negative delta_policies → fewer policies → risk likely decreased
    """
    print(f"\n{'=' * 60}")
    print(f"STAGE 4: Computing LOMR deltas (±{delta_window_months} months)")
    print(f"{'=' * 60}")

    # Get treated zips with valid LOMR dates
    treated = treatment_df[treatment_df["ever_treated"] == 1].copy()
    treated["first_lomr_date"] = pd.to_datetime(treated["first_lomr_date"], errors="coerce")
    treated = treated.dropna(subset=["first_lomr_date"])
    print(f"  {len(treated):,} treated zips with valid LOMR dates")

    # Convert panel year_month to timestamp for comparison
    panel = panel.copy()
    panel["month_ts"] = panel["year_month"].dt.to_timestamp()

    results = []
    n_insufficient = 0

    for _, row in treated.iterrows():
        zip_code = str(row["zip"])
        lomr_date = row["first_lomr_date"]

        # Define pre/post windows
        pre_start = lomr_date - pd.DateOffset(months=delta_window_months)
        post_end = lomr_date + pd.DateOffset(months=delta_window_months)

        zip_data = panel[panel["zip"] == zip_code]
        if len(zip_data) == 0:
            n_insufficient += 1
            continue

        pre = zip_data[(zip_data["month_ts"] >= pre_start) & (zip_data["month_ts"] < lomr_date)]
        post = zip_data[(zip_data["month_ts"] > lomr_date) & (zip_data["month_ts"] <= post_end)]

        # Require at least 3 months in each window
        if len(pre) < 3 or len(post) < 3:
            n_insufficient += 1
            continue

        result = {
            "zip": zip_code,
            "first_lomr_date": lomr_date,
            "pre_months": len(pre),
            "post_months": len(post),
            # Policy deltas
            "pre_avg_policies": pre["n_policies"].mean(),
            "post_avg_policies": post["n_policies"].mean(),
            "delta_policies": post["n_policies"].mean() - pre["n_policies"].mean(),
            # Premium deltas
            "pre_avg_premium": pre["avg_premium"].mean(),
            "post_avg_premium": post["avg_premium"].mean(),
            "delta_premium": post["avg_premium"].mean() - pre["avg_premium"].mean(),
            # SFHA share deltas
            "pre_avg_sfha_share": pre["sfha_share"].mean(),
            "post_avg_sfha_share": post["sfha_share"].mean(),
            "delta_sfha_share": post["sfha_share"].mean() - pre["sfha_share"].mean(),
            # Raw SFHA counts
            "pre_n_sfha": pre["n_sfha"].mean(),
            "post_n_sfha": post["n_sfha"].mean(),
            # Claims deltas
            "pre_avg_claims": pre["n_claims"].mean(),
            "post_avg_claims": post["n_claims"].mean(),
            "delta_claims": post["n_claims"].mean() - pre["n_claims"].mean(),
        }
        # Per-zone share deltas (AE, X, VE)
        for zb in ["AE", "X", "VE"]:
            col = f"share_{zb}"
            if col in pre.columns:
                result[f"pre_share_{zb}"] = pre[col].mean()
                result[f"post_share_{zb}"] = post[col].mean()
                result[f"delta_share_{zb}"] = post[col].mean() - pre[col].mean()
            else:
                result[f"pre_share_{zb}"] = 0
                result[f"post_share_{zb}"] = 0
                result[f"delta_share_{zb}"] = 0
        results.append(result)

    deltas = pd.DataFrame(results)

    if len(deltas) > 0:
        # Classify risk direction based on policy delta sign (legacy)
        deltas["risk_direction"] = np.where(
            deltas["delta_policies"] > 0, "up",
            np.where(deltas["delta_policies"] < 0, "down", "flat")
        )

        # Classify zone-based risk direction from SFHA share change (>1pp threshold)
        deltas["zone_risk_direction"] = np.where(
            deltas["delta_sfha_share"] > 0.01, "up",
            np.where(deltas["delta_sfha_share"] < -0.01, "down", "stable")
        )

    n_computed = len(deltas)
    print(f"  Computed deltas for {n_computed:,} zips")
    print(f"  Insufficient data for {n_insufficient:,} zips (< 3 months in pre or post window)")

    if len(deltas) > 0:
        # Legacy policy-count-based direction
        n_up = (deltas["risk_direction"] == "up").sum()
        n_down = (deltas["risk_direction"] == "down").sum()
        n_flat = (deltas["risk_direction"] == "flat").sum()
        print(f"\n  Risk direction (policy-count-based, legacy):")
        print(f"    Up (more policies post-LOMR):   {n_up:,} ({n_up/n_computed*100:.1f}%)")
        print(f"    Down (fewer policies post-LOMR): {n_down:,} ({n_down/n_computed*100:.1f}%)")
        print(f"    Flat (no change):                {n_flat:,} ({n_flat/n_computed*100:.1f}%)")

        # Zone-based direction
        z_up = (deltas["zone_risk_direction"] == "up").sum()
        z_down = (deltas["zone_risk_direction"] == "down").sum()
        z_stable = (deltas["zone_risk_direction"] == "stable").sum()
        print(f"\n  Zone risk direction (SFHA share change, ±1pp threshold):")
        print(f"    Up (SFHA share increased):  {z_up:,} ({z_up/n_computed*100:.1f}%)")
        print(f"    Down (SFHA share decreased): {z_down:,} ({z_down/n_computed*100:.1f}%)")
        print(f"    Stable (< 1pp change):       {z_stable:,} ({z_stable/n_computed*100:.1f}%)")

        # Cross-tab: old vs new classification
        print(f"\n  Cross-tabulation — risk_direction (rows) vs zone_risk_direction (cols):")
        xtab = pd.crosstab(deltas["risk_direction"], deltas["zone_risk_direction"], margins=True)
        print(xtab.to_string(col_space=10))

        print(f"\n  Delta statistics:")
        print(f"    delta_policies:   mean={deltas['delta_policies'].mean():.2f}, "
              f"median={deltas['delta_policies'].median():.2f}")
        print(f"    delta_premium:    mean={deltas['delta_premium'].mean():.2f}, "
              f"median={deltas['delta_premium'].median():.2f}")
        print(f"    delta_sfha_share: mean={deltas['delta_sfha_share'].mean():.4f}, "
              f"median={deltas['delta_sfha_share'].median():.4f}")
        print(f"    delta_share_AE:   mean={deltas['delta_share_AE'].mean():.4f}, "
              f"median={deltas['delta_share_AE'].median():.4f}")
        print(f"    delta_share_X:    mean={deltas['delta_share_X'].mean():.4f}, "
              f"median={deltas['delta_share_X'].median():.4f}")
        print(f"    delta_share_VE:   mean={deltas['delta_share_VE'].mean():.4f}, "
              f"median={deltas['delta_share_VE'].median():.4f}")
        print(f"    delta_claims:     mean={deltas['delta_claims'].mean():.2f}, "
              f"median={deltas['delta_claims'].median():.2f}")

    return deltas


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Aggregate NFIP policies/claims to zip x month panel and compute LOMR risk deltas"
    )
    parser.add_argument(
        "--threshold", type=str, default="full",
        help="Population threshold label matching the treatment CSV"
    )
    parser.add_argument(
        "--start-year", type=int, default=None,
        help="Start of analysis window (matches treatment CSV filename)"
    )
    parser.add_argument(
        "--end-year", type=int, default=None,
        help="End of analysis window"
    )
    parser.add_argument(
        "--delta-window", type=int, default=12,
        help="Months before/after LOMR for delta computation (default: 12)"
    )
    parser.add_argument(
        "--skip-panel", action="store_true",
        help="Skip panel construction, load existing panel from disk"
    )
    args = parser.parse_args()

    # Parse threshold
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
    delta_window = args.delta_window

    # Build treatment CSV path
    window_suffix = ""
    if start_year or end_year:
        window_suffix = f"_{start_year or 'x'}-{end_year or 'x'}"
    treatment_path = os.path.join(CLEAN_DIR, f"coastal_zipcodes_lomr_tr_{label}{window_suffix}.csv")

    print("NFIP Policy/Claims Aggregation & LOMR Delta Computation")
    print(f"  Threshold: {label}")
    if start_year or end_year:
        print(f"  Analysis window: {start_year or '...'}-{end_year or '...'}")
    print(f"  Delta window: ±{delta_window} months")
    print("=" * 60)

    # Check inputs
    for path, name in [(POLICIES_PATH, "NFIP Policies"), (CLAIMS_PATH, "NFIP Claims"),
                       (COASTAL_ZIPS_PATH, "Coastal zips"), (treatment_path, "Treatment CSV")]:
        if not os.path.exists(path):
            print(f"ERROR: {name} not found: {path}")
            sys.exit(1)

    # Load coastal zip set
    print(f"\nLoading coastal zips from: {COASTAL_ZIPS_PATH}")
    coastal_df = pd.read_csv(COASTAL_ZIPS_PATH, dtype={"zip": str})
    coastal_zips = set(coastal_df["zip"])
    print(f"  {len(coastal_zips):,} coastal zips")

    if args.skip_panel and os.path.exists(PANEL_PATH):
        # Load existing panel
        print(f"\nLoading existing panel from: {PANEL_PATH}")
        panel = pd.read_csv(PANEL_PATH, dtype={"zip": str})
        panel["year_month"] = pd.PeriodIndex(panel["year_month"], freq="M")
        print(f"  {len(panel):,} zip-month rows")
    else:
        # Stage 1: Policies
        policy_panel = aggregate_policies(POLICIES_PATH, coastal_zips)

        # Stage 2: Claims
        claims_panel = aggregate_claims(CLAIMS_PATH, coastal_zips)

        # Stage 3: Merge
        panel = merge_panels(policy_panel, claims_panel)

        # Save panel
        os.makedirs(CLEAN_DIR, exist_ok=True)
        save_panel = panel.copy()
        save_panel["year_month"] = save_panel["year_month"].astype(str)
        save_panel.to_csv(PANEL_PATH, index=False)
        size_mb = os.path.getsize(PANEL_PATH) / 1e6
        print(f"\n  Saved panel: {PANEL_PATH} ({size_mb:.1f} MB, {len(panel):,} rows)")

    # Stage 4: Compute LOMR deltas
    print(f"\nLoading treatment data from: {treatment_path}")
    treatment_df = pd.read_csv(treatment_path, dtype={"zip": str})
    print(f"  {len(treatment_df):,} zips, {(treatment_df['ever_treated'] == 1).sum():,} treated")

    deltas = compute_lomr_deltas(panel, treatment_df, delta_window_months=delta_window)

    # Save deltas
    if len(deltas) > 0:
        deltas.to_csv(DELTAS_PATH, index=False)
        size_mb = os.path.getsize(DELTAS_PATH) / 1e6
        print(f"\n  Saved deltas: {DELTAS_PATH} ({size_mb:.2f} MB, {len(deltas):,} rows)")
    else:
        print("\n  WARNING: No deltas computed (no treated zips with sufficient NFIP data)")

    print(f"\nDone. Outputs:")
    print(f"  {PANEL_PATH}")
    print(f"  {DELTAS_PATH}")

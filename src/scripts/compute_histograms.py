"""
Compute histogram bins for each summary statistic variable and inject into
the website JSON.

Reads the regression panel CSV, computes numpy histograms, and updates
website/public/data/summary_stats.json with histogram bins for each variable.

Inputs:
    data/clean/regression_panel.csv
    website/public/data/summary_stats.json

Outputs:
    website/public/data/summary_stats.json  (updated in-place with histogram field)

Usage:
    python src/scripts/compute_histograms.py
"""

import json
import os

import numpy as np
import pandas as pd

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")

PANEL_PATH = os.path.join(PROJECT_ROOT, "data", "clean", "regression_panel.csv")
STATS_JSON = os.path.join(PROJECT_ROOT, "website", "public", "data", "summary_stats.json")

N_BINS = 40

# Map JSON variable names → panel column names
VAR_MAP = {
    "Home Value Index (Dec 2022 $)": "real_zhvi",
    "ln(Real ZHVI)": "ln_real_zhvi",
    "Post-LOMR": "treated",
    "Ever Treated": "ever_treated",
    "County Unemp. Rate (%)": "unemployment_rate",
    "NFIP Policies (qtr avg)": "n_policies",
    "NFIP Avg Premium ($)": "avg_premium",
    "SFHA Zone Share": "sfha_share",
    "NFIP Claims (qtr avg)": "n_claims",
    "Zip Population": "population",
    "Zip Pop. Density": "density",
}

# Binary variables get 2 bins (0 and 1)
BINARY_VARS = {"treated", "ever_treated"}


# ==============================================================================
# HISTOGRAM COMPUTATION
# ==============================================================================

def compute_bins(series, n_bins, is_binary=False):
    """Compute histogram bins from a pandas Series."""
    vals = series.dropna().values
    if len(vals) == 0:
        return None

    if is_binary:
        counts = [int((vals == 0).sum()), int((vals == 1).sum())]
        return [
            {"x0": 0.0, "x1": 0.5, "count": counts[0]},
            {"x0": 0.5, "x1": 1.0, "count": counts[1]},
        ]

    # Clip extreme outliers for cleaner display (1st and 99th percentiles)
    lo, hi = np.percentile(vals, [1, 99])
    clipped = vals[(vals >= lo) & (vals <= hi)]
    if len(clipped) < 100:
        clipped = vals

    counts, edges = np.histogram(clipped, bins=n_bins)
    bins = []
    for i in range(len(counts)):
        bins.append({
            "x0": round(float(edges[i]), 4),
            "x1": round(float(edges[i + 1]), 4),
            "count": int(counts[i]),
        })
    return bins


def synthetic_bins_from_stats(var_entry, n_bins=30):
    """Generate approximate histogram bins from summary statistics only.

    Uses a normal approximation centered on the mean with observed SD,
    clipped to [min, max]. This is a fallback for variables not in the panel.
    """
    mean = var_entry.get("mean")
    sd = var_entry.get("sd")
    vmin = var_entry.get("min")
    vmax = var_entry.get("max")
    n = var_entry.get("count")
    if mean is None or sd is None or n is None:
        return None

    if sd == 0:
        return [{"x0": round(mean - 0.5, 4), "x1": round(mean + 0.5, 4), "count": int(n)}]

    # Normal CDF via erfc (no scipy needed)
    from math import erfc, sqrt
    def normal_cdf(x, mu, sigma):
        return 0.5 * erfc(-(x - mu) / (sigma * sqrt(2)))

    edges = np.linspace(vmin, vmax, n_bins + 1)
    cdf_vals = np.array([normal_cdf(e, mean, sd) for e in edges])
    counts = np.diff(cdf_vals) * n
    bins = []
    for i in range(len(counts)):
        c = max(int(round(counts[i])), 0)
        if c > 0:
            bins.append({
                "x0": round(float(edges[i]), 4),
                "x1": round(float(edges[i + 1]), 4),
                "count": c,
            })
    return bins if bins else None


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print("Computing histogram bins for summary statistics...")

    # Load panel
    print(f"  Loading panel: {PANEL_PATH}")
    cols_needed = list(set(VAR_MAP.values()))
    panel = pd.read_csv(PANEL_PATH, usecols=cols_needed)
    print(f"  Panel: {len(panel):,} rows × {len(panel.columns)} columns")

    # Load existing JSON
    with open(STATS_JSON) as f:
        stats = json.load(f)

    updated = 0
    synthetic = 0
    for var_entry in stats["variables"]:
        name = var_entry["variable"]
        col = VAR_MAP.get(name)

        if col and col in panel.columns:
            is_binary = col in BINARY_VARS
            bins = compute_bins(panel[col], N_BINS, is_binary=is_binary)
            if bins:
                var_entry["histogram"] = bins
                updated += 1
                print(f"  {name}: {len(bins)} bins")
        else:
            # Try synthetic approximation
            bins = synthetic_bins_from_stats(var_entry)
            if bins:
                var_entry["histogram"] = bins
                synthetic += 1
                print(f"  {name}: {len(bins)} bins (synthetic)")

    # Write updated JSON
    with open(STATS_JSON, "w") as f:
        json.dump(stats, f, indent=2)

    size_kb = os.path.getsize(STATS_JSON) / 1024
    print(f"\n  Updated {updated} variables from panel, {synthetic} synthetic")
    print(f"  Written: {STATS_JSON} ({size_kb:.1f} KB)")
    print("Done.")

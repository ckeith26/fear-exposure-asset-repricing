"""
Plot LOMR treatment timing for staggered DiD visualization.

Inputs:
    data/clean/coastal_zipcodes_lomr_tr_{label}.csv

Outputs:
    data/clean/plots/treatment_timing_{label}.png

Usage:
    python src/scripts/plot_treatment_timing.py
    python src/scripts/plot_treatment_timing.py --threshold 25k
    python src/scripts/plot_treatment_timing.py --threshold 25k --start-year 2009 --end-year 2022
"""

import argparse
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "clean")
PLOT_DIR = os.path.join(CLEAN_DIR, "plots")

ZHVI_PATH = os.path.join(RAW_DIR, "zhvi", "Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv")


def threshold_label(threshold):
    if threshold <= 0:
        return "full"
    if threshold % 1000 == 0:
        return f"{threshold // 1000}k"
    return str(threshold)


def load_zhvi_at_treatment(treated_df):
    """Load ZHVI and look up each treated zip's home value at its first LOMR date.

    Returns treated_df with a new `zhvi_at_treatment` column (NaN where missing).
    """
    if not os.path.exists(ZHVI_PATH):
        print(f"  ZHVI file not found ({ZHVI_PATH}), skipping home-value panel")
        return treated_df

    print("Loading ZHVI zip-level data...")
    zhvi = pd.read_csv(ZHVI_PATH, dtype={"RegionName": str})

    # Identify date columns (YYYY-MM-DD format)
    date_cols = [c for c in zhvi.columns if len(c) == 10 and c[4] == "-"]
    date_timestamps = pd.to_datetime(date_cols)

    # Zero-pad zip codes to 5 digits
    zhvi["RegionName"] = zhvi["RegionName"].str.zfill(5)

    # Keep only zips we need
    zhvi_subset = zhvi[zhvi["RegionName"].isin(treated_df["zip"])].copy()
    zhvi_subset = zhvi_subset.set_index("RegionName")
    print(f"  Matched {len(zhvi_subset):,} of {len(treated_df):,} treated zips in ZHVI")

    # For each treated zip, find the ZHVI column closest to its first_lomr_date
    values = []
    for _, row in treated_df.iterrows():
        z = row["zip"]
        lomr_dt = row["first_lomr_date"]
        if z not in zhvi_subset.index or pd.isna(lomr_dt):
            values.append(np.nan)
            continue
        # Find nearest date column
        idx = np.argmin(np.abs(date_timestamps - lomr_dt))
        val = zhvi_subset.loc[z, date_cols[idx]]
        values.append(val)

    treated_df = treated_df.copy()
    treated_df["zhvi_at_treatment"] = values
    n_valid = treated_df["zhvi_at_treatment"].notna().sum()
    print(f"  ZHVI matched for {n_valid:,} treated zips ({n_valid / len(treated_df):.0%})")
    return treated_df


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot LOMR treatment timing")
    parser.add_argument(
        "--threshold", type=str, default="full",
        help="Population threshold label matching the treatment CSV"
    )
    parser.add_argument(
        "--start-year", type=int, default=None,
        help="Start of analysis window (highlights window on plots, matches overlay CSV)"
    )
    parser.add_argument(
        "--end-year", type=int, default=None,
        help="End of analysis window"
    )
    args = parser.parse_args()

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

    # Match filename from overlay script
    window_suffix = ""
    if start_year or end_year:
        window_suffix = f"_{start_year or 'x'}-{end_year or 'x'}"
    input_path = os.path.join(CLEAN_DIR, f"coastal_zipcodes_lomr_tr_{label}{window_suffix}.csv")

    # Fall back to non-windowed file if windowed version doesn't exist
    if not os.path.exists(input_path) and window_suffix:
        fallback = os.path.join(CLEAN_DIR, f"coastal_zipcodes_lomr_tr_{label}.csv")
        if os.path.exists(fallback):
            print(f"  Windowed file not found, using: {fallback}")
            input_path = fallback

    print(f"Loading: {input_path}")
    if not os.path.exists(input_path):
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    df = pd.read_csv(input_path, dtype={"zip": str})
    df["first_lomr_date"] = pd.to_datetime(df["first_lomr_date"])

    treated = df[df["ever_treated"] == 1].copy()
    treated = load_zhvi_at_treatment(treated)
    has_zhvi = "zhvi_at_treatment" in treated.columns and treated["zhvi_at_treatment"].notna().any()
    n_treated = len(treated)
    n_control = len(df[df["ever_treated"] == 0])

    # Window-aware stats
    has_window_cols = "already_treated" in df.columns
    if has_window_cols:
        n_already = (df["already_treated"] == 1).sum()
        n_in_window = (df["treated_in_window"] == 1).sum()
        print(f"  {n_treated:,} treated total ({n_already:,} pre-window, {n_in_window:,} in-window), {n_control:,} control")
    else:
        print(f"  {n_treated:,} treated, {n_control:,} control zips")

    window_label = f" ({start_year}-{end_year})" if start_year and end_year else ""

    # === BUILD FIGURE ===
    n_panels = 4 if has_zhvi else 3
    fig, axes = plt.subplots(n_panels, 1, figsize=(12, 4 * n_panels),
                             gridspec_kw={"hspace": 0.35})
    fig.suptitle(f"LOMR Treatment Timing — {label} threshold{window_label}",
                 fontsize=14, fontweight="bold", y=0.97)

    # --- Panel 1: Annual histogram of first LOMR dates ---
    ax1 = axes[0]
    treated["year"] = treated["first_lomr_date"].dt.year
    year_counts = treated["year"].value_counts().sort_index()

    # Color bars inside vs outside window
    if start_year or end_year:
        colors = []
        for y in year_counts.index:
            in_window = True
            if start_year and y < start_year:
                in_window = False
            if end_year and y > end_year:
                in_window = False
            colors.append("#2196F3" if in_window else "#BDBDBD")
        ax1.bar(year_counts.index, year_counts.values, color=colors, edgecolor="white", linewidth=0.5)
    else:
        ax1.bar(year_counts.index, year_counts.values, color="#2196F3", edgecolor="white", linewidth=0.5)

    ax1.set_xlabel("Year")
    ax1.set_ylabel("Zip codes entering treatment")
    ax1.set_title("New treated zip codes by year (first LOMR date)")
    ax1.axvline(x=2005, color="red", linestyle="--", alpha=0.6, label="Hurricane Katrina (2005)")
    ax1.axvline(x=2012, color="orange", linestyle="--", alpha=0.6, label="Hurricane Sandy (2012)")

    # Shade analysis window
    if start_year and end_year:
        ax1.axvspan(start_year - 0.5, end_year + 0.5, alpha=0.08, color="green",
                     label=f"Analysis window ({start_year}-{end_year})")
    ax1.legend(fontsize=9)

    # --- Panel 2: Cumulative treatment adoption ---
    ax2 = axes[1]
    sorted_dates = treated["first_lomr_date"].sort_values().reset_index(drop=True)
    cumulative = range(1, len(sorted_dates) + 1)
    ax2.plot(sorted_dates, cumulative, color="#4CAF50", linewidth=2)
    ax2.fill_between(sorted_dates, cumulative, alpha=0.15, color="#4CAF50")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Cumulative treated zip codes")
    ax2.set_title("Cumulative treatment adoption over time")
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.axhline(y=n_treated, color="gray", linestyle=":", alpha=0.5)
    ax2.text(sorted_dates.iloc[0], n_treated * 1.02, f"Total: {n_treated}", fontsize=9, color="gray")

    # Shade analysis window
    if start_year and end_year:
        ax2.axvspan(pd.Timestamp(f"{start_year}-01-01"), pd.Timestamp(f"{end_year}-12-31"),
                     alpha=0.08, color="green")

    # --- Panel 3: Treatment vs control balance over time ---
    ax3 = axes[2]
    plot_start = start_year if start_year else int(year_counts.index.min())
    plot_end = end_year if end_year else int(year_counts.index.max())
    years = range(plot_start, plot_end + 1)
    cum_treated = []
    cum_control = []
    cum_already = []
    total = len(df)
    for y in years:
        n_tr = (treated["first_lomr_date"].dt.year <= y).sum()
        cum_treated.append(n_tr)
        cum_control.append(total - n_tr)

    years_list = list(years)

    # If we have window info, split treated into already-treated and in-window
    if has_window_cols and start_year:
        already_treated = treated[treated.get("already_treated", pd.Series(dtype=int)) == 1] if "already_treated" in treated.columns else pd.DataFrame()
        n_already_total = len(already_treated)
        in_window_treated = []
        for y in years:
            n_iw = (treated["first_lomr_date"].dt.year <= y).sum() - n_already_total
            in_window_treated.append(max(0, n_iw))

        ax3.stackplot(years_list,
                      [n_already_total] * len(years_list),
                      in_window_treated,
                      cum_control,
                      labels=[f"Already treated (pre-{start_year})",
                              "Treated in window", "Control (no LOMR yet)"],
                      colors=["#FFAB91", "#FF7043", "#90CAF9"], alpha=0.85)
    else:
        ax3.stackplot(years_list, cum_treated, cum_control,
                      labels=["Treated (any LOMR)", "Control (no LOMR yet)"],
                      colors=["#FF7043", "#90CAF9"], alpha=0.85)

    ax3.set_xlabel("Year")
    ax3.set_ylabel("Zip codes")
    ax3.set_title("Treatment vs. control balance over time")
    ax3.legend(loc="center right", fontsize=9)

    # --- Panel 4: ZHVI at treatment scatter ---
    if has_zhvi:
        ax4 = axes[3]
        scatter_df = treated.dropna(subset=["zhvi_at_treatment"]).copy()

        # Log scale for color — home values span orders of magnitude
        vals = scatter_df["zhvi_at_treatment"]
        norm = mcolors.LogNorm(vmin=vals.quantile(0.01), vmax=vals.quantile(0.99))

        sc = ax4.scatter(
            scatter_df["first_lomr_date"],
            scatter_df["zhvi_at_treatment"],
            c=scatter_df["zhvi_at_treatment"],
            cmap="RdYlGn",
            norm=norm,
            alpha=0.6, s=18, edgecolors="none",
        )
        cbar = fig.colorbar(sc, ax=ax4, pad=0.02)
        cbar.set_label("ZHVI ($)", fontsize=10)

        ax4.set_yscale("log")
        ax4.set_xlabel("First LOMR date")
        ax4.set_ylabel("ZHVI at treatment ($)")
        ax4.set_title("Home values at treatment — ZHVI by zip code at first LOMR date")
        ax4.xaxis.set_major_locator(mdates.YearLocator(2))
        ax4.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        # Format y-axis ticks as dollar amounts
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

        # Shade analysis window
        if start_year and end_year:
            ax4.axvspan(pd.Timestamp(f"{start_year}-01-01"), pd.Timestamp(f"{end_year}-12-31"),
                         alpha=0.08, color="green")

        # Annotate coverage
        n_scatter = len(scatter_df)
        ax4.text(0.02, 0.95, f"{n_scatter:,} zips with ZHVI data ({n_scatter / n_treated:.0%} of treated)",
                 transform=ax4.transAxes, fontsize=9, color="gray", va="top")

    # Save
    os.makedirs(PLOT_DIR, exist_ok=True)
    out_path = os.path.join(PLOT_DIR, f"treatment_timing_{label}{window_suffix}.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nSaved: {out_path}")
    plt.close()

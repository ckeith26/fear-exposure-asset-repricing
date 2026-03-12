"""
Clean county-level presidential election returns for merge with regression panel.

Inputs:
    data/raw/election-returns/countypres_2000-2024.tab  (MIT Election Lab via Dataverse)

Outputs:
    data/clean/election_county_year.csv
        county_fips     — 5-digit zero-padded string (merge key)
        year            — integer (2009–2022, forward-filled from election years)
        rep_share       — Republican two-party vote share: R / (R + D)
        margin          — Republican margin: (R - D) / total votes
        turnout         — total votes cast (election years only; NaN in off-years)
        election_year   — nearest prior election year (source of forward-fill)

Usage:
    python src/scripts/clean_election_returns.py
"""

import os
import pandas as pd

# ==============================================================================
# CONFIGURATION
# ==============================================================================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INPUT_FILE = os.path.join(PROJECT_ROOT, "data", "raw", "election-returns",
                          "countypres_2000-2024.tab")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "clean", "election_county_year.csv")

# Panel years to fill (match regression panel window)
PANEL_START = 2009
PANEL_END = 2022


# ==============================================================================
# LOAD AND FILTER
# ==============================================================================

print("Clean Election Returns")
print("=" * 60)

df = pd.read_csv(INPUT_FILE, sep="\t", dtype={"county_fips": str})
print(f"  Loaded {len(df):,} rows, {df['year'].nunique()} election years")

# Filter to TOTAL mode (avoid double-counting absentee/election-day splits)
if "mode" in df.columns:
    modes = df["mode"].str.strip('"').unique()
    print(f"  Vote modes present: {modes}")
    df["mode"] = df["mode"].str.strip('"')
    df = df[df["mode"] == "TOTAL"]
    print(f"  Filtered to TOTAL mode: {len(df):,} rows")

# Strip quotes from string columns
for col in ["state", "county_name", "party", "candidate", "state_po"]:
    if col in df.columns:
        df[col] = df[col].str.strip('"')

# Drop rows with missing county_fips (write-ins, overseas, etc.)
n_before = len(df)
df = df.dropna(subset=["county_fips"])
df["county_fips"] = df["county_fips"].astype(float).astype(int).astype(str).str.zfill(5)
n_dropped = n_before - len(df)
if n_dropped > 0:
    print(f"  Dropped {n_dropped} rows with missing county_fips")


# ==============================================================================
# COMPUTE VOTE SHARES PER COUNTY × ELECTION YEAR
# ==============================================================================

print("\n--- Computing vote shares ---")

# Pivot to get R and D votes per county-year
party_votes = (
    df[df["party"].isin(["REPUBLICAN", "DEMOCRAT"])]
    .groupby(["county_fips", "year", "party"])["candidatevotes"]
    .sum()
    .unstack("party")
    .rename(columns={"REPUBLICAN": "r_votes", "DEMOCRAT": "d_votes"})
    .reset_index()
)

# Total votes per county-year (all candidates)
totals = (
    df.groupby(["county_fips", "year"])["totalvotes"]
    .first()  # totalvotes is repeated per candidate row
    .reset_index()
    .rename(columns={"totalvotes": "turnout"})
)

elect = party_votes.merge(totals, on=["county_fips", "year"], how="left")

# Republican two-party vote share: R / (R + D)
elect["rep_share"] = elect["r_votes"] / (elect["r_votes"] + elect["d_votes"])

# Republican margin: (R - D) / total
elect["margin"] = (elect["r_votes"] - elect["d_votes"]) / elect["turnout"]

elect = elect[["county_fips", "year", "rep_share", "margin", "turnout"]].copy()

print(f"  Election-year observations: {len(elect):,}")
print(f"  Unique counties: {elect['county_fips'].nunique():,}")
print(f"  Election years: {sorted(elect['year'].unique())}")
print(f"  Mean Republican two-party share: {elect['rep_share'].mean():.3f}")


# ==============================================================================
# FORWARD-FILL TO ANNUAL PANEL
# ==============================================================================

print("\n--- Forward-filling to annual panel ---")

# Create full county × year grid for panel window
counties = elect["county_fips"].unique()
years = range(PANEL_START, PANEL_END + 1)
grid = pd.MultiIndex.from_product([counties, years], names=["county_fips", "year"])
grid = pd.DataFrame(index=grid).reset_index()

# Merge election-year data onto grid
panel = grid.merge(elect, on=["county_fips", "year"], how="left")

# Forward-fill within each county (last election result carries forward)
# Sort to ensure elections before panel start (2008, 2004, ...) are available
elect_all = elect.copy()
panel_plus = pd.concat([elect_all, panel]).drop_duplicates(subset=["county_fips", "year"])
panel_plus = panel_plus.sort_values(["county_fips", "year"])
panel_plus[["rep_share", "margin"]] = (
    panel_plus.groupby("county_fips")[["rep_share", "margin"]].ffill()
)

# Restrict back to panel window
panel = panel_plus[
    (panel_plus["year"] >= PANEL_START) & (panel_plus["year"] <= PANEL_END)
].copy()

# Track which election year each row comes from
panel["election_year"] = panel["year"].where(panel["turnout"].notna())
panel["election_year"] = panel.groupby("county_fips")["election_year"].ffill()
panel["election_year"] = panel["election_year"].astype("Int64")

# Turnout only meaningful in election years; NaN in off-years
print(f"  Panel rows: {len(panel):,}")
print(f"  Missing rep_share after fill: {panel['rep_share'].isna().sum()}")


# ==============================================================================
# SAVE
# ==============================================================================

out = panel[["county_fips", "year", "rep_share", "margin", "turnout", "election_year"]]
out = out.sort_values(["county_fips", "year"]).reset_index(drop=True)

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)

print(f"\n  Saved: {OUTPUT_FILE}")
print(f"  Shape: {out.shape[0]:,} rows × {out.shape[1]} columns")

# Quick summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Counties:    {out['county_fips'].nunique():,}")
print(f"  Years:       {out['year'].min()}–{out['year'].max()}")
print(f"  Rep share:   mean={out['rep_share'].mean():.3f}, "
      f"sd={out['rep_share'].std():.3f}")
print(f"  Margin:      mean={out['margin'].mean():.3f}, "
      f"sd={out['margin'].std():.3f}")
print(f"\n  Merge key: county_fips (5-digit, zero-padded) × year")
print("=" * 60)

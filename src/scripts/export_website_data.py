"""
Export research output data as optimized JSON for the static website.

Reads existing output CSVs from output/results/ and writes structured JSON
files to website/public/data/ for consumption by the Next.js frontend.
Also copies static images (Bacon, CS, parallel trends, maps) to website/public/images/.

Inputs:
    output/results/s05_event_study_coefficients.csv
    output/results/s06_event_study_intensity_coefficients.csv
    output/results/s09_event_study_updown_coefficients.csv
    output/results/s08_event_study_policies_coefficients.csv
    output/results/s09b_event_study_disclosure_coefficients.csv
    output/results/s04_regression_table.csv
    output/results/s06_regression_intensity.csv
    output/results/s06b_regression_intensity_quartiles.csv
    output/results/s09_regression_updown.csv
    output/results/s09_regression_updown_intensity.csv
    output/results/s08_regression_insurance.csv
    output/results/s08b_regression_insurance_updown.csv
    output/results/s09b_regression_disclosure.csv
    output/results/s09c_regression_republican.csv
    output/results/s095_robustness_table.csv
    output/results/s07_did_twfe.tex
    output/results/s02_summary_stats.csv
    output/results/s03_balance_table.csv
    output/results/s06b_event_study_intensity_quartiles_coefficients.csv
    output/results/s09_event_study_updown_decomposed_coefficients.csv
    output/results/s09_event_study_updown_intensity_coefficients.csv
    output/results/s09c_event_study_republican_coefficients.csv
    output/results/s08b_event_study_policies_updown_coefficients.csv
    output/results/s12_bacon_decomposition.png
    output/results/s13_event_study_cs.png
    output/results/s10_parallel_trends.png
    output/results/s10_treatment_timing_hist.png

Outputs:
    website/public/data/event_study_main.json
    website/public/data/event_study_intensity.json
    website/public/data/event_study_intensity_quartiles.json
    website/public/data/event_study_updown.json
    website/public/data/event_study_updown_decomposed.json
    website/public/data/event_study_updown_intensity.json
    website/public/data/event_study_policies.json
    website/public/data/event_study_policies_updown.json
    website/public/data/event_study_disclosure.json
    website/public/data/event_study_republican.json
    website/public/data/regression_tables.json
    website/public/data/summary_stats.json
    website/public/data/balance_table.json
    website/public/data/site_metadata.json
    website/public/images/*.png

Usage:
    python src/scripts/export_website_data.py
"""

import csv
import json
import os
import re
import shutil
import sys

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
RESULTS_DIR = os.path.join(OUTPUT_DIR, "results")
WEBSITE_DATA_DIR = os.path.join(PROJECT_ROOT, "website", "public", "data")
WEBSITE_IMG_DIR = os.path.join(PROJECT_ROOT, "website", "public", "images")


# ==============================================================================
# HELPERS
# ==============================================================================

def read_csv_rows(path):
    """Read a CSV file and return list of rows (list of strings)."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def read_listtab_rows(path):
    """Read a Stata listtab CSV where cells are emitted as =\"...\"."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip():
                rows.append([])
                continue
            fields = re.findall(r'="((?:[^"]|"")*)"', line)
            if fields:
                rows.append([field.replace('""', '"') for field in fields])
            else:
                rows.append(next(csv.reader([line])))
    return rows


def parse_coefficient(val):
    """Parse a coefficient string like '-.0065847' or '-.0132099*' into (float, stars)."""
    val = val.strip()
    if not val:
        return None, ""
    stars = ""
    while val.endswith("*"):
        stars += "*"
        val = val[:-1]
    try:
        return float(val), stars
    except ValueError:
        return None, ""


def parse_number(val):
    """Parse a number string, handling commas, whitespace, and parenthesized SEs."""
    val = val.strip().replace(",", "").strip("()")
    try:
        return float(val)
    except ValueError:
        return None


def write_json(data, filename):
    """Write data as JSON to the website data directory."""
    path = os.path.join(WEBSITE_DATA_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    size_kb = os.path.getsize(path) / 1024
    print(f"  {filename}: {size_kb:.1f} KB")


def copy_image(src_filename, dst_filename=None):
    """Copy an image from results/ to website/public/images/."""
    src = os.path.join(RESULTS_DIR, src_filename)
    if dst_filename is None:
        dst_filename = src_filename
    dst = os.path.join(WEBSITE_IMG_DIR, dst_filename)
    if not os.path.exists(src):
        print(f"  WARNING: {src_filename} not found, skipping")
        return False
    shutil.copy2(src, dst)
    size_kb = os.path.getsize(dst) / 1024
    print(f"  {dst_filename}: {size_kb:.0f} KB")
    return True


# ==============================================================================
# EVENT STUDY COEFFICIENT EXPORTS
# ==============================================================================

def export_event_study_simple(input_file, output_file, title, y_label):
    """Export a simple event study CSV (tau, coef, se, ci_lo, ci_hi)."""
    path = os.path.join(RESULTS_DIR, input_file)
    if not os.path.exists(path):
        print(f"  WARNING: {input_file} not found, skipping")
        return False

    rows = read_csv_rows(path)
    points = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        tau_str = row[0].strip().replace("+", "")
        points.append({
            "tau": int(tau_str),
            "coef": float(row[1]),
            "se": float(row[2]),
            "ci_lo": float(row[3]),
            "ci_hi": float(row[4]),
        })

    write_json({
        "title": title,
        "y_label": y_label,
        "reference_tau": -1,
        "points": points,
    }, output_file)
    return True


def export_event_study_two_series(input_file, output_file, title, y_label,
                                   series1_name, series2_name,
                                   series1_color, series2_color):
    """Export a two-series event study CSV (up/down or disclosure/non-disclosure).

    Auto-detects column layout:
      Standard: tau,coef,ci_lo,ci_hi,group,...
      Series-first: series,tau,coef,se,ci_lo,ci_hi,...
    """
    path = os.path.join(RESULTS_DIR, input_file)
    if not os.path.exists(path):
        print(f"  WARNING: {input_file} not found, skipping")
        return False

    rows = read_csv_rows(path)
    header = [h.strip().lower() for h in rows[0]]
    series_first = header[0] == "series"

    series1 = []
    series2 = []

    # Determine column indices based on format
    if series_first:
        group_col, tau_col, coef_col, ci_lo_col, ci_hi_col = 0, 1, 2, 4, 5
    else:
        tau_col, coef_col, ci_lo_col, ci_hi_col, group_col = 0, 1, 2, 3, 4

    # Collect unique group labels from the data
    group_labels = []
    for row in rows[1:]:
        if row and len(row) > group_col:
            g = row[group_col].strip()
            if g and g not in group_labels:
                group_labels.append(g)

    # Assign CSV group labels to series by matching first word
    s1_key = series1_name.split()[0].lower()
    label_to_series = {}
    for g in group_labels:
        if g.lower().startswith(s1_key):
            label_to_series[g] = 1
        else:
            label_to_series[g] = 2

    for row in rows[1:]:
        if not row or len(row) <= group_col:
            continue
        tau = int(float(row[tau_col]))
        coef = float(row[coef_col])
        ci_lo = float(row[ci_lo_col])
        ci_hi = float(row[ci_hi_col])
        group = row[group_col].strip()

        point = {"tau": tau, "coef": coef, "ci_lo": ci_lo, "ci_hi": ci_hi}
        if label_to_series.get(group) == 1:
            series1.append(point)
        else:
            series2.append(point)

    write_json({
        "title": title,
        "y_label": y_label,
        "reference_tau": -1,
        "series": [
            {"label": series1_name, "color": series1_color, "points": series1},
            {"label": series2_name, "color": series2_color, "points": series2},
        ],
    }, output_file)
    return True


def export_event_study_four_series(input_file, output_file, title, y_label,
                                    series_config):
    """Export a four-series event study CSV (e.g. intensity quartiles).

    series_config: list of (group_prefix, label, color) tuples, one per series.
    The CSV has columns: tau, coef, ci_lo, ci_hi, group, ...
    """
    path = os.path.join(RESULTS_DIR, input_file)
    if not os.path.exists(path):
        print(f"  WARNING: {input_file} not found, skipping")
        return False

    rows = read_csv_rows(path)

    # Collect unique group labels from column index 4
    group_labels = []
    for row in rows[1:]:
        if row and len(row) >= 5:
            g = row[4].strip()
            if g and g not in group_labels:
                group_labels.append(g)

    # Map CSV group labels to series config index by prefix match
    label_to_idx = {}
    for g in group_labels:
        for idx, (prefix, _, _) in enumerate(series_config):
            if g.startswith(prefix):
                label_to_idx[g] = idx
                break

    # Initialize series buckets
    series_points = [[] for _ in series_config]

    for row in rows[1:]:
        if not row or len(row) < 5:
            continue
        tau = int(row[0])
        coef = float(row[1])
        ci_lo = float(row[2])
        ci_hi = float(row[3])
        group = row[4].strip()

        point = {"tau": tau, "coef": coef, "ci_lo": ci_lo, "ci_hi": ci_hi}
        idx = label_to_idx.get(group)
        if idx is not None:
            series_points[idx].append(point)

    series = []
    for i, (_, label, color) in enumerate(series_config):
        series.append({"label": label, "color": color, "points": series_points[i]})

    write_json({
        "title": title,
        "y_label": y_label,
        "reference_tau": -1,
        "series": series,
    }, output_file)
    return True


# ==============================================================================
# REGRESSION TABLE EXPORTS
# ==============================================================================

def strip_listtab(val):
    """Strip Stata listtab ='...' quoting from a cell value."""
    val = val.strip()
    if val.startswith('="') and val.endswith('"'):
        return val[2:-1]
    return val


def parse_estout_csv(path):
    """
    Parse an estout-style CSV with alternating coef/SE rows.

    Format:
      Row 0: header ("", "Col1 Title", "Col2 Title", ...)
      Row 1: subheader ("", "b/se", "b/se", ...)
      Row 2: variable label, coef1, coef2, ...
      Row 3: "", se1, se2, ...
      ...
      Row N-2: "Observations", val1, val2, ...
      Row N-1: "Within R²", val1, val2, ...

    Also handles Stata listtab format where cells are wrapped in ="...".
    """
    rows = read_csv_rows(path)

    # Detect and re-read Stata listtab output before commas inside =\"...\" cells
    # get split by the standard CSV reader.
    has_listtab = any(row and row[0].strip().startswith('="') for row in rows[:5])
    if has_listtab:
        rows = read_listtab_rows(path)
        # Remove completely empty rows and footnote rows
        rows = [row for row in rows if any(c.strip() for c in row)
                and not row[0].strip().startswith("Standard errors")
                and not row[0].strip().startswith("* p<")]
    if len(rows) < 4:
        return None

    col_titles = [c.strip() for c in rows[0][1:]]
    n_cols = len(col_titles)

    variables = []
    stats = []
    i = 2  # skip header + subheader
    while i < len(rows):
        row = rows[i]
        if not row:
            i += 1
            continue
        label = row[0].strip()

        # Check if this is a stats row (Observations, Within R², etc.)
        if label in ("Observations", "Within R²", "Within R-squared"):
            stat_key = label
            if "R²" in label or "R-squared" in label:
                stat_key = "Within R²"
            values = []
            for j in range(1, min(n_cols + 1, len(row))):
                values.append(row[j].strip() if j < len(row) else "")
            stats.append({"label": stat_key, "values": values})
            i += 1
            continue

        # Skip empty label rows (SE rows handled below)
        if not label:
            i += 1
            continue

        # This is a variable row — next row should be SEs
        coefs = []
        for j in range(1, min(n_cols + 1, len(row))):
            val = row[j].strip() if j < len(row) else ""
            c, stars = parse_coefficient(val)
            coefs.append({"value": c, "stars": stars})

        # Read SE row
        ses = []
        if i + 1 < len(rows):
            se_row = rows[i + 1]
            for j in range(1, min(n_cols + 1, len(se_row))):
                val = se_row[j].strip() if j < len(se_row) else ""
                se_val = parse_number(val)
                ses.append(se_val)
            i += 2
        else:
            ses = [None] * n_cols
            i += 1

        variables.append({
            "label": label,
            "coefficients": coefs,
            "standard_errors": ses,
        })

    return {
        "columns": col_titles,
        "variables": variables,
        "stats": stats,
    }


def parse_twfe_tex(path):
    """Parse the TWFE DiD TeX table into structured JSON."""
    with open(path, encoding="utf-8") as f:
        tex = f.read()

    variables = []
    stats = []

    # Extract rows: "Variable & value \\"
    pattern = re.compile(
        r"^(.+?)\s*&\s*(.+?)\\\\",
        re.MULTILINE,
    )
    matches = pattern.findall(tex)

    i = 0
    while i < len(matches):
        label = matches[i][0].strip()
        val = matches[i][1].strip()

        # Skip hlines and empty
        if "hline" in label or not label:
            i += 1
            continue

        # Stats rows
        if label in ("Observations", "Within R²"):
            stats.append({"label": label, "values": [val.replace(",", "").strip()]})
            i += 1
            continue

        # Variable row
        coef_val, stars = parse_coefficient(val.replace("\\sym{", "").replace("}", ""))
        se_val = None
        if i + 1 < len(matches) and not matches[i + 1][0].strip():
            se_str = matches[i + 1][1].strip().strip("()")
            se_val = parse_number(se_str)
            i += 2
        else:
            i += 1

        variables.append({
            "label": label,
            "coefficients": [{"value": coef_val, "stars": stars}],
            "standard_errors": [se_val],
        })

    return {
        "columns": ["TWFE DiD"],
        "variables": variables,
        "stats": stats,
    }


def export_regression_tables():
    """Export all regression tables as a single JSON file."""
    tables = {}

    # Main regression table (3 specs)
    path = os.path.join(RESULTS_DIR, "s04_regression_table.csv")
    if os.path.exists(path):
        parsed = parse_estout_csv(path)
        if parsed:
            tables["main"] = {
                "title": "ln(Real ZHVI) on LOMR Treatment",
                "notes": [
                    "Zip and county\u00d7year fixed effects.",
                    "Standard errors clustered at county level.",
                    "Reference period: 12-0 months before LOMR (\u03c4 = -1).",
                    "Already-treated zips (LOMR before 2009) excluded.",
                    "(1) No controls. (2) Unemployment rate, NFIP policies. (3) Adds avg premium, claims.",
                ],
                **parsed,
            }

    # Intensity regression
    path = os.path.join(RESULTS_DIR, "s06_regression_intensity.csv")
    if os.path.exists(path):
        parsed = parse_estout_csv(path)
        if parsed:
            tables["intensity"] = {
                "title": "ln(Real ZHVI) on LOMR × Policy Intensity",
                "notes": [
                    "Zip and county\u00d7year FE. SE clustered at county level.",
                    "Intensity = pre-LOMR NFIP policies / population.",
                ],
                **parsed,
            }

    # Up/down regression
    path = os.path.join(RESULTS_DIR, "s09_regression_updown.csv")
    if os.path.exists(path):
        parsed = parse_estout_csv(path)
        if parsed:
            tables["updown"] = {
                "title": "ln(Real ZHVI) on Upzoning vs Downzoning",
                "notes": [
                    "Zip and county\u00d7year FE. SE clustered at county level.",
                    "Each spec uses its treated subsample + all never-treated controls.",
                    "Risk direction classified by SFHA zone share change (\u00b11pp threshold).",
                ],
                **parsed,
            }

    # Insurance regression
    path = os.path.join(RESULTS_DIR, "s08_regression_insurance.csv")
    if os.path.exists(path):
        parsed = parse_estout_csv(path)
        if parsed:
            tables["insurance"] = {
                "title": "ln(NFIP Policies) on LOMR Treatment",
                "notes": [
                    "Zip and county\u00d7year FE. SE clustered at county level.",
                    "Policies: NFIP policy count (mechanism). Claims: falsification.",
                    "Reference period: \u03c4 = -1 (12-0 months before LOMR).",
                ],
                **parsed,
            }

    # Disclosure regression
    path = os.path.join(RESULTS_DIR, "s09b_regression_disclosure.csv")
    if os.path.exists(path):
        parsed = parse_estout_csv(path)
        if parsed:
            tables["disclosure"] = {
                "title": "ln(Real ZHVI) on LOMR \u00d7 Disclosure",
                "notes": [
                    "Zip and county\u00d7year FE. SE clustered at county level.",
                    "ebin = binary LOMR effect (non-disclosure states).",
                    "dbin/dbinb = differential effect in disclosure states.",
                    "Strict: CA, IL, IN, LA, MS, OR, SC, TX, WI. Broad adds FL, VA, NC, NY.",
                ],
                **parsed,
            }

    # Intensity quartiles regression — reshape from 32 rows × 1 col to 8 rows × 4 cols
    path = os.path.join(RESULTS_DIR, "s06b_regression_intensity_quartiles.csv")
    if os.path.exists(path):
        parsed = parse_estout_csv(path)
        if parsed:
            # Pivot: each variable is "τ = {period} × Q{n}" → rows=periods, cols=quartiles
            period_order = ["m4", "m3", "m2", "p0", "p1", "p2", "p3", "p4"]
            period_labels = {
                "m4": "τ = −4", "m3": "τ = −3", "m2": "τ = −2",
                "p0": "τ = 0", "p1": "τ = +1", "p2": "τ = +2",
                "p3": "τ = +3", "p4": "τ = +4",
            }
            quartile_data = {p: {"coefs": [None]*4, "ses": [None]*4} for p in period_order}
            for var in parsed["variables"]:
                m = re.match(r"τ = (m\d|p\d) × Q(\d)", var["label"])
                if m:
                    period, qnum = m.group(1), int(m.group(2))
                    if period in quartile_data and 1 <= qnum <= 4:
                        quartile_data[period]["coefs"][qnum - 1] = var["coefficients"][0]
                        quartile_data[period]["ses"][qnum - 1] = var["standard_errors"][0]
            pivoted_vars = []
            for p in period_order:
                pivoted_vars.append({
                    "label": period_labels[p],
                    "coefficients": [c if c else {"value": None, "stars": ""} for c in quartile_data[p]["coefs"]],
                    "standard_errors": quartile_data[p]["ses"],
                })
            tables["intensity_quartiles"] = {
                "title": "ln(Real ZHVI) by Policy Intensity Quartile",
                "notes": [
                    "Zip and county×year FE. SE clustered at county level.",
                    "Quartiles based on pre-LOMR NFIP policy penetration.",
                    "Q1 = lowest penetration, Q4 = highest.",
                ],
                "columns": ["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"],
                "variables": pivoted_vars,
                "stats": parsed["stats"],
            }

    # Republican heterogeneity regression
    path = os.path.join(RESULTS_DIR, "s09c_regression_republican.csv")
    if os.path.exists(path):
        parsed = parse_estout_csv(path)
        if parsed:
            tables["republican"] = {
                "title": "ln(Real ZHVI) on Policy Intensity \u00d7 Political Lean",
                "notes": [
                    "Zip and county\u00d7year FE. SE clustered at county level.",
                    "Intensity = pre-LOMR NFIP policies / population.",
                    "Rep = 1 if county above-median Republican two-party vote share (2020).",
                ],
                **parsed,
            }

    # Up/down intensity regression
    path = os.path.join(RESULTS_DIR, "s09_regression_updown_intensity.csv")
    if os.path.exists(path):
        parsed = parse_estout_csv(path)
        if parsed:
            tables["updown_intensity"] = {
                "title": "ln(Real ZHVI) on Signed LOMR × Policy Intensity",
                "notes": [
                    "Zip and county\u00d7year FE. SE clustered at county level.",
                    "Signed intensity separates upzoned (risk \u2191) and downzoned (risk \u2193) LOMRs.",
                ],
                **parsed,
            }

    # Robustness table
    path = os.path.join(RESULTS_DIR, "s095_robustness_table.csv")
    if os.path.exists(path):
        parsed = parse_estout_csv(path)
        if parsed:
            tables["robustness"] = {
                "title": "ln(Real ZHVI) on LOMR (Robustness)",
                "notes": [
                    "Zip and county\u00d7year FE. SE clustered at county level.",
                    "(1) Main (weighted): baseline specification with population weights.",
                    "(2) Unweighted: no population weights.",
                    "(3) Geographic intensity: LOMR area / ZCTA area ratio.",
                ],
                **parsed,
            }

    # TWFE DiD
    path = os.path.join(RESULTS_DIR, "s07_did_twfe.tex")
    if os.path.exists(path):
        parsed = parse_twfe_tex(path)
        if parsed:
            tables["twfe"] = {
                "title": "ln(Real ZHVI) on LOMR (TWFE DiD)",
                "notes": [
                    "Zip and county\u00d7year FE. SE clustered at county level.",
                ],
                **parsed,
            }

    write_json(tables, "regression_tables.json")
    return True


# ==============================================================================
# SUMMARY STATISTICS & BALANCE TABLE
# ==============================================================================

def export_summary_stats():
    """Export summary statistics CSV as JSON."""
    path = os.path.join(RESULTS_DIR, "s02_summary_stats.csv")
    if not os.path.exists(path):
        print("  WARNING: s02_summary_stats.csv not found, skipping")
        return False

    rows = read_csv_rows(path)
    header = [h.strip() for h in rows[0]]

    variables = []
    for row in rows[1:]:
        entry = {}
        for i, col in enumerate(header):
            val = row[i].strip() if i < len(row) else ""
            if col == "" or col == "Variable":
                entry["variable"] = val
            else:
                entry[col.lower().replace(" ", "_")] = parse_number(val)
        variables.append(entry)

    # Organize variables into panels by analytical role
    PANELS = [
        {
            "label": "Panel A: Outcomes",
            "vars": [
                "Home Value Index (Dec 2022 USD)",
                "Home Value Index (Dec 2022 $)",
                "Home Value (Dec 2022 $)",
                "Home Value (Dec 2022 USD)",
                "ln(Real ZHVI)",
                "ln(NFIP Policies + 1)",
                "ln(NFIP Claims + 1)",
            ],
        },
        {
            "label": "Panel B: Treatment",
            "vars": [
                "Post-LOMR",
                "Ever Treated",
                "NFIP Policy Penetration (pre-LOMR)",
                "NFIP Policy Penetration",
                "Policy Intensity",
                "Policy Intensity (per 1,000)",
                "LOMR Area / ZCTA Area",
                "Treatment Intensity (LOMR/ZCTA)",
                "Treatment Intensity (per 1,000)",
                "Upzoned (into SFHA)",
                "Downzoned (out of SFHA)",
                "SFHA-Crossing LOMR",
            ],
        },
        {
            "label": "Panel C: Controls",
            "vars": [
                "County Unemp. Rate (%)",
                "NFIP Policies (qtr avg)",
                "NFIP Avg Premium ($)",
                "NFIP Avg Premium (USD)",
                "SFHA Zone Share",
                "NFIP Claims (qtr avg)",
                "Zip Population",
                "Zip Pop. Density",
            ],
        },
        {
            "label": "Panel D: Heterogeneity",
            "vars": [
                "Republican County",
                "R Two-Party Vote Share",
                "Mandatory Flood Disclosure State",
                "Mandatory Flood Disclosure",
                "Disclosure: Strict (9 states)",
                "Disclosure: Broad (13 states)",
            ],
        },
    ]

    # Build panel-grouped structure
    var_lookup = {v["variable"]: v for v in variables}
    panels = []
    for panel in PANELS:
        panel_vars = []
        for var_name in panel["vars"]:
            if var_name in var_lookup:
                panel_vars.append(var_lookup[var_name])
        if panel_vars:
            panels.append({"label": panel["label"], "variables": panel_vars})

    write_json({
        "title": "Summary Statistics \u2014 Estimation Sample (2009-2022)",
        "columns": ["N", "Mean", "Std Dev", "Min", "P25", "Median", "P75", "Max"],
        "panels": panels,
        "variables": variables,  # keep flat list for backward compat
        "notes": [
            "Estimation sample of U.S. coastal zip codes, quarterly 2009Q1\u20132022Q4. N = 228,005 zip-quarter obs.",
            "R Two-Party Vote Share has fewer obs. due to missing election data in some counties.",
        ],
    }, "summary_stats.json")
    return True


def export_balance_table():
    """Export balance table CSV as JSON."""
    path = os.path.join(RESULTS_DIR, "s03_balance_table.csv")
    if not os.path.exists(path):
        print("  WARNING: s03_balance_table.csv not found, skipping")
        return False

    rows = read_csv_rows(path)

    variables = []
    for row in rows[1:]:
        label = row[0].strip()
        control_val = row[1].strip() if len(row) > 1 else ""
        treated_val = row[2].strip() if len(row) > 2 else ""
        diff_val = row[3].strip() if len(row) > 3 else ""

        # Parse difference with stars
        diff_num, stars = parse_coefficient(diff_val)

        variables.append({
            "variable": label,
            "control": parse_number(control_val),
            "treated": parse_number(treated_val),
            "difference": diff_num,
            "stars": stars,
        })

    write_json({
        "title": "Balance Table: Pre-Treatment Characteristics",
        "columns": ["Control", "Treated", "Difference"],
        "notes": [
            "Treated: zips with single LOMR during 2009-2022.",
            "Control: zips with no LOMR.",
            "Pre-treatment means reported for treated zips.",
            "Difference = Treated - Control. Welch t-test.",
        ],
        "variables": variables,
    }, "balance_table.json")
    return True


# ==============================================================================
# SITE METADATA
# ==============================================================================

def export_site_metadata():
    """Generate site metadata JSON with key numbers for the website."""
    metadata = {
        "title": "Flood Risk and Home Values",
        "subtitle": "How FEMA Flood Zone Reclassifications Affect Property Markets",
        "author": "Cameron Keith",
        "course": "Econ 66: Topics in Money and Finance",
        "analysis_window": {"start": 2009, "end": 2022},
    }

    # Extract key numbers from existing data
    stats_path = os.path.join(RESULTS_DIR, "s02_summary_stats.csv")
    if os.path.exists(stats_path):
        rows = read_csv_rows(stats_path)
        for row in rows[1:]:
            if row[0].strip() == "ln(Real ZHVI)":
                metadata["n_observations"] = int(parse_number(row[1]) or 0)
                break

    # Headline from binary event study: τ = +4 coefficient
    coef_path = os.path.join(RESULTS_DIR, "s05_event_study_coefficients.csv")
    if os.path.exists(coef_path):
        rows = read_csv_rows(coef_path)
        for row in rows[1:]:
            if row[0].strip() in ("+4", "4"):
                headline_coef = float(row[1])
                metadata["headline_coefficient"] = round(headline_coef, 4)
                import math
                metadata["headline_pct"] = round((math.exp(headline_coef) - 1) * 100, 1)
                metadata["headline_description"] = (
                    f"{metadata['headline_pct']}% decline in home values "
                    f"four or more years after LOMR flood zone reclassification"
                )
                break

    # Headline from intensity event study: τ = +4 coefficient
    intensity_path = os.path.join(RESULTS_DIR, "s06_event_study_intensity_coefficients.csv")
    if os.path.exists(intensity_path):
        rows = read_csv_rows(intensity_path)
        for row in rows[1:]:
            if row[0].strip() in ("+4", "4"):
                metadata["intensity_coefficient"] = round(float(row[1]), 2)
                break

    metadata["sample_description"] = (
        "Coastal US zip codes (excluding Alaska and territories), "
        "quarterly panel 2009-2022"
    )

    reg_path = os.path.join(RESULTS_DIR, "s04_regression_table.csv")
    if os.path.exists(reg_path):
        rows = read_csv_rows(reg_path)
        for row in rows:
            if row[0].strip() == "Observations":
                metadata["n_observations_regression"] = row[1].strip()
                break

    write_json(metadata, "site_metadata.json")
    return True


# ==============================================================================
# STATIC IMAGES
# ==============================================================================

def export_event_study_cs(input_file, output_file, title, y_label):
    """Export Callaway & Sant'Anna event study CSV as two-series JSON.

    The CSV has aggregate 'pre'/'post' rows followed by individual tau
    coefficients. We skip the aggregates and split individual taus into
    pre-treatment (tau <= -1) and post-treatment (tau >= 0) series.
    """
    path = os.path.join(RESULTS_DIR, input_file)
    if not os.path.exists(path):
        print(f"  WARNING: {input_file} not found, skipping")
        return False

    rows = read_csv_rows(path)
    pre_points = []
    post_points = []

    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        tau_str = row[0].strip()
        # Skip aggregate pre/post rows
        if tau_str in ("pre", "post"):
            continue
        tau = int(float(tau_str))
        point = {
            "tau": tau,
            "coef": float(row[1]),
            "ci_lo": float(row[3]),
            "ci_hi": float(row[4]),
        }
        if tau <= -1:
            pre_points.append(point)
        else:
            post_points.append(point)

    write_json({
        "title": title,
        "y_label": y_label,
        "reference_tau": -1,
        "series": [
            {"label": "Pre-treatment", "points": pre_points},
            {"label": "Post-treatment", "points": post_points},
        ],
    }, output_file)
    return True


def export_leave_one_out(input_file, output_file):
    """Export leave-one-out CSV as JSON for forest plot."""
    path = os.path.join(RESULTS_DIR, input_file)
    if not os.path.exists(path):
        print(f"  WARNING: {input_file} not found, skipping")
        return False

    rows = read_csv_rows(path)

    points = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        points.append({
            "excluded_state": int(float(row[0])),
            "coef": float(row[1]),
            "se": float(row[2]),
            "ci_lo": float(row[3]),
            "ci_hi": float(row[4]),
            "n_obs": int(float(row[5])),
        })

    # Get full-sample reference from the main event study
    main_path = os.path.join(RESULTS_DIR, "s05_event_study_coefficients.csv")
    full_coef = None
    if os.path.exists(main_path):
        main_rows = read_csv_rows(main_path)
        for row in main_rows[1:]:
            if row[0].strip() in ("+4", "4"):
                full_coef = float(row[1])
                break

    write_json({
        "title": "Leave-One-Out by State: \u03c4 = +4 Coefficient",
        "full_sample_coef": full_coef,
        "points": points,
    }, output_file)
    return True


def export_images():
    """Copy static result images to website/public/images/."""
    images = [
        ("s12_bacon_decomposition.png", "bacon_decomposition.png"),
        ("s13_event_study_cs.png", "event_study_cs.png"),
        ("s10_parallel_trends.png", "parallel_trends.png"),
        ("s10_treatment_timing_hist.png", "treatment_timing.png"),
        ("s05_event_study_main.png", "event_study_main.png"),
        ("s06_event_study_intensity.png", "event_study_intensity.png"),
        ("s09_event_study_updown.png", "event_study_updown.png"),
        ("s08_event_study_policies.png", "event_study_policies.png"),
        ("s09b_event_study_disclosure.png", "event_study_disclosure.png"),
        ("s06b_event_study_intensity_quartiles.png", "event_study_intensity_quartiles.png"),
        ("s09c_event_study_republican.png", "event_study_republican.png"),
        ("s14_event_study_placebo.png", "event_study_placebo.png"),
    ]

    for src, dst in images:
        copy_image(src, dst)


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print("Exporting website data...")
    print(f"  Input:  {RESULTS_DIR}")
    print(f"  Output: {WEBSITE_DATA_DIR}")

    # Check output directory exists
    if not os.path.exists(RESULTS_DIR):
        print(f"ERROR: Results directory not found: {RESULTS_DIR}")
        sys.exit(1)

    os.makedirs(WEBSITE_DATA_DIR, exist_ok=True)
    os.makedirs(WEBSITE_IMG_DIR, exist_ok=True)

    # Export all datasets
    print("\n--- Event Study Coefficients ---")
    export_event_study_simple(
        "s05_event_study_coefficients.csv",
        "event_study_main.json",
        "ln(Home Values) on LOMR Treatment",
        "Effect on ln(Real ZHVI)",
    )
    export_event_study_simple(
        "s06_event_study_intensity_coefficients.csv",
        "event_study_intensity.json",
        "ln(Home Values) on LOMR × Policy Intensity",
        "Effect on ln(Real ZHVI) per Unit Policy Penetration",
    )
    export_event_study_two_series(
        "s09_event_study_updown_coefficients.csv",
        "event_study_updown.json",
        "ln(Home Values) on Upzoning vs Downzoning",
        "Effect on ln(Real ZHVI)",
        "Upzoned (risk increased)", "Downzoned (risk decreased)",
        "red", "blue",
    )
    export_event_study_simple(
        "s08_event_study_policies_coefficients.csv",
        "event_study_policies.json",
        "ln(NFIP Policies) on LOMR Treatment",
        "Effect on ln(NFIP Policies + 1)",
    )
    export_event_study_two_series(
        "s09b_event_study_disclosure_coefficients.csv",
        "event_study_disclosure.json",
        "ln(Home Values) on LOMR \u00d7 Disclosure",
        "Effect on ln(Real ZHVI)",
        "Disclosure", "Non-Disclosure",
        "red", "blue",
    )
    export_event_study_two_series(
        "s09_event_study_updown_decomposed_coefficients.csv",
        "event_study_updown_decomposed.json",
        "ln(Home Values) on Signed LOMR × Policy Intensity",
        "Effect on ln(Real ZHVI) per Unit Intensity",
        "Upzoned", "Downzoned",
        "red", "blue",
    )
    export_event_study_two_series(
        "s09c_event_study_republican_coefficients.csv",
        "event_study_republican.json",
        "ln(Home Values) on Policy Intensity \u00d7 Political Lean",
        "Effect on ln(Real ZHVI) per Unit Intensity",
        "Republican", "Democratic",
        "red", "blue",
    )
    export_event_study_simple(
        "s09_event_study_updown_intensity_coefficients.csv",
        "event_study_updown_intensity.json",
        "ln(Home Values) on Signed LOMR × Policy Intensity (Pooled)",
        "Effect on ln(Real ZHVI) per Unit Signed Intensity",
    )
    export_event_study_two_series(
        "s08b_event_study_policies_updown_coefficients.csv",
        "event_study_policies_updown.json",
        "ln(NFIP Policies) on Upzoning vs Downzoning",
        "Effect on ln(NFIP Policies + 1)",
        "Upzoned", "Downzoned",
        "red", "blue",
    )
    export_event_study_simple(
        "s09d_event_study_sfha_crossing_coefficients.csv",
        "event_study_sfha_crossing.json",
        "ln(Home Values) on SFHA-Crossing LOMRs",
        "Effect on ln(Real ZHVI)",
    )
    export_event_study_four_series(
        "s06b_event_study_intensity_quartiles_coefficients.csv",
        "event_study_intensity_quartiles.json",
        "ln(Home Values) by Policy Intensity Quartile",
        "Effect on ln(Real ZHVI)",
        [
            ("Q1", "Q1 (low)", "#94a3b8"),
            ("Q2", "Q2 (med-low)", "#60a5fa"),
            ("Q3", "Q3 (med-high)", "#3b82f6"),
            ("Q4", "Q4 (high)", "#1d4ed8"),
        ],
    )
    export_event_study_cs(
        "s13_event_study_cs_coefficients.csv",
        "event_study_cs.json",
        "ln(Home Values) on LOMR (CS Estimator)",
        "ATT on ln(Real ZHVI)",
    )
    export_event_study_simple(
        "s14_event_study_placebo_coefficients.csv",
        "event_study_placebo.json",
        "Unemployment on LOMR Treatment (Placebo)",
        "Effect on Unemployment Rate",
    )
    export_event_study_two_series(
        "s16_event_study_alt_clustering_coefficients.csv",
        "event_study_alt_clustering.json",
        "ln(Home Values) on LOMR Treatment (Alt. SE)",
        "Effect on ln(Real ZHVI)",
        "County", "State",
        "red", "blue",
    )
    export_leave_one_out(
        "s15_leave_one_out_state.csv",
        "leave_one_out_state.json",
    )

    print("\n--- Regression Tables ---")
    export_regression_tables()

    print("\n--- Summary Statistics ---")
    export_summary_stats()

    print("\n--- Balance Table ---")
    export_balance_table()

    print("\n--- Site Metadata ---")
    export_site_metadata()

    print("\n--- Static Images ---")
    export_images()

    print("\nDone. All data written to website/public/")

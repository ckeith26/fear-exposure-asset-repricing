"""
Convert Republican heterogeneity CSV results to website JSON format.

Inputs (from output/results/):
    s09c_event_study_republican_coefficients.csv
    s09d_event_study_republican_trend_coefficients.csv
    s09c_regression_republican.csv
    s09d_regression_republican_trend.csv

Outputs (to website/public/data/):
    event_study_republican.json
    event_study_republican_trend.json
    regression_tables.json  (adds 'republican' and 'republican_trend' keys)

Usage:
    python website/scripts/convert_republican_results.py
"""

import csv
import json
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "output", "results")
DATA_DIR = os.path.join(PROJECT_ROOT, "website", "public", "data")


# === EVENT STUDY JSON ===

def parse_event_study_csv(path):
    """Parse a two-group coefficient CSV into {Republican: [...], Democratic: [...]}."""
    groups = {"Republican": [], "Democratic": []}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            group = row["group"]
            tau = int(float(row["tau"]))
            coef = float(row["coef"])
            ci_lo = float(row["ci_lo"])
            ci_hi = float(row["ci_hi"])
            groups[group].append({
                "tau": tau,
                "coef": coef,
                "ci_lo": ci_lo,
                "ci_hi": ci_hi,
            })
    # Sort by tau
    for g in groups:
        groups[g].sort(key=lambda p: p["tau"])
    return groups


def build_event_study_json(groups, title, y_label):
    """Build the two-series JSON matching the disclosure.json format."""
    return {
        "title": title,
        "y_label": y_label,
        "reference_tau": -1,
        "series": [
            {
                "label": "Republican",
                "color": "red",
                "points": groups["Republican"],
            },
            {
                "label": "Democratic",
                "color": "blue",
                "points": groups["Democratic"],
            },
        ],
    }


# === REGRESSION TABLE JSON ===

def parse_regression_csv(path):
    """Parse Stata esttab CSV into variables list and stats list.

    Returns (columns, variables, stats) where:
      columns: list of column header strings
      variables: list of {label, coefficients: [{value, stars}], standard_errors: [float]}
      stats: list of {label, values: [str]}
    """
    rows = []
    with open(path) as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)

    # Row 0: header row - ["", "Col1", "Col2", ...]
    # Row 1: subheader - ["", "b/se", "b/se", ...]
    # Remaining rows alternate: variable name + coef, then SE
    columns = [c.strip() for c in rows[0][1:]]
    n_cols = len(columns)

    variables = []
    stats = []
    i = 2  # skip header and b/se rows
    while i < len(rows):
        label = rows[i][0].strip().strip('"')
        values_raw = [v.strip().strip('"') for v in rows[i][1:]]

        # Check if this is a stat row (Observations, Within R², etc.)
        if label in ("Observations", "Within R²", "R²", "N"):
            stats.append({"label": label, "values": values_raw[:n_cols]})
            i += 1
            continue

        # Parse coefficient row: value with optional stars
        coefficients = []
        for v in values_raw[:n_cols]:
            parsed = parse_coef_value(v)
            coefficients.append(parsed)

        # Next row should be SE
        se_values = []
        if i + 1 < len(rows):
            se_raw = [v.strip().strip('"') for v in rows[i + 1][1:]]
            for v in se_raw[:n_cols]:
                try:
                    se_values.append(float(v))
                except (ValueError, IndexError):
                    se_values.append(None)
            i += 2
        else:
            se_values = [None] * n_cols
            i += 1

        variables.append({
            "label": label,
            "coefficients": coefficients,
            "standard_errors": se_values,
        })

    return columns, variables, stats


def parse_coef_value(s):
    """Parse '−3.262021*' into {'value': -3.262021, 'stars': '*'}."""
    s = s.strip()
    if not s:
        return {"value": None, "stars": ""}
    # Extract stars
    stars = ""
    while s and s[-1] == "*":
        stars += "*"
        s = s[:-1]
    try:
        value = float(s)
    except ValueError:
        return {"value": None, "stars": ""}
    return {"value": value, "stars": stars}


def main():
    # --- Event study JSONs ---
    for csv_name, json_name, title in [
        (
            "s09c_event_study_republican_coefficients.csv",
            "event_study_republican.json",
            "LOMR Intensity: Republican vs Democratic Counties",
        ),
        (
            "s09d_event_study_republican_trend_coefficients.csv",
            "event_study_republican_trend.json",
            "LOMR Intensity: Republican vs Democratic (Zip Trends)",
        ),
    ]:
        csv_path = os.path.join(RESULTS_DIR, csv_name)
        groups = parse_event_study_csv(csv_path)
        data = build_event_study_json(
            groups,
            title=title,
            y_label="Effect on ln(Real ZHVI) per Unit Intensity",
        )
        out_path = os.path.join(DATA_DIR, json_name)
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  wrote {out_path}")

    # --- Regression table entries ---
    reg_path = os.path.join(DATA_DIR, "regression_tables.json")
    with open(reg_path) as f:
        reg_tables = json.load(f)

    # 9c: single-column republican interaction
    cols_9c, vars_9c, stats_9c = parse_regression_csv(
        os.path.join(RESULTS_DIR, "s09c_regression_republican.csv")
    )
    reg_tables["republican"] = {
        "title": "Intensity \u00d7 Republican Interaction",
        "notes": [
            "Zip and county\u00d7year FE. SE clustered at county level.",
            "Intensity = pre-LOMR NFIP policies / population.",
            "Republican = county voted >50% for GOP in most recent presidential election.",
        ],
        "columns": cols_9c,
        "variables": vars_9c,
        "stats": stats_9c,
    }

    # 9d: two-column baseline vs zip trends
    cols_9d, vars_9d, stats_9d = parse_regression_csv(
        os.path.join(RESULTS_DIR, "s09d_regression_republican_trend.csv")
    )
    reg_tables["republican_trend"] = {
        "title": "Republican Interaction: Baseline vs Zip Linear Trends",
        "notes": [
            "Zip and county\u00d7year FE. SE clustered at county level.",
            "Column 2 adds zip-specific linear time trends to absorb differential pre-trends.",
        ],
        "columns": cols_9d,
        "variables": vars_9d,
        "stats": stats_9d,
    }

    with open(reg_path, "w") as f:
        json.dump(reg_tables, f, indent=2)
    print(f"  updated {reg_path}")

    print("Done.")


if __name__ == "__main__":
    main()

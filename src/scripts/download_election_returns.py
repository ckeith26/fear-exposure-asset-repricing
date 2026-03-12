"""
Download county-level presidential election returns from the MIT Election
Data + Science Lab (MEDSL) via Harvard Dataverse.

Pipeline step: Acquisition (mechanism variable — political salience)

Requirements:
    pip install requests

Usage:
    python download_election_returns.py          # download if not present
    python download_election_returns.py --force  # re-download even if exists

Source:
    MIT Election Data + Science Lab, 2017,
    "County Presidential Election Returns 2000-2020",
    https://doi.org/10.7910/DVN/VOQCHQ, Harvard Dataverse

Downloads to: data/raw/election-returns/countypres_2000-2020.csv
"""

import os
import csv
import requests

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Harvard Dataverse persistent identifier
DATASET_DOI = "doi:10.7910/DVN/VOQCHQ"
DATAVERSE_API = "https://dataverse.harvard.edu/api"

# Dataverse stores the file as .tab (tab-separated); we look for the presidential returns
TARGET_PATTERN = "countypres"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "election-returns")


# ==============================================================================
# DOWNLOAD
# ==============================================================================

def get_file_info():
    """Query Dataverse API to find the file ID and name for the target data."""
    print("  Querying Dataverse for dataset metadata...")
    url = f"{DATAVERSE_API}/datasets/:persistentId/"
    params = {"persistentId": DATASET_DOI}
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    files = data.get("data", {}).get("latestVersion", {}).get("files", [])

    # Find the county presidential returns file
    for f in files:
        label = f.get("label", "") or f.get("dataFile", {}).get("filename", "")
        if TARGET_PATTERN.lower() in label.lower() and "source" not in label.lower():
            file_id = f["dataFile"]["id"]
            print(f"  Found '{label}' (file ID: {file_id})")
            return file_id, label

    available = [f.get("label", "unknown") for f in files]
    raise FileNotFoundError(
        f"No file matching '{TARGET_PATTERN}' in dataset {DATASET_DOI}.\n"
        f"  Available files: {available}"
    )


def download(force=False):
    """Download the county presidential returns file."""
    file_id, filename = get_file_info()
    output_file = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(output_file) and not force:
        size_mb = os.path.getsize(output_file) / 1e6
        print(f"  SKIP: {filename} already exists ({size_mb:.1f} MB)")
        return output_file

    print(f"  Downloading file ID {file_id}...")
    url = f"{DATAVERSE_API}/access/datafile/{file_id}"
    r = requests.get(url, timeout=120)
    r.raise_for_status()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(r.content)

    size_mb = os.path.getsize(output_file) / 1e6
    print(f"  Saved: {output_file} ({size_mb:.1f} MB)")
    return output_file


# ==============================================================================
# VERIFICATION
# ==============================================================================

def verify(output_file):
    """Print summary statistics from the downloaded file."""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    if not output_file or not os.path.exists(output_file):
        print("  File not found!")
        return

    # Detect delimiter: .tab files are TSV, .csv files are CSV
    delimiter = "\t" if output_file.endswith(".tab") else ","

    years = set()
    counties = set()
    row_count = 0
    header = None

    with open(output_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        header = reader.fieldnames
        for row in reader:
            row_count += 1
            year = row.get("year", "")
            fips = row.get("county_fips", "")
            if year:
                try:
                    years.add(int(float(year)))
                except ValueError:
                    pass
            if fips:
                counties.add(fips)

    filename = os.path.basename(output_file)
    print(f"\n  File: {filename}")
    print(f"  Size: {os.path.getsize(output_file) / 1e6:.1f} MB")
    print(f"  Rows: {row_count:,}")
    print(f"  Columns: {header}")
    if years:
        print(f"  Election years: {sorted(years)}")
        print(f"  Counties: {len(counties):,} unique FIPS codes")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download MIT Election Lab county presidential returns")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    args = parser.parse_args()

    print("MIT Election Lab — County Presidential Returns")
    print("=" * 60)

    output_file = download(force=args.force)
    verify(output_file)

    print("\n" + "=" * 60)
    print(f"DONE! File saved to: {OUTPUT_DIR}")
    print("=" * 60)

"""
Download BLS Local Area Unemployment Statistics (LAUS) county-level data
from bulk HTTPS files at download.bls.gov.

Pipeline step: Acquisition (control variables — unemployment)

Requirements:
    pip install requests

Usage:
    python download_bls_laus.py          # download all files
    python download_bls_laus.py --force  # re-download even if files exist

Downloads four tab-delimited files to data/raw/bls-laus/:
    - la.data.64.County  — county-level monthly series data (all years)
    - la.area            — area code to county FIPS crosswalk
    - la.series          — series ID definitions
    - la.measure         — measure type codes (unemployment rate, labor force, etc.)
"""

import os
import requests
import time

# ==============================================================================
# CONFIGURATION
# ==============================================================================

BASE_URL = "https://download.bls.gov/pub/time.series/la"

FILES_TO_DOWNLOAD = [
    "la.data.64.County",  # main county-level data (~200 MB)
    "la.area",            # area code → FIPS crosswalk
    "la.series",          # series ID definitions
    "la.measure",         # measure type codes
]

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "bls-laus")

# BLS Akamai CDN blocks non-browser User-Agent strings with 403
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# ==============================================================================
# DOWNLOAD
# ==============================================================================

def download_file(filename, force=False):
    """Download a single file from BLS bulk HTTPS server."""
    url = f"{BASE_URL}/{filename}"
    outpath = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(outpath) and not force:
        size_mb = os.path.getsize(outpath) / 1e6
        print(f"  SKIP {filename} (already exists, {size_mb:.1f} MB)")
        return outpath

    print(f"  Downloading {filename}...")
    r = requests.get(url, headers=HEADERS, timeout=300, stream=True)
    r.raise_for_status()

    # Stream to disk for large files
    total = 0
    with open(outpath, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
            total += len(chunk)
            print(f"    {total / 1e6:.1f} MB downloaded...", end="\r")

    size_mb = os.path.getsize(outpath) / 1e6
    print(f"    {filename}: {size_mb:.1f} MB                ")
    return outpath


# ==============================================================================
# VERIFICATION
# ==============================================================================

def verify_files():
    """Check that downloaded files are non-empty and tab-delimited; print stats."""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    for filename in FILES_TO_DOWNLOAD:
        path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(path):
            print(f"  MISSING: {filename}")
            continue

        size_mb = os.path.getsize(path) / 1e6
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            header = f.readline().strip()
            cols = header.split("\t")
            # Count lines (read in chunks for large files)
            line_count = 1
            for line in f:
                line_count += 1

        print(f"\n  {filename}:")
        print(f"    Size: {size_mb:.1f} MB")
        print(f"    Rows: {line_count:,} (including header)")
        print(f"    Columns ({len(cols)}): {cols[:6]}{'...' if len(cols) > 6 else ''}")

        # For the main data file, show date range
        if filename == "la.data.64.County":
            _print_date_range(path)


def _print_date_range(path):
    """Print year range from the county data file."""
    years = set()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        f.readline()  # skip header
        for line in f:
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    year = int(parts[1].strip()[:4])
                    years.add(year)
                except (ValueError, IndexError):
                    pass
    if years:
        print(f"    Year range: {min(years)} – {max(years)}")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download BLS LAUS county unemployment data")
    parser.add_argument("--force", action="store_true", help="Re-download even if files exist")
    args = parser.parse_args()

    print("BLS LAUS County Unemployment — Bulk Download")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename in FILES_TO_DOWNLOAD:
        download_file(filename, force=args.force)
        time.sleep(0.5)  # be polite to BLS servers

    verify_files()

    print("\n" + "=" * 60)
    print(f"DONE! Files saved to: {OUTPUT_DIR}")
    print("=" * 60)

"""
Build interactive HTML map of treatment/control zip code BOUNDARIES over time.

Reads the FULL treatment CSV + ZCTA shapefile and generates a self-contained
HTML file with zip code polygon boundaries colored by treatment status.

Features:
  - ZCTA boundary polygons (simplified for performance)
  - Year slider with play/pause animation
  - Population threshold dropdown (client-side filter)
  - Data availability timeline (sidebar)
  - Live treatment/control stats

Inputs:
    data/clean/coastal_zipcodes_lomr_tr_full_{window}.csv
    data/raw/tiger-census/tl_2025_us_zcta520.shp
    data/raw/us-zips/uszips.csv

Outputs:
    data/clean/plots/treatment_map_{window}.html

Usage:
    python src/scripts/build_treatment_map.py --start-year 2009 --end-year 2022
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

import geopandas as gpd
import pandas as pd

# ==============================================================================
# CONFIGURATION
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..", "..")
CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "clean")
PLOT_DIR = os.path.join(CLEAN_DIR, "plots")
RAW_ZIPS_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "us-zips", "uszips.csv")
CENSUS_POP_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "census-2010", "census_2010_zcta_population.csv")
ZCTA_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "tiger-census", "tl_2025_us_zcta520.shp")

SIMPLIFY_TOLERANCE = 0.002  # ~200m, yields ~4.4 MB GeoJSON for 3,646 ZCTAs


# ==============================================================================
# HTML TEMPLATE
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LOMR Treatment Dashboard — {title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a2e; color: #e0e0e0; }}

  .header {{
    background: #16213e;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    border-bottom: 1px solid #0f3460;
    flex-wrap: wrap;
  }}
  .header h1 {{ font-size: 16px; font-weight: 600; color: #e0e0e0; white-space: nowrap; }}

  .slider-group {{
    flex: 1;
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 300px;
  }}
  .slider-group label {{ font-size: 13px; color: #a0a0a0; white-space: nowrap; }}
  #year-slider {{
    flex: 1; height: 6px;
    -webkit-appearance: none; appearance: none;
    background: #0f3460; border-radius: 3px; outline: none; cursor: pointer;
  }}
  #year-slider::-webkit-slider-thumb {{
    -webkit-appearance: none; width: 20px; height: 20px; border-radius: 50%;
    background: #4fc3f7; border: 2px solid #fff; cursor: grab;
  }}
  #year-display {{
    font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums;
    color: #4fc3f7; min-width: 60px; text-align: center;
  }}

  .btn {{
    background: #0f3460; border: 1px solid #4fc3f7; color: #4fc3f7;
    padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; white-space: nowrap;
  }}
  .btn:hover {{ background: #1a4a7a; }}

  select.filter-select {{
    background: #0f3460; color: #4fc3f7; border: 1px solid #4fc3f7;
    padding: 6px 10px; border-radius: 4px; font-size: 13px; cursor: pointer;
  }}

  .main {{ display: flex; height: calc(100vh - 110px); }}
  #map {{ flex: 1; }}

  .sidebar {{
    width: 280px;
    background: #16213e;
    border-left: 1px solid #0f3460;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}
  .sidebar h2 {{
    font-size: 13px; text-transform: uppercase; letter-spacing: 1px;
    color: #4fc3f7; margin-bottom: 4px;
  }}

  .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
  .stat-card {{
    background: #0f3460; padding: 10px; border-radius: 6px; text-align: center;
  }}
  .stat-card .num {{
    font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums;
  }}
  .stat-card .lbl {{ font-size: 11px; color: #a0a0a0; margin-top: 2px; }}
  .stat-card.treated .num {{ color: #ef5350; }}
  .stat-card.new .num {{ color: #ffa726; }}
  .stat-card.control .num {{ color: #42a5f5; }}
  .stat-card.total .num {{ color: #e0e0e0; }}

  .dataset-list {{ display: flex; flex-direction: column; gap: 6px; }}
  .dataset-row {{ display: flex; align-items: center; gap: 8px; font-size: 12px; }}
  .dataset-bar {{
    flex: 1; height: 14px; background: #0a1a3a; border-radius: 3px;
    position: relative; overflow: hidden;
  }}
  .dataset-fill {{
    position: absolute; top: 0; left: 0; height: 100%;
    border-radius: 3px; transition: width 0.15s;
  }}
  .dataset-name {{ width: 90px; text-align: right; color: #a0a0a0; flex-shrink: 0; font-size: 11px; }}
  .dataset-years {{ width: 72px; font-size: 10px; color: #666; text-align: center; flex-shrink: 0; }}
  .dot-indicator {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}

  .legend-list {{ display: flex; flex-direction: column; gap: 4px; }}
  .legend-row {{ display: flex; align-items: center; gap: 8px; font-size: 12px; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
</style>
</head>
<body>

<div class="header">
  <h1>LOMR Treatment Dashboard</h1>
  <div class="slider-group">
    <label>Year:</label>
    <input type="range" id="year-slider" min="{min_year}" max="{max_year}" value="{min_year}" step="1">
    <div id="year-display">{min_year}</div>
  </div>
  <button class="btn" id="play-btn">Play</button>
  <select class="filter-select" id="pop-filter">
    <option value="0">All zips</option>
    <option value="10000">County pop 10k+</option>
    <option value="25000" selected>County pop 25k+</option>
    <option value="50000">County pop 50k+</option>
  </select>
</div>

<div class="main">
  <div id="map"></div>
  <div class="sidebar">
    <div>
      <h2>Treatment Status</h2>
      <div class="stat-grid">
        <div class="stat-card treated"><div class="num" id="s-treated">0</div><div class="lbl">Treated</div></div>
        <div class="stat-card new"><div class="num" id="s-new">0</div><div class="lbl">New this year</div></div>
        <div class="stat-card control"><div class="num" id="s-control">0</div><div class="lbl">Control</div></div>
        <div class="stat-card total"><div class="num" id="s-total">0</div><div class="lbl">Visible</div></div>
      </div>
    </div>
    <div>
      <h2>Data Availability</h2>
      <div class="dataset-list" id="dataset-panel"></div>
    </div>
    <div>
      <h2>Legend</h2>
      <div class="legend-list" id="legend-panel"></div>
    </div>
  </div>
</div>

<script>
// === DATA ===
var GEOJSON = {geojson_data};
var COUNTY_POP = {county_pop};

var DATASETS = [
  {{ name: 'ZHVI (outcome)',   start: 2000, end: 2025, color: '#ab47bc', gap: null }},
  {{ name: 'NFIP Policies',    start: 2009, end: 2022, color: '#42a5f5', gap: null }},
  {{ name: 'NFIP Claims',      start: 1978, end: 2026, color: '#26c6da', gap: null }},
  {{ name: 'Disaster Decl.',   start: 1953, end: 2026, color: '#66bb6a', gap: null }},
  {{ name: 'BLS Unemploy.',    start: 2000, end: 2025, color: '#ffca28', gap: null }},
  {{ name: 'Building Permits', start: 2004, end: 2025, color: '#ff7043', gap: [2019, 2023] }},
  {{ name: 'LOMR (treatment)', start: 1996, end: 2026, color: '#ef5350', gap: null }}
];

var ANALYSIS_START = {min_year};
var ANALYSIS_END = {max_year};

// === MAP ===
var map = L.map('map', {{ center: [37.5, -96], zoom: 4, preferCanvas: true }});
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '&copy; OpenStreetMap &copy; CARTO', maxZoom: 18
}}).addTo(map);

// === LEGEND ===
(function() {{
  var panel = document.getElementById('legend-panel');
  var items = [
    {{ color: '#ef5350', text: 'Treated (LOMR before year)' }},
    {{ color: '#ffa726', text: 'Newly treated this year' }},
    {{ color: '#42a5f5', text: 'Control (no LOMR)' }},
    {{ color: '#78909c', text: 'Not yet treated' }}
  ];
  items.forEach(function(item) {{
    var row = document.createElement('div');
    row.className = 'legend-row';
    var dot = document.createElement('span');
    dot.className = 'legend-dot';
    dot.style.backgroundColor = item.color;
    var lbl = document.createElement('span');
    lbl.textContent = item.text;
    row.appendChild(dot);
    row.appendChild(lbl);
    panel.appendChild(row);
  }});
}})();

// === DATA AVAILABILITY ===
(function() {{
  var panel = document.getElementById('dataset-panel');
  var rangeStart = ANALYSIS_START - 5;
  var rangeEnd = ANALYSIS_END + 5;
  var totalSpan = rangeEnd - rangeStart;

  DATASETS.forEach(function(ds, i) {{
    var row = document.createElement('div');
    row.className = 'dataset-row';

    var name = document.createElement('span');
    name.className = 'dataset-name';
    name.textContent = ds.name;

    var dot = document.createElement('span');
    dot.className = 'dot-indicator';
    dot.id = 'ds-dot-' + i;
    dot.style.backgroundColor = '#666';

    var bar = document.createElement('div');
    bar.className = 'dataset-bar';

    var fill = document.createElement('div');
    fill.className = 'dataset-fill';
    fill.style.backgroundColor = ds.color;
    fill.style.opacity = '0.3';
    var left = Math.max(0, (ds.start - rangeStart) / totalSpan * 100);
    var right = Math.min(100, (ds.end - rangeStart) / totalSpan * 100);
    fill.style.left = left + '%';
    fill.style.width = (right - left) + '%';
    bar.appendChild(fill);

    var cursor = document.createElement('div');
    cursor.style.cssText = 'position:absolute;top:0;width:2px;height:100%;background:#fff;transition:left 0.15s;';
    cursor.id = 'ds-cursor-' + i;
    bar.appendChild(cursor);

    if (ds.gap) {{
      var gapFill = document.createElement('div');
      gapFill.className = 'dataset-fill';
      gapFill.style.backgroundColor = '#1a1a2e';
      gapFill.style.opacity = '0.8';
      var gL = Math.max(0, (ds.gap[0] - rangeStart) / totalSpan * 100);
      var gR = Math.min(100, (ds.gap[1] - rangeStart) / totalSpan * 100);
      gapFill.style.left = gL + '%';
      gapFill.style.width = (gR - gL) + '%';
      bar.appendChild(gapFill);
    }}

    var years = document.createElement('span');
    years.className = 'dataset-years';
    years.textContent = ds.start + '-' + ds.end;

    row.appendChild(name);
    row.appendChild(dot);
    row.appendChild(bar);
    row.appendChild(years);
    panel.appendChild(row);
  }});
}})();

function updateDataAvailability(year) {{
  var rangeStart = ANALYSIS_START - 5;
  var totalSpan = (ANALYSIS_END + 5) - rangeStart;

  DATASETS.forEach(function(ds, i) {{
    var dot = document.getElementById('ds-dot-' + i);
    var cursor = document.getElementById('ds-cursor-' + i);
    cursor.style.left = Math.max(0, Math.min(100, (year - rangeStart) / totalSpan * 100)) + '%';

    var inRange = year >= ds.start && year <= ds.end;
    var inGap = ds.gap && year >= ds.gap[0] && year <= ds.gap[1];
    dot.style.backgroundColor = (inRange && !inGap) ? '#66bb6a' : inGap ? '#ffa726' : '#ef5350';
  }});
}}

// === GEOJSON LAYER ===
var allLayers = [];
var currentThreshold = 25000;
var currentYear = ANALYSIS_START;

var geoLayer = L.geoJSON(GEOJSON, {{
  style: function() {{
    return {{ weight: 1, color: '#333', fillOpacity: 0.6, fillColor: '#42a5f5' }};
  }},
  onEachFeature: function(feature, layer) {{
    var p = feature.properties;
    layer._props = p;
    layer.bindTooltip('', {{ sticky: true }});
    allLayers.push(layer);
  }}
}}).addTo(map);

// === COLOR HELPERS ===
function getColor(yr, year) {{
  if (yr === null) return '#42a5f5';
  if (yr < year) return '#ef5350';
  if (yr === year) return '#ffa726';
  return '#78909c';
}}

function getStatus(yr, year) {{
  if (yr === null) return 'Control';
  if (yr < year) return 'Treated (' + yr + ')';
  if (yr === year) return 'New this year (' + yr + ')';
  return 'Not yet (first: ' + yr + ')';
}}

// === UPDATE ===
function update() {{
  var nTreated = 0, nNew = 0, nControl = 0;

  allLayers.forEach(function(layer) {{
    var p = layer._props;
    var countyPop = COUNTY_POP[p.cf] || 0;
    var visible = countyPop >= currentThreshold;

    if (!visible) {{
      layer.setStyle({{ fillOpacity: 0, opacity: 0 }});
      layer.unbindTooltip();
      return;
    }}

    var color = getColor(p.yr, currentYear);
    layer.setStyle({{ fillColor: color, fillOpacity: 0.6, opacity: 1, weight: 1, color: '#333' }});

    // Rebind tooltip
    layer.bindTooltip(p.zip + ' — ' + p.city + ', ' + p.st + '\\n' + getStatus(p.yr, currentYear), {{ sticky: true }});

    if (p.yr === null) {{ nControl++; }}
    else if (p.yr < currentYear) {{ nTreated++; }}
    else if (p.yr === currentYear) {{ nNew++; nTreated++; }}
    else {{ nControl++; }}
  }});

  document.getElementById('s-treated').textContent = nTreated;
  document.getElementById('s-new').textContent = nNew;
  document.getElementById('s-control').textContent = nControl;
  document.getElementById('s-total').textContent = nTreated + nControl;

  updateDataAvailability(currentYear);
}}

// === SLIDER ===
var slider = document.getElementById('year-slider');
var display = document.getElementById('year-display');

slider.addEventListener('input', function() {{
  currentYear = parseInt(this.value);
  display.textContent = currentYear;
  update();
}});

// === POP FILTER ===
document.getElementById('pop-filter').addEventListener('change', function() {{
  currentThreshold = parseInt(this.value);
  update();
}});

// === PLAY ===
var playing = false, playInterval = null;
var playBtn = document.getElementById('play-btn');

playBtn.addEventListener('click', function() {{
  if (playing) {{
    clearInterval(playInterval);
    playBtn.textContent = 'Play';
    playing = false;
  }} else {{
    if (parseInt(slider.value) >= parseInt(slider.max)) slider.value = slider.min;
    playing = true;
    playBtn.textContent = 'Stop';
    playInterval = setInterval(function() {{
      var val = parseInt(slider.value) + 1;
      if (val > parseInt(slider.max)) {{
        clearInterval(playInterval);
        playBtn.textContent = 'Play';
        playing = false;
        return;
      }}
      slider.value = val;
      display.textContent = val;
      currentYear = val;
      update();
    }}, 600);
  }}
}});

// === INIT ===
update();
</script>
</body>
</html>
"""


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build interactive treatment boundary map")
    parser.add_argument("--start-year", type=int, default=2009)
    parser.add_argument("--end-year", type=int, default=2022)
    args = parser.parse_args()

    start_year = args.start_year
    end_year = args.end_year
    window_suffix = f"_{start_year}-{end_year}"

    # Load treatment CSV (full, no pop filter)
    input_path = os.path.join(CLEAN_DIR, f"coastal_zipcodes_lomr_tr_full{window_suffix}.csv")
    print(f"Loading treatment data: {input_path}")
    if not os.path.exists(input_path):
        print(f"ERROR: Not found. Run: python src/scripts/overlay_lomr_zcta.py --threshold full --start-year {start_year} --end-year {end_year}")
        sys.exit(1)

    df = pd.read_csv(input_path, dtype={"zip": str, "county_fips": str})
    df["first_lomr_date"] = pd.to_datetime(df["first_lomr_date"])
    df["lomr_year"] = df["first_lomr_date"].dt.year
    print(f"  {len(df):,} zips")

    # Load ZCTA boundaries
    print(f"Loading ZCTA boundaries: {ZCTA_PATH}")
    coastal_zips = set(df["zip"])
    zcta = gpd.read_file(ZCTA_PATH)
    zcta = zcta[zcta["ZCTA5CE20"].isin(coastal_zips)].copy()
    zcta = zcta.to_crs("EPSG:4326")
    print(f"  {len(zcta):,} ZCTA polygons matched")

    # Simplify for performance
    print(f"  Simplifying geometries (tolerance={SIMPLIFY_TOLERANCE}) ...")
    zcta["geometry"] = zcta.geometry.simplify(SIMPLIFY_TOLERANCE)

    # Join treatment data onto ZCTA features
    zip_props = {}
    for _, row in df.iterrows():
        zip_props[row["zip"]] = {
            "zip": row["zip"],
            "city": str(row.get("city", "")),
            "st": str(row.get("state_id", "")),
            "cf": str(row.get("county_fips", "")),
            "yr": int(row["lomr_year"]) if pd.notna(row["lomr_year"]) else None,
        }

    # Build GeoJSON FeatureCollection manually for compact output
    features = []
    for _, row in zcta.iterrows():
        zc = row["ZCTA5CE20"]
        props = zip_props.get(zc)
        if props is None:
            continue
        geom = row.geometry.__geo_interface__
        features.append({"type": "Feature", "properties": props, "geometry": geom})

    geojson_obj = {"type": "FeatureCollection", "features": features}
    geojson_str = json.dumps(geojson_obj, separators=(",", ":"))
    print(f"  GeoJSON: {len(geojson_str)/1024/1024:.1f} MB ({len(features)} features)")

    # Compute county populations (2010 Census, with SimpleMaps fallback)
    print(f"Computing county populations ...")
    census_pop = {}
    if os.path.exists(CENSUS_POP_PATH):
        with open(CENSUS_POP_PATH, newline="") as f:
            for row in csv.DictReader(f):
                z = row.get("zip", "").strip()
                pop = row.get("population", "")
                if z and pop:
                    try:
                        census_pop[z] = int(float(pop))
                    except ValueError:
                        pass

    county_pop = defaultdict(int)
    with open(RAW_ZIPS_PATH, newline="") as f:
        for row in csv.DictReader(f):
            fips = row.get("county_fips", "").strip()
            z = row.get("zip", "").strip()
            if not fips:
                continue
            if z in census_pop:
                county_pop[fips] += census_pop[z]
            else:
                pop = row.get("population", "")
                if pop:
                    try:
                        county_pop[fips] += int(float(pop))
                    except ValueError:
                        pass

    coastal_fips = set(df["county_fips"].dropna().unique())
    county_pop_filtered = {k: v for k, v in county_pop.items() if k in coastal_fips}
    print(f"  {len(county_pop_filtered)} counties")

    # Generate HTML
    title = f"{start_year}-{end_year}"
    html = HTML_TEMPLATE.format(
        title=title,
        geojson_data=geojson_str,
        county_pop=json.dumps(county_pop_filtered, separators=(",", ":")),
        min_year=start_year,
        max_year=end_year,
    )

    os.makedirs(PLOT_DIR, exist_ok=True)
    out_path = os.path.join(PLOT_DIR, f"treatment_map{window_suffix}.html")
    with open(out_path, "w") as f:
        f.write(html)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"\nSaved: {out_path} ({size_mb:.1f} MB)")
    print(f"Open: file://{os.path.abspath(out_path)}")

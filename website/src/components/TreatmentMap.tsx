"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import * as d3 from "d3";
import * as topojson from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import usTopoRaw from "../../public/data/us-states-10m.json";
import zipTopoRaw from "../../public/data/coastal_zips.json";

// ============================================================
// TreatmentMap - US map with sample zip code outlines
// ============================================================

const usTopo = usTopoRaw as unknown as Topology;
const zipTopo = zipTopoRaw as unknown as Topology;
const zipObjKey = Object.keys(zipTopo.objects)[0];

interface ZipProps {
  z: string;
  ct: number;
  tr: number;
  yr?: number;
  pop?: number;
  den?: number;
  is?: number;
  nl?: number;
  ci?: string; // city
  st?: string; // state
  co?: string; // county
  rep?: number; // 2020 Republican two-party vote share
  hv?: Record<string, number>; // yearly ZHVI {\"2009\": val, ..., \"2022\": val}
  hv22?: number; // 2022 median ZHVI (for threshold filter)
}

type MapMode = "treatment" | "population" | "density" | "politics" | "home-values";

const YEAR_ALL = 0;
const YEAR_MIN = 2009;
const YEAR_MAX = 2022;
const YEAR_STEPS = [
  YEAR_ALL,
  ...Array.from({ length: YEAR_MAX - YEAR_MIN + 1 }, (_, i) => YEAR_MIN + i),
];

const COLORS_DARK = {
  treated: "#ef4444",
  control: "#3b82f6",
  excluded: "#2a2d3a",
  zipFill: "#1a1d27",
  stateFill: "#1a1d27",
  stateBorder: "#3d4155",
  zipBorder: "rgba(255,255,255,0.15)",
  cityLabel: "rgba(255,255,255,0.7)",
  cityLabelShadow: "0 1px 3px rgba(0,0,0,0.8)",
  selectHighlight: "#ffffff",
  hoverHighlight: "rgba(255,255,255,0.45)",
};

const COLORS_LIGHT = {
  treated: "#dc2626",
  control: "#2563eb",
  excluded: "#e5e7eb",
  zipFill: "#f3f4f6",
  stateFill: "#f3f4f6",
  stateBorder: "#d1d5db",
  zipBorder: "rgba(0,0,0,0.1)",
  cityLabel: "rgba(0,0,0,0.6)",
  cityLabelShadow: "0 1px 3px rgba(255,255,255,0.8)",
  selectHighlight: "#111827",
  hoverHighlight: "rgba(0,0,0,0.15)",
};

// Default to dark — component will override with theme state
let COLORS = COLORS_DARK;

/** Zip is a treated zip in the regression sample (ever_treated = 1) */
function isTreated(p: ZipProps): boolean {
  return p.is === 1 && p.tr === 1;
}

/** Zip is in the regression sample at all (treated or control) */
function isInSample(p: ZipProps): boolean {
  return p.is === 1;
}

function zipColor(p: ZipProps, year: number): string {
  if (!isInSample(p)) return COLORS.excluded;
  if (isTreated(p) && (year === YEAR_ALL || (p.yr != null && p.yr <= year)))
    return COLORS.treated;
  return COLORS.control;
}


// Precompute treatment counts and control relevance from TopoJSON (module-level, runs once)
const allZipFeatures = topojson.feature(
  zipTopo,
  zipTopo.objects[zipObjKey] as GeometryCollection,
).features;
const treatedZips = allZipFeatures.filter((f) => isTreated(f.properties as ZipProps));
const controlZips = allZipFeatures.filter((f) => {
  const p = f.properties as ZipProps;
  return isInSample(p) && p.tr === 0;
});
const TOTAL_TREATED = treatedZips.length;
const TOTAL_CONTROL = controlZips.length;

// Population color scale (log scale for better visual spread)
const pops = allZipFeatures
  .map((f) => (f.properties as ZipProps).pop ?? 0)
  .filter((p) => p > 0);
const popExtent = d3.extent(pops) as [number, number];
const popColorScale = d3
  .scaleSequentialLog(d3.interpolateYlOrRd)
  .domain(popExtent);

function popColor(p: ZipProps): string {
  if (!p.pop || p.pop <= 0) return COLORS.zipFill;
  return popColorScale(p.pop);
}

// Density color scale (log scale, people per sq mi)
const densities = allZipFeatures
  .map((f) => (f.properties as ZipProps).den ?? 0)
  .filter((d) => d > 0);
const denExtent = d3.extent(densities) as [number, number];
const denColorScale = d3
  .scaleSequentialLog(d3.interpolateViridis)
  .domain(denExtent);

function denColor(p: ZipProps): string {
  if (!p.den || p.den <= 0) return COLORS.zipFill;
  return denColorScale(p.den);
}

// Politics color scale (blue-white-red, 0=full Dem, 1=full Rep)
const polColorScale = d3.scaleLinear<string>()
  .domain([0.3, 0.5, 0.7])
  .range(["#3b82f6", "#e8e8e8", "#ef4444"])
  .clamp(true);

function polColor(p: ZipProps): string {
  if (p.rep == null) return COLORS.zipFill;
  return polColorScale(p.rep);
}

// Home-value color scale (sequential green-yellow-red, log scale)
const hvValues = allZipFeatures
  .map((f) => (f.properties as ZipProps).hv22 ?? 0)
  .filter((v) => v > 0);
const hvExtent = d3.extent(hvValues) as [number, number];
const hvColorScale = d3
  .scaleSequentialLog(d3.interpolateYlOrRd)
  .domain(hvExtent);

function getNoDataColor() {
  return COLORS === COLORS_LIGHT ? "#d1d5db" : "#3d3d4d";
}

function hvColor(p: ZipProps, year: number): string {
  const yr = year === YEAR_ALL ? "2022" : String(year);
  const val = p.hv?.[yr];
  if (val == null || val <= 0) return getNoDataColor();
  return hvColorScale(Math.max(hvExtent[0], Math.min(hvExtent[1], val)));
}

// Search index — flat array built once from TopoJSON properties
interface SearchEntry {
  label: string;
  zip: string;
  searchText: string;
}
const searchIndex: SearchEntry[] = allZipFeatures.map((f) => {
  const p = f.properties as ZipProps;
  const city = p.ci ?? "";
  const state = p.st ?? "";
  const county = p.co ?? "";
  const label = city
    ? `${city}, ${state} (${p.z})${county ? ` · ${county}` : ""}`
    : `${p.z} · ${state}`;
  return {
    label,
    zip: p.z,
    searchText: `${p.z} ${city} ${state} ${county}`.toLowerCase(),
  };
});

interface TooltipData {
  zip: string;
  city?: string;
  state?: string;
  county?: string;
  treated: boolean;
  inSample: boolean;
  year?: number;
  pop?: number;
  den?: number;
  hv22?: number;
  hv?: Record<string, number>;
  x: number;
  y: number;
}

export default function TreatmentMap() {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [theme, setTheme] = useState("dark");

  // Theme observer — re-render map when theme changes
  useEffect(() => {
    const el = document.documentElement;
    const update = () => {
      const isLight = el.classList.contains("light");
      COLORS = isLight ? COLORS_LIGHT : COLORS_DARK;
      setTheme(isLight ? "light" : "dark");
    };
    update();
    const observer = new MutationObserver(update);
    observer.observe(el, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);
  const [year, setYear] = useState(YEAR_ALL);
  const yearRef = useRef(YEAR_ALL);
  const [isPlaying, setIsPlaying] = useState(true);
  const [mapMode, setMapMode] = useState<MapMode>("treatment");
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [popMin, setPopMin] = useState(0);
  const [denMin, setDenMin] = useState(0);
  const [hviMin, setHviMin] = useState(0);
  const [hviMax, setHviMax] = useState(0);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [selectedZip, setSelectedZip] = useState<string | null>(null);
  const selectedZipRef = useRef<string | null>(null);
  const pinnedTooltipRef = useRef<TooltipData | null>(null);
  const [showLabels, setShowLabels] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchEntry[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchHighlight, setSearchHighlight] = useState(0);
  const searchRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown>>();
  const pathRef = useRef<d3.GeoPath>();
  const validZipsRef = useRef<typeof allZipFeatures>([]);

  // Track native fullscreen changes
  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  // Resize observer
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width > 0) {
        setDimensions({
          width,
          height: isFullscreen ? height : width * 0.58,
        });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [isFullscreen]);

  // D3 rendering
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || dimensions.width === 0) return;

    const { width, height } = dimensions;
    const sel = d3.select(svg);
    sel.selectAll("*").remove();
    sel
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", `0 0 ${width} ${height}`);

    // Clip to viewport — some zip MultiPolygons have inverted winding
    // that fills the entire plane; clipping hides the overflow
    sel.append("defs").append("clipPath").attr("id", "map-clip")
      .append("rect").attr("width", width).attr("height", height);
    const g = sel.append("g").attr("clip-path", "url(#map-clip)");

    // Projection — lower 48 + DC only (FIPS 01–56, excluding AK=02, HI=15)
    const statesGeo = topojson.feature(
      usTopo,
      usTopo.objects.states as GeometryCollection,
    );
    statesGeo.features = statesGeo.features.filter((f) => {
      const fips = Number(f.id);
      return fips >= 1 && fips <= 56 && fips !== 2 && fips !== 15;
    });

    // Zoom behavior — constrained to SVG bounds
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 20])
      .translateExtent([[0, 0], [width, height]])
      .on("zoom", (event) => g.attr("transform", event.transform));
    zoomRef.current = zoom;
    sel.call(zoom);
    sel.on("dblclick.zoom", () => {
      sel.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
      selectedZipRef.current = null;
      setSelectedZip(null);
      pinnedTooltipRef.current = null;
      setTooltip(null);
      sel.select(".zip-highlight").selectAll("*").remove();
    });
    // Click on background (non-zip area) clears selection
    sel.on("click", (event) => {
      if ((event.target as Element).classList.contains("zip-poly")) return;
      if (!selectedZipRef.current) return;
      selectedZipRef.current = null;
      setSelectedZip(null);
      pinnedTooltipRef.current = null;
      setTooltip(null);
      sel.select(".zip-highlight").selectAll("*").remove();
    });
    const projection = d3.geoAlbers().fitSize([width, height], statesGeo);
    const path = d3.geoPath(projection);
    pathRef.current = path;

    // State fills
    g.append("g")
      .attr("class", "states")
      .selectAll("path")
      .data(statesGeo.features)
      .join("path")
      .attr("d", path)
      .style("fill", COLORS.stateFill)
      .style("stroke", COLORS.stateBorder)
      .style("stroke-width", "0.8");

    // Zip polygons — only in-sample zips, treated on top
    const zipGeo = topojson.feature(
      zipTopo,
      zipTopo.objects[zipObjKey] as GeometryCollection,
    );
    const viewportArea = width * height;
    const validZips = zipGeo.features.filter((f) => {
      const p = f.properties as ZipProps;
      return p.is === 1 && path.area(f) < viewportArea;
    });
    validZipsRef.current = validZips;
    const sorted = [...validZips].sort((a, b) => {
      const aT = (a.properties as ZipProps).tr;
      const bT = (b.properties as ZipProps).tr;
      return aT - bT;
    });
    g.append("g")
      .attr("class", "zips")
      .selectAll("path")
      .data(sorted)
      .join("path")
      .attr("class", "zip-poly")
      .attr("d", path)
      .style("fill", (d) => zipColor(d.properties as ZipProps, yearRef.current))
      .style("fill-rule", "evenodd")
      .style("stroke", COLORS.zipBorder)
      .style("stroke-width", "0.2")
      .on("mouseenter", function (event, d) {
        const p = d.properties as ZipProps;
        const container = containerRef.current;
        const svgEl = svgRef.current;
        if (!container || !svgEl) return;
        const rect = container.getBoundingClientRect();
        // Show hover highlight in overlay (renders over state borders)
        if (p.z !== selectedZipRef.current) {
          const overlay = d3.select(svgEl).select<SVGGElement>(".zip-hover");
          overlay.selectAll("*").remove();
          overlay.append("path")
            .datum(d)
            .attr("d", path)
            .style("fill", COLORS.hoverHighlight)
            .style("fill-rule", "evenodd")
            .style("stroke", "none")
            .style("pointer-events", "none");
        }
        setTooltip({
          zip: p.z,
          city: p.ci,
          state: p.st,
          county: p.co,
          treated: isTreated(p),
          inSample: isInSample(p),
          year: p.yr,
          pop: p.pop,
          den: p.den,
          hv22: p.hv22,
          hv: p.hv,
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
        });
      })
      .on("mousemove", function (event) {
        const container = containerRef.current;
        if (!container) return;
        const rect = container.getBoundingClientRect();
        setTooltip((prev) =>
          prev ? { ...prev, x: event.clientX - rect.left, y: event.clientY - rect.top } : null,
        );
      })
      .on("mouseleave", function () {
        const svgEl = svgRef.current;
        if (svgEl) d3.select(svgEl).select(".zip-hover").selectAll("*").remove();
        setTooltip(pinnedTooltipRef.current);
      })
      .on("click", function (event, d) {
        const p = d.properties as ZipProps;
        const svg = svgRef.current;
        const container = containerRef.current;
        if (!svg || !container) return;
        const wasSelected = selectedZipRef.current === p.z;
        const newZip = wasSelected ? null : p.z;
        selectedZipRef.current = newZip;
        setSelectedZip(newZip);
        // Update highlight overlay
        const overlay = d3.select(svg).select<SVGGElement>(".zip-highlight");
        overlay.selectAll("*").remove();
        if (newZip) {
          const feature = validZips.find((f) => (f.properties as ZipProps).z === newZip);
          if (feature) {
            overlay.append("path")
              .datum(feature)
              .attr("d", path)
              .style("fill", COLORS.selectHighlight)
              .style("fill-rule", "evenodd")
              .style("stroke", "none")
              .style("pointer-events", "none");
          }
          // Pin tooltip at click position
          const rect = container.getBoundingClientRect();
          const pinned: TooltipData = {
            zip: p.z, city: p.ci, state: p.st, county: p.co,
            treated: isTreated(p), inSample: isInSample(p),
            year: p.yr, pop: p.pop, den: p.den,
            hv22: p.hv22, hv: p.hv,
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
          };
          pinnedTooltipRef.current = pinned;
          setTooltip(pinned);
        } else {
          pinnedTooltipRef.current = null;
          setTooltip(null);
        }
      });

    // State borders on top (lower 48 only)
    const isLower48 = (id: unknown) => {
      const fips = Number(id);
      return fips >= 1 && fips <= 56 && fips !== 2 && fips !== 15;
    };
    g.append("path")
      .datum(
        topojson.mesh(
          usTopo,
          usTopo.objects.states as GeometryCollection,
          (a, b) => isLower48(a.id) && isLower48(b.id),
        ),
      )
      .attr("d", path)
      .style("fill", "none")
      .style("stroke", COLORS.stateBorder)
      .style("stroke-width", "0.8")
      .style("pointer-events", "none");

    // Hover + selection overlays — render on top of state borders
    g.append("g").attr("class", "zip-hover").style("pointer-events", "none");
    g.append("g").attr("class", "zip-highlight").style("pointer-events", "none");

    // City labels for major coastal clusters
    const cities: { name: string; lng: number; lat: number; anchor?: string }[] = [
      { name: "Seattle", lng: -122.33, lat: 47.61 },
      { name: "Portland", lng: -122.68, lat: 45.52 },
      { name: "San Francisco", lng: -122.42, lat: 37.77 },
      { name: "Los Angeles", lng: -118.24, lat: 34.05 },
      { name: "San Diego", lng: -117.16, lat: 32.72 },
      { name: "Houston", lng: -95.37, lat: 29.76 },
      { name: "New Orleans", lng: -90.07, lat: 29.95 },
      { name: "Tampa", lng: -82.46, lat: 27.95 },
      { name: "Miami", lng: -80.19, lat: 25.76 },
      { name: "Charleston", lng: -79.93, lat: 32.78 },
      { name: "Virginia Beach", lng: -75.98, lat: 36.85 },
      { name: "Washington DC", lng: -77.04, lat: 38.91, anchor: "end" },
      { name: "Philadelphia", lng: -75.17, lat: 39.95, anchor: "end" },
      { name: "New York", lng: -74.01, lat: 40.71 },
      { name: "Boston", lng: -71.06, lat: 42.36 },
    ];
    const labelsG = g.append("g").attr("class", "city-labels").style("pointer-events", "none");
    labelsG
      .selectAll("text")
      .data(cities)
      .join("text")
      .attr("x", (d) => projection([d.lng, d.lat])?.[0] ?? 0)
      .attr("y", (d) => projection([d.lng, d.lat])?.[1] ?? 0)
      .attr("dx", (d) => d.anchor === "end" ? -6 : 6)
      .attr("dy", -6)
      .attr("text-anchor", (d) => d.anchor ?? "start")
      .text((d) => d.name)
      .style("fill", COLORS.cityLabel)
      .style("font-size", "9px")
      .style("font-family", "var(--font-mono, monospace)")
      .style("text-shadow", COLORS.cityLabelShadow);
  }, [dimensions, theme]);

  // Toggle city label visibility
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    d3.select(svg).select(".city-labels").style("display", showLabels ? "block" : "none");
  }, [showLabels, dimensions]);

  // Close search dropdown on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Search handler
  const handleSearch = useCallback((q: string) => {
    setSearchQuery(q);
    setSearchHighlight(0);
    if (q.length < 2) {
      setSearchResults([]);
      setSearchOpen(false);
      return;
    }
    const lower = q.toLowerCase();
    const results = searchIndex.filter((e) => e.searchText.includes(lower)).slice(0, 8);
    setSearchResults(results);
    setSearchOpen(results.length > 0);
  }, []);

  // Zoom to a zip on search selection
  const zoomToZip = useCallback((zip: string) => {
    setSearchQuery("");
    setSearchResults([]);
    setSearchOpen(false);
    const svg = svgRef.current;
    const zoom = zoomRef.current;
    const path = pathRef.current;
    const validZips = validZipsRef.current;
    const container = containerRef.current;
    if (!svg || !zoom || !path || !validZips.length) return;
    const feature = validZips.find((f) => (f.properties as ZipProps).z === zip);
    if (!feature) return;
    // Zoom to feature bounds
    const [[x0, y0], [x1, y1]] = path.bounds(feature);
    const { width, height } = dimensions;
    const dx = x1 - x0;
    const dy = y1 - y0;
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    const scale = Math.min(8, 0.8 / Math.max(dx / width, dy / height));
    const translate = [width / 2 - scale * cx, height / 2 - scale * cy];
    const transform = d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale);
    d3.select(svg).transition().duration(750).call(zoom.transform, transform);
    // Select the zip
    selectedZipRef.current = zip;
    setSelectedZip(zip);
    const overlay = d3.select(svg).select<SVGGElement>(".zip-highlight");
    overlay.selectAll("*").remove();
    overlay.append("path")
      .datum(feature)
      .attr("d", path)
      .style("fill", COLORS.selectHighlight)
      .style("fill-rule", "evenodd")
      .style("stroke", "none")
      .style("pointer-events", "none");
    // Show pinned tooltip for the selected zip (centered in viewport after zoom)
    const p = feature.properties as ZipProps;
    const cW = container?.offsetWidth ?? width;
    const cH = container?.offsetHeight ?? height;
    const pinned: TooltipData = {
      zip: p.z, city: p.ci, state: p.st, county: p.co,
      treated: isTreated(p), inSample: isInSample(p),
      year: p.yr, pop: p.pop, den: p.den,
      hv22: p.hv22, hv: p.hv,
      x: cW / 2, y: cH / 2,
    };
    pinnedTooltipRef.current = pinned;
    setTooltip(pinned);
  }, [dimensions]);

  // Update zip fill colors when year, mode, or filters change (without redrawing the map)
  useEffect(() => {
    yearRef.current = year;
    const svg = svgRef.current;
    if (!svg || dimensions.width === 0) return;
    d3.select(svg)
      .selectAll<SVGPathElement, { properties: ZipProps }>(".zip-poly")
      .style("fill", (d) => {
        const p = d.properties;
        // Apply population/density minimum filters
        if (popMin > 0 && (p.pop ?? 0) < popMin) return COLORS.zipFill;
        if (denMin > 0 && (p.den ?? 0) < denMin) return COLORS.zipFill;
        // Apply home-value min/max filter (always uses 2022 values)
        if (hviMin > 0 && (p.hv22 ?? 0) < hviMin) return COLORS.zipFill;
        if (hviMax > 0 && (p.hv22 ?? Infinity) > hviMax) return COLORS.zipFill;
        if (mapMode === "treatment") return zipColor(p, year);
        // For heatmap modes, only color zips active at the current year
        const active =
          year === YEAR_ALL ||
          p.tr === 0 ||
          (isTreated(p) && p.yr! <= year);
        if (!active) return COLORS.zipFill;
        if (mapMode === "population") return popColor(p);
        if (mapMode === "politics") return polColor(p);
        if (mapMode === "home-values") return hvColor(p, year);
        return denColor(p);
      });
  }, [year, dimensions, mapMode, popMin, denMin, hviMin, hviMax, theme]);

  // Auto-play: advance year on a timer
  useEffect(() => {
    if (!isPlaying) return;
    const delay = year === YEAR_ALL ? 3000 : 1500;
    const timer = setTimeout(() => {
      const idx = YEAR_STEPS.indexOf(year);
      const next = idx >= YEAR_STEPS.length - 1 ? 0 : idx + 1;
      setYear(YEAR_STEPS[next]);
    }, delay);
    return () => clearTimeout(timer);
  }, [isPlaying, year]);

  // Check if a zip passes the population/density filters
  const passesFilter = useCallback(
    (p: ZipProps) => {
      if (popMin > 0 && (p.pop ?? 0) < popMin) return false;
      if (denMin > 0 && (p.den ?? 0) < denMin) return false;
      if (hviMin > 0 && (p.hv22 ?? 0) < hviMin) return false;
      if (hviMax > 0 && (p.hv22 ?? Infinity) > hviMax) return false;
      return true;
    },
    [popMin, denMin, hviMin, hviMax],
  );

  // Count treated zips visible at current year (respecting filters)
  const filteredTreated = treatedZips.filter((f) => passesFilter(f.properties as ZipProps));
  const treatedCount =
    year === YEAR_ALL
      ? filteredTreated.length
      : filteredTreated.filter((f) => {
          const p = f.properties as ZipProps;
          return p.yr !== undefined && p.yr <= year;
        }).length;

  const filteredTotal = filteredTreated.length;
  const controlCount = controlZips.filter((f) => passesFilter(f.properties as ZipProps)).length;

  const sliderIndex = YEAR_STEPS.indexOf(year);

  const toggleFullscreen = useCallback(() => {
    const el = wrapperRef.current;
    if (!el) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      el.requestFullscreen();
    }
  }, []);

  return (
    <div
      ref={wrapperRef}
      className="w-full flex flex-col"
      style={
        isFullscreen
          ? { background: "var(--color-bg)", padding: "16px" }
          : undefined
      }
    >
      <div
        ref={containerRef}
        className={`relative rounded-lg overflow-hidden ${isFullscreen ? "flex-1" : ""}`}
        style={{
          background: "var(--color-bg)",
          border: "1px solid var(--color-border)",
        }}
      >
        <svg
          ref={svgRef}
          className="w-full cursor-grab active:cursor-grabbing"
        />

        {/* Tooltip */}
        {tooltip && (
          <div
            ref={tooltipRef}
            className="absolute z-20 rounded-lg px-3 py-2 text-[11px] pointer-events-none"
            style={{
              left: (() => {
                const pad = 8;
                const ttW = tooltipRef.current?.offsetWidth ?? 180;
                const cW = containerRef.current?.offsetWidth ?? dimensions.width;
                let x = tooltip.x + 12;
                if (x + ttW > cW - pad) x = tooltip.x - ttW - 12;
                return Math.max(pad, x);
              })(),
              top: (() => {
                const pad = 8;
                const ttH = tooltipRef.current?.offsetHeight ?? 80;
                const cH = containerRef.current?.offsetHeight ?? dimensions.height;
                let y = tooltip.y - ttH - 12;
                if (y < pad) y = tooltip.y + 16;
                return Math.min(cH - ttH - pad, Math.max(pad, y));
              })(),
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text)",
              boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
              whiteSpace: "nowrap",
            }}
          >
            <div className="font-semibold text-[13px]">
              {tooltip.city ? `${tooltip.city}, ${tooltip.state}` : `ZIP ${tooltip.zip}`}
            </div>
            <div className="text-[11px] mb-1" style={{ color: "var(--color-text-secondary)" }}>
              {tooltip.city && <>{tooltip.zip} · </>}
              <span style={{
                color: !tooltip.inSample ? "var(--color-text-secondary)" : tooltip.treated ? COLORS.treated : COLORS.control,
                fontWeight: 600,
              }}>
                {!tooltip.inSample ? "Excluded" : tooltip.treated ? "Treated" : "Control"}
              </span>
              {tooltip.treated && tooltip.year && <> · LOMR {tooltip.year}</>}
              {tooltip.county && <> · {tooltip.county}</>}
            </div>
            <div className="flex flex-col gap-0.5 text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
              {(tooltip.pop != null || tooltip.den != null) && (
                <span>
                  {tooltip.pop != null && <>{tooltip.pop.toLocaleString()} pop</>}
                  {tooltip.pop != null && tooltip.den != null && " · "}
                  {tooltip.den != null && <>{tooltip.den.toLocaleString()}/mi²</>}
                </span>
              )}
              {(() => {
                const hvYear = year === YEAR_ALL ? "2022" : String(year);
                const hvVal = tooltip.hv?.[hvYear];
                const label = year === YEAR_ALL ? "2022" : year;
                if (hvVal != null) return <span>${hvVal.toLocaleString()} ({label})</span>;
                return <span style={{ opacity: 0.5 }}>No home value data ({label})</span>;
              })()}
            </div>
          </div>
        )}

        {/* Legend — hidden on mobile (shown below map instead) */}
        <div
          className="hidden sm:flex absolute bottom-3 left-3 flex-col gap-1.5 px-3 py-2 rounded text-[11px]"
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-secondary)",
          }}
        >
          {mapMode === "treatment" ? (
            <>
              {[
                { color: COLORS.treated, label: year === YEAR_ALL ? "Treated (single LOMR)" : `Treated (by ${year})` },
                { color: COLORS.control, label: "Control (never / not-yet treated)" },
              ].map(({ color, label }) => (
                <div key={label} className="flex items-center gap-2">
                  <span
                    className="inline-block w-2.5 h-2.5 rounded-sm"
                    style={{ background: color }}
                  />
                  {label}
                </div>
              ))}
            </>
          ) : mapMode === "population" ? (
            <>
              <div className="flex items-center gap-2 mb-0.5">Population</div>
              <div
                className="h-2 rounded-sm"
                style={{
                  width: "100px",
                  background: `linear-gradient(to right, ${popColorScale(popExtent[0])}, ${popColorScale(Math.sqrt(popExtent[0] * popExtent[1]))}, ${popColorScale(popExtent[1])})`,
                }}
              />
              <div className="flex justify-between text-[9px]" style={{ width: "100px" }}>
                <span>{popExtent[0].toLocaleString()}</span>
                <span>{popExtent[1].toLocaleString()}</span>
              </div>
            </>
          ) : mapMode === "density" ? (
            <>
              <div className="flex items-center gap-2 mb-0.5">Density (per mi&sup2;)</div>
              <div
                className="h-2 rounded-sm"
                style={{
                  width: "100px",
                  background: `linear-gradient(to right, ${denColorScale(denExtent[0])}, ${denColorScale(Math.sqrt(denExtent[0] * denExtent[1]))}, ${denColorScale(denExtent[1])})`,
                }}
              />
              <div className="flex justify-between text-[9px]" style={{ width: "100px" }}>
                <span>{Math.round(denExtent[0]).toLocaleString()}</span>
                <span>{Math.round(denExtent[1]).toLocaleString()}</span>
              </div>
            </>
          ) : mapMode === "politics" ? (
            <>
              <div className="flex items-center gap-2 mb-0.5">2020 Presidential Vote</div>
              <div
                className="h-2 rounded-sm"
                style={{
                  width: "100px",
                  background: `linear-gradient(to right, ${polColorScale(0.3)}, ${polColorScale(0.5)}, ${polColorScale(0.7)})`,
                }}
              />
              <div className="flex justify-between text-[9px]" style={{ width: "100px" }}>
                <span>D+40</span>
                <span>Even</span>
                <span>R+40</span>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-0.5">
                Median Home Value {year === YEAR_ALL ? "(2022)" : `(${year})`}
              </div>
              <div
                className="h-2 rounded-sm"
                style={{
                  width: "100px",
                  background: `linear-gradient(to right, ${hvColorScale(hvExtent[0])}, ${hvColorScale(Math.sqrt(hvExtent[0] * hvExtent[1]))}, ${hvColorScale(hvExtent[1])})`,
                }}
              />
              <div className="flex justify-between text-[9px]" style={{ width: "100px" }}>
                <span>${(hvExtent[0] / 1000).toFixed(0)}K</span>
                <span>${(hvExtent[1] / 1e6).toFixed(1)}M</span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-sm"
                  style={{ background: getNoDataColor() }}
                />
                No data
              </div>
            </>
          )}
        </div>

        {/* Zoom hint — hidden on mobile */}
        <div
          className="hidden sm:block absolute bottom-2 right-2 text-[10px] px-2 py-1 rounded"
          style={{
            background: "var(--color-surface)",
            color: "var(--color-text-secondary)",
            border: "1px solid var(--color-border)",
          }}
        >
          Scroll to zoom · Drag to pan · Double-click to reset
        </div>

        {/* Top toolbar — hidden on mobile (controls shown below map instead) */}
        <div className="hidden sm:flex absolute top-3 left-3 right-3 z-10 items-center gap-2">
          {/* Mode toggle */}
          <div
            className="flex rounded-md overflow-hidden text-[11px] font-medium shrink-0"
            style={{ border: "1px solid var(--color-border)" }}
          >
            {(["treatment", "population", "density", "politics", "home-values"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setMapMode(mode)}
                className="px-3 py-1.5 transition-colors capitalize"
                style={{
                  background: mapMode === mode ? "var(--color-accent)" : "var(--color-surface)",
                  color: mapMode === mode ? "#fff" : "var(--color-text-secondary)",
                }}
              >
                {mode === "home-values" ? "Home Values" : mode}
              </button>
            ))}
          </div>

          <div className="flex-1" />

          {/* Search bar */}
          <div ref={searchRef} className="relative min-w-0 max-w-[260px] w-[220px]">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              onFocus={() => { if (searchResults.length > 0) setSearchOpen(true); }}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  setSearchOpen(false);
                  (e.target as HTMLInputElement).blur();
                } else if (e.key === "ArrowDown") {
                  e.preventDefault();
                  setSearchHighlight((prev) => Math.min(prev + 1, searchResults.length - 1));
                } else if (e.key === "ArrowUp") {
                  e.preventDefault();
                  setSearchHighlight((prev) => Math.max(prev - 1, 0));
                } else if (e.key === "Enter" && searchOpen && searchResults.length > 0) {
                  e.preventDefault();
                  zoomToZip(searchResults[searchHighlight].zip);
                }
              }}
              placeholder="Search zip, city, county..."
              className="w-full px-2 py-1.5 rounded-md text-[11px] outline-none"
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                color: "var(--color-text)",
              }}
            />
            {searchOpen && searchResults.length > 0 && (
              <div
                className="absolute top-full left-0 right-0 mt-1 rounded-md overflow-hidden text-[11px] max-h-[240px] overflow-y-auto"
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                }}
              >
                {searchResults.map((r, i) => (
                  <button
                    key={r.zip}
                    onClick={() => zoomToZip(r.zip)}
                    onMouseEnter={() => setSearchHighlight(i)}
                    className="w-full text-left px-2.5 py-1.5 transition-colors truncate"
                    style={{
                      color: "var(--color-text)",
                      background: i === searchHighlight ? "var(--color-accent)" : "transparent",
                      borderBottom: "1px solid var(--color-border)",
                    }}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex-1" />

          {/* Compact filter inputs */}
          <div
            className="flex items-center gap-2 px-2 py-1 rounded-md text-[10px] font-mono shrink-0"
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text-secondary)",
            }}
          >
            <label className="flex items-center gap-1">
              Pop&ge;
              <input
                type="text"
                inputMode="numeric"
                value={popMin || ""}
                placeholder="Any"
                onChange={(e) => setPopMin(Number(e.target.value.replace(/\D/g, "")) || 0)}
                className="w-14 px-1 py-0.5 rounded text-[10px] font-mono text-right outline-none"
                style={{
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text)",
                  boxShadow: "none",
                  WebkitAppearance: "none",
                }}
              />
            </label>
            <label className="flex items-center gap-1">
              Den&ge;
              <input
                type="text"
                inputMode="numeric"
                value={denMin || ""}
                placeholder="Any"
                onChange={(e) => setDenMin(Number(e.target.value.replace(/\D/g, "")) || 0)}
                className="w-14 px-1 py-0.5 rounded text-[10px] font-mono text-right outline-none"
                style={{
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text)",
                  boxShadow: "none",
                  WebkitAppearance: "none",
                }}
              />
            </label>
            <span style={{ color: "var(--color-border)" }}>|</span>
            <label className="flex items-center gap-1">
              ZHVI&ge;
              <input
                type="text"
                inputMode="numeric"
                value={hviMin ? hviMin.toLocaleString() : ""}
                placeholder="Any"
                onChange={(e) => setHviMin(Number(e.target.value.replace(/\D/g, "")) || 0)}
                className="w-16 px-1 py-0.5 rounded text-[10px] font-mono text-right outline-none"
                style={{
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text)",
                  boxShadow: "none",
                  WebkitAppearance: "none",
                }}
              />
            </label>
            <label className="flex items-center gap-1">
              ZHVI&le;
              <input
                type="text"
                inputMode="numeric"
                value={hviMax ? hviMax.toLocaleString() : ""}
                placeholder="Any"
                onChange={(e) => setHviMax(Number(e.target.value.replace(/\D/g, "")) || 0)}
                className="w-16 px-1 py-0.5 rounded text-[10px] font-mono text-right outline-none"
                style={{
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text)",
                  boxShadow: "none",
                  WebkitAppearance: "none",
                }}
              />
            </label>
          </div>

          {/* Labels toggle */}
          <button
            onClick={() => setShowLabels((v) => !v)}
            className="shrink-0 px-2 py-1.5 rounded-md text-[10px] font-medium transition-colors"
            style={{
              background: showLabels ? "var(--color-accent)" : "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: showLabels ? "#fff" : "var(--color-text-secondary)",
            }}
          >
            Labels
          </button>

          {/* Fullscreen toggle */}
          <button
            onClick={toggleFullscreen}
            className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors"
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text)",
            }}
            aria-label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? (
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M6 2v4H2M10 14v-4h4M14 2l-4 4M2 14l4-4" />
              </svg>
            ) : (
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M2 6V2h4M14 10v4h-4M2 2l4 4M14 14l-4-4" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Legend — mobile only, single line */}
      <div
        className="flex sm:hidden items-center justify-center gap-4 mt-2 text-[11px]"
        style={{ color: "var(--color-text-secondary)" }}
      >
        {mapMode === "treatment" ? (
          <>
            {[
              { color: COLORS.treated, label: year === YEAR_ALL ? "Treated" : `Treated (by ${year})` },
              { color: COLORS.control, label: "Control" },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-1.5">
                <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
                {label}
              </div>
            ))}
          </>
        ) : mapMode === "politics" ? (
          <div className="flex items-center gap-2">
            <span className="text-[9px]">D+40</span>
            <div className="h-2 rounded-sm" style={{ width: "80px", background: `linear-gradient(to right, ${polColorScale(0.3)}, ${polColorScale(0.5)}, ${polColorScale(0.7)})` }} />
            <span className="text-[9px]">R+40</span>
          </div>
        ) : mapMode === "home-values" ? (
          <div className="flex items-center gap-2">
            <span className="text-[9px]">${(hvExtent[0] / 1000).toFixed(0)}K</span>
            <div className="h-2 rounded-sm" style={{ width: "80px", background: `linear-gradient(to right, ${hvColorScale(hvExtent[0])}, ${hvColorScale(Math.sqrt(hvExtent[0] * hvExtent[1]))}, ${hvColorScale(hvExtent[1])})` }} />
            <span className="text-[9px]">${(hvExtent[1] / 1e6).toFixed(1)}M</span>
          </div>
        ) : mapMode === "population" ? (
          <div className="flex items-center gap-2">
            <span className="text-[9px]">{popExtent[0].toLocaleString()}</span>
            <div className="h-2 rounded-sm" style={{ width: "80px", background: `linear-gradient(to right, ${popColorScale(popExtent[0])}, ${popColorScale(Math.sqrt(popExtent[0] * popExtent[1]))}, ${popColorScale(popExtent[1])})` }} />
            <span className="text-[9px]">{popExtent[1].toLocaleString()}</span>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-[9px]">{Math.round(denExtent[0]).toLocaleString()}/mi²</span>
            <div className="h-2 rounded-sm" style={{ width: "80px", background: `linear-gradient(to right, ${denColorScale(denExtent[0])}, ${denColorScale(Math.sqrt(denExtent[0] * denExtent[1]))}, ${denColorScale(denExtent[1])})` }} />
            <span className="text-[9px]">{Math.round(denExtent[1]).toLocaleString()}/mi²</span>
          </div>
        )}
      </div>

      {/* Mode toggle — mobile only */}
      <div
        className="flex sm:hidden rounded-md overflow-hidden text-[11px] font-medium mt-3"
        style={{ border: "1px solid var(--color-border)" }}
      >
        {(["treatment", "population", "density", "politics", "home-values"] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setMapMode(mode)}
            className="flex-1 px-2 py-1.5 transition-colors capitalize"
            style={{
              background: mapMode === mode ? "var(--color-accent)" : "var(--color-surface)",
              color: mapMode === mode ? "#fff" : "var(--color-text-secondary)",
            }}
          >
            {mode === "home-values" ? "Values" : mode === "treatment" ? "Treated" : mode === "population" ? "Pop." : mode === "politics" ? "Politics" : mode === "density" ? "Density" : mode}
          </button>
        ))}
      </div>

      {/* Search bar — mobile only */}
      <div className="sm:hidden mt-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => { if (searchResults.length > 0) setSearchOpen(true); }}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setSearchOpen(false);
              (e.target as HTMLInputElement).blur();
            } else if (e.key === "Enter" && searchOpen && searchResults.length > 0) {
              e.preventDefault();
              zoomToZip(searchResults[searchHighlight].zip);
            }
          }}
          placeholder="Search zip, city, county..."
          className="w-full px-3 py-2 rounded-md text-[12px] outline-none"
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text)",
          }}
        />
        {searchOpen && searchResults.length > 0 && (
          <div
            className="relative mt-1 rounded-md overflow-hidden text-[12px] max-h-[200px] overflow-y-auto"
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
            }}
          >
            {searchResults.map((r, i) => (
              <button
                key={r.zip}
                onClick={() => zoomToZip(r.zip)}
                onMouseEnter={() => setSearchHighlight(i)}
                className="w-full text-left px-2.5 py-1.5 transition-colors truncate"
                style={{
                  color: "var(--color-text)",
                  background: i === searchHighlight ? "var(--color-accent)" : "transparent",
                  borderBottom: "1px solid var(--color-border)",
                }}
              >
                {r.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Filter inputs — mobile only */}
      <div
        className="flex sm:hidden items-center gap-2 mt-2 px-2 py-1.5 rounded-md text-[10px] font-mono"
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          color: "var(--color-text-secondary)",
        }}
      >
        <label className="flex items-center gap-1">
          Pop&ge;
          <input
            type="text"
            inputMode="numeric"
            value={popMin || ""}
            placeholder="Any"
            onChange={(e) => setPopMin(Number(e.target.value.replace(/\D/g, "")) || 0)}
            className="w-12 px-1 py-0.5 rounded text-[10px] font-mono text-right outline-none"
            style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          />
        </label>
        <label className="flex items-center gap-1">
          Den&ge;
          <input
            type="text"
            inputMode="numeric"
            value={denMin || ""}
            placeholder="Any"
            onChange={(e) => setDenMin(Number(e.target.value.replace(/\D/g, "")) || 0)}
            className="w-12 px-1 py-0.5 rounded text-[10px] font-mono text-right outline-none"
            style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          />
        </label>
        <span style={{ color: "var(--color-border)" }}>|</span>
        <label className="flex items-center gap-1">
          ZHVI&ge;
          <input
            type="text"
            inputMode="numeric"
            value={hviMin ? hviMin.toLocaleString() : ""}
            placeholder="Any"
            onChange={(e) => setHviMin(Number(e.target.value.replace(/\D/g, "")) || 0)}
            className="w-14 px-1 py-0.5 rounded text-[10px] font-mono text-right outline-none"
            style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          />
        </label>
        <label className="flex items-center gap-1">
          &le;
          <input
            type="text"
            inputMode="numeric"
            value={hviMax ? hviMax.toLocaleString() : ""}
            placeholder="Any"
            onChange={(e) => setHviMax(Number(e.target.value.replace(/\D/g, "")) || 0)}
            className="w-14 px-1 py-0.5 rounded text-[10px] font-mono text-right outline-none"
            style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", color: "var(--color-text)" }}
          />
        </label>
      </div>

      {/* Year selector bar */}
      <div
        className="mt-3 px-3 py-2.5 rounded-lg text-[12px] font-mono"
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          color: "var(--color-text-secondary)",
        }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsPlaying((p) => !p)}
            className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center transition-colors"
            style={{
              background: isPlaying ? "var(--color-accent)" : "transparent",
              border: `1px solid ${isPlaying ? "var(--color-accent)" : "var(--color-border)"}`,
              color: isPlaying ? "#fff" : "var(--color-text)",
            }}
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? (
              <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
                <rect x="1" y="1" width="3" height="8" rx="0.5" />
                <rect x="6" y="1" width="3" height="8" rx="0.5" />
              </svg>
            ) : (
              <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
                <path d="M2 1l7 4-7 4V1z" />
              </svg>
            )}
          </button>
          <span className="shrink-0 font-semibold" style={{ color: "var(--color-text)", minWidth: "36px" }}>
            {year === YEAR_ALL ? "All" : year}
          </span>
          <input
            type="range"
            min={0}
            max={YEAR_STEPS.length - 1}
            value={sliderIndex}
            onChange={(e) => { setIsPlaying(false); setYear(YEAR_STEPS[Number(e.target.value)]); }}
            className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer"
            style={{
              background: `linear-gradient(to right, var(--color-accent) ${(sliderIndex / (YEAR_STEPS.length - 1)) * 100}%, var(--color-border) ${(sliderIndex / (YEAR_STEPS.length - 1)) * 100}%)`,
              accentColor: "var(--color-accent)",
            }}
          />
        </div>
        <div className="flex justify-end mt-1.5 tabular-nums">
          <span style={{ color: COLORS.treated }}>{treatedCount}</span>
          <span>/{filteredTotal} treated</span>
          <span style={{ color: "var(--color-text-secondary)", margin: "0 4px" }}>·</span>
          <span style={{ color: COLORS.control }}>{controlCount}&nbsp;</span>
          <span>control</span>
        </div>
      </div>

      {/* Footnote */}
      <p
        className="mt-2 text-[10px] leading-relaxed px-1"
        style={{ color: "var(--color-text-secondary)", opacity: 0.7 }}
      >
        {year === YEAR_ALL
          ? "Showing all treatment and control zip codes in the sample (2009\u20132022). "
          : `Showing treatment zip codes reclassified from 2009\u2013${year} and their adjacent control zip codes. `}
        {year !== YEAR_ALL &&
          "In the regression, all control zips are compared against treated zips across the full panel. "}
        See{" "}
        <a
          href="#methodology"
          className="underline"
          style={{ color: "var(--color-accent)" }}
        >
          Methodology
        </a>
        {" "}for the identification strategy.
      </p>
    </div>
  );
}

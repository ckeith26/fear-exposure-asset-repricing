import Section, { SectionTitle } from "@/components/Section";

const REPO_BASE = "https://github.com/ckeith26/fear-exposure-asset-repricing/blob/main";

interface DataSource {
  name: string;
  source: string;
  url: string;
  size: string;
  acquisition: "Scripted" | "Manual";
  role: string;
  /** Path relative to repo root — links "Scripted" badge to the download script on GitHub */
  scriptPath?: string;
}

const OUTCOME_SOURCES: DataSource[] = [
  {
    name: "Zillow ZHVI (Zip)",
    source: "Zillow Research Data",
    url: "https://www.zillow.com/research/data/",
    size: "~95 MB",
    acquisition: "Manual",
    role: "Primary outcome: monthly home value index by zip code",
  },
  {
    name: "CPI-U (All Urban Consumers)",
    source: "FRED (BLS via St. Louis Fed)",
    url: "https://fred.stlouisfed.org/series/CPIAUCSL",
    size: "<1 MB",
    acquisition: "Scripted",
    scriptPath: "src/scripts/compute_summary_stats.py",
    role: "Deflates ZHVI to constant December 2022 dollars",
  },
];

const TREATMENT_SOURCES: DataSource[] = [
  {
    name: "FEMA LOMR Polygons",
    source: "FEMA NFHL ArcGIS REST API",
    url: "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/1",
    size: "~180 MB",
    acquisition: "Scripted",
    scriptPath: "src/scripts/download_FEMA.py",
    role: "Treatment events: LOMR effective dates define DiD timing",
  },
  {
    name: "NFIP Policies",
    source: "OpenFEMA Dataset",
    url: "https://www.fema.gov/openfema-data-page/fima-nfip-redacted-policies-v2",
    size: "~30 GB",
    acquisition: "Manual",
    role: "Policy intensity (treatment scaling), risk direction (upzoned/downzoned)",
  },
  {
    name: "NFIP Claims",
    source: "OpenFEMA Dataset",
    url: "https://www.fema.gov/openfema-data-page/fima-nfip-redacted-claims-v2",
    size: "~2.3 GB",
    acquisition: "Manual",
    role: "Mechanism outcome (moral hazard), falsification for physical risk channel",
  },
];

const CONTROL_SOURCES: DataSource[] = [
  {
    name: "BLS LAUS Unemployment",
    source: "Bureau of Labor Statistics",
    url: "https://www.bls.gov/lau/",
    size: "~200 MB",
    acquisition: "Scripted",
    scriptPath: "src/scripts/download_bls_laus.py",
    role: "County unemployment rate control",
  },
];

const HETEROGENEITY_SOURCES: DataSource[] = [
  {
    name: "Presidential Election Returns",
    source: "MIT Election Data + Science Lab",
    url: "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/VOQCHQ",
    size: "~75 MB",
    acquisition: "Scripted",
    scriptPath: "src/scripts/download_election_returns.py",
    role: "Climate skepticism proxy (Republican vote share interaction)",
  },
  {
    name: "State Disclosure Laws",
    source: "Verified against state statutes",
    url: "https://github.com/ckeith26/fear-exposure-asset-repricing/blob/main/data/raw/state-disclosure-laws/disclosure_laws_sources.md",
    size: "<1 KB",
    acquisition: "Manual",
    role: "Asymmetric information mechanism: 9-state disclosure indicator",
  },
];

const GEO_SOURCES: DataSource[] = [
  {
    name: "ZCTA Boundaries (TIGER/Line 2020)",
    source: "US Census Bureau",
    url: "https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.2020.html#list-tab-790442341",
    size: "~830 MB",
    acquisition: "Manual",
    role: "Zip code polygons for spatial overlay with LOMRs",
  },
  {
    name: "NOAA Coastal Counties",
    source: "NOAA Office for Coastal Management",
    url: "https://coast.noaa.gov/digitalcoast/data/coastalcounties.html",
    size: "~2 MB",
    acquisition: "Manual",
    role: "Defines universe of coastal counties for sample selection",
  },
  {
    name: "Natural Earth Ocean Polygon",
    source: "Natural Earth Data",
    url: "https://www.naturalearthdata.com/downloads/110m-physical-vectors/110m-ocean/",
    size: "~1 MB",
    acquisition: "Manual",
    role: "Removes inland watershed-only counties via spatial join",
  },
  {
    name: "US Zip Code Database",
    source: "SimpleMaps",
    url: "https://simplemaps.com/data/us-zips",
    size: "~9 MB",
    acquisition: "Manual",
    role: "Zip-to-county crosswalk, population (weights + intensity denominator)",
  },
  {
    name: "State FIPS Crosswalk",
    source: "US Census Bureau",
    url: "https://www.census.gov/library/reference/code-lists/ansi.html",
    size: "<1 KB",
    acquisition: "Manual",
    role: "State name-to-FIPS mapping for merges across datasets",
  },
];

function AcquisitionBadge({ method, scriptPath }: { method: DataSource["acquisition"]; scriptPath?: string }) {
  const styles: Record<string, { bg: string; text: string }> = {
    Scripted: { bg: "color-mix(in srgb, var(--color-accent) 15%, transparent)", text: "var(--color-accent)" },
    Manual: { bg: "color-mix(in srgb, var(--color-text-secondary) 15%, transparent)", text: "var(--color-text-secondary)" },
  };
  const s = styles[method];
  const className = "inline-block rounded px-1.5 py-0.5 text-xs font-medium";

  if (scriptPath) {
    return (
      <a
        href={`${REPO_BASE}/${scriptPath}`}
        target="_blank"
        rel="noopener noreferrer"
        className={`${className} underline decoration-dotted underline-offset-2`}
        style={{ backgroundColor: s.bg, color: s.text }}
        title={scriptPath}
      >
        {method}
      </a>
    );
  }

  return (
    <span className={className} style={{ backgroundColor: s.bg, color: s.text }}>
      {method}
    </span>
  );
}

function SourceTable({ sources, caption }: { sources: DataSource[]; caption: string }) {
  return (
    <div className="mb-10">
      <h3 className="text-lg font-semibold mb-2">{caption}</h3>
      <div
        className="rounded-lg border overflow-x-auto"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
      >
        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              {["Dataset", "Source", "Size", "Acq.", "Pipeline Role"].map((h) => (
                <th
                  key={h}
                  className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sources.map((s, i) => (
              <tr
                key={s.name}
                style={{
                  borderBottom: i < sources.length - 1 ? "1px solid var(--color-border)" : undefined,
                }}
              >
                <td className="px-4 py-3 font-medium whitespace-nowrap">{s.name}</td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline decoration-dotted underline-offset-2"
                    style={{ color: "var(--color-accent)" }}
                  >
                    {s.source}
                  </a>
                </td>
                <td
                  className="px-4 py-3 whitespace-nowrap"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {s.size}
                </td>
                <td className="px-4 py-3">
                  <AcquisitionBadge method={s.acquisition} scriptPath={s.scriptPath} />
                </td>
                <td className="px-4 py-3" style={{ color: "var(--color-text-secondary)" }}>
                  {s.role}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function DataSources() {
  return (
    <Section id="data-sources">
      <SectionTitle subtitle="External datasets feeding the estimation pipeline">
        Data Sources
      </SectionTitle>

      <p className="text-sm mb-8 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
        This study integrates 13 external data sources across outcome measurement,
        treatment construction, controls, heterogeneity analysis, and geographic
        sample definition. &ldquo;Scripted&rdquo; datasets are downloaded automatically
        via dedicated pipeline scripts; &ldquo;Manual&rdquo; datasets require one-time
        download from their provider. Full pipeline code is on{" "}
        <a
          href="https://github.com/ckeith26/fear-exposure-asset-repricing"
          target="_blank"
          rel="noopener noreferrer"
          className="underline"
          style={{ color: "var(--color-accent)" }}
        >
          GitHub
        </a>
        .
      </p>

      <SourceTable sources={OUTCOME_SOURCES} caption="Outcome" />
      <SourceTable sources={TREATMENT_SOURCES} caption="Treatment" />
      <SourceTable sources={CONTROL_SOURCES} caption="Controls" />
      <SourceTable sources={HETEROGENEITY_SOURCES} caption="Heterogeneity" />
      <SourceTable sources={GEO_SOURCES} caption="Geographic Construction" />
    </Section>
  );
}

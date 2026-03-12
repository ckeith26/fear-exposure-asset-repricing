"use client";

import Section, { SectionTitle } from "@/components/Section";
import DownloadCard from "@/components/DownloadCard";

const COEFFICIENT_FILES = [
  { name: "Main (Binary)", href: "/data/downloads/event_study_coefficients.csv" },
  { name: "Policy Intensity", href: "/data/downloads/event_study_intensity_coefficients.csv" },
  { name: "Policy Intensity Quartiles", href: "/data/downloads/event_study_intensity_quartiles_coefficients.csv" },
  { name: "Up/Down Zoned", href: "/data/downloads/event_study_updown_coefficients.csv" },
  { name: "Up/Down Decomposed", href: "/data/downloads/event_study_updown_decomposed_coefficients.csv" },
  { name: "Up/Down Intensity", href: "/data/downloads/event_study_updown_intensity_coefficients.csv" },
  { name: "Insurance Policies", href: "/data/downloads/event_study_policies_coefficients.csv" },
  { name: "Policies Up/Down", href: "/data/downloads/event_study_policies_updown_coefficients.csv" },
  { name: "Disclosure Laws", href: "/data/downloads/event_study_disclosure_coefficients.csv" },
  { name: "Republican Vote Share", href: "/data/downloads/event_study_republican_coefficients.csv" },
  { name: "SFHA Crossing", href: "/data/downloads/event_study_sfha_crossing_coefficients.csv" },
  { name: "Placebo (Unemployment)", href: "/data/downloads/s14_event_study_placebo_coefficients.csv" },
  { name: "Alt Clustering", href: "/data/downloads/s16_event_study_alt_clustering_coefficients.csv" },
];

const DATASETS = [
  {
    name: "Summary Statistics",
    description:
      "Observation counts, means, standard deviations, and percentiles for all regression variables.",
    format: "CSV",
    size: "~1 KB",
    href: "/data/downloads/summary_stats.csv",
  },
  {
    name: "Balance Table",
    description:
      "Pre-treatment covariate balance between treated and control zip codes with difference tests.",
    format: "CSV",
    size: "<1 KB",
    href: "/data/downloads/balance_table.csv",
  },
  {
    name: "LOMR Treatment Timing",
    description:
      "Zip-level treatment data: LOMR dates, number of LOMRs, treatment status, zip characteristics.",
    format: "CSV",
    size: "~870 KB",
    href: "/data/downloads/lomr_treatment_timing.csv",
  },
  {
    name: "Stata Do-File",
    description:
      "Complete event study estimation script with all specifications, tables, and figures.",
    format: "DO",
    size: "~82 KB",
    href: "/data/downloads/event_study.do",
  },
  {
    name: "Leave-One-Out State Results",
    description:
      "\u03c4 = +4 coefficient and 95% CI when each state is excluded from the sample.",
    format: "CSV",
    size: "<1 KB",
    href: "/data/downloads/s15_leave_one_out_state.csv",
  },
  {
    name: "Disclosure Law Sources",
    description:
      "Statutory citations and verification for the 9 states classified as having mandatory flood zone disclosure during the study period.",
    format: "MD",
    size: "<5 KB",
    href: "https://github.com/ckeith26/fear-exposure-asset-repricing/blob/main/data/raw/state-disclosure-laws/disclosure_laws_sources.md",
    external: true,
  },
  {
    name: "Regression Panel",
    description:
      "Full zip × quarter panel with ZHVI, treatment indicators, NFIP policies/claims, and BLS unemployment. Generate via the data pipeline on GitHub.",
    format: "CSV",
    size: "~151 MB",
    href: "https://github.com/ckeith26/fear-exposure-asset-repricing",
    external: true,
  },
  {
    name: "NFIP Policy Panel",
    description:
      "Zip × month NFIP policy counts, premiums, claims, and SFHA shares. 997K rows. Generate via the data pipeline on GitHub.",
    format: "CSV",
    size: "~112 MB",
    href: "https://github.com/ckeith26/fear-exposure-asset-repricing",
    external: true,
  },
];

export default function DataDownload() {
  return (
    <Section id="data-download">
      <SectionTitle subtitle="Download research data and replication files">
        Data
      </SectionTitle>

      <p className="text-sm mb-8 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
        All datasets used in this research are available for download. Data is
        provided as-is for replication and academic use. The source code for the
        full data pipeline is available on{" "}
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

      {/* Event Study Coefficients */}
      <div className="mb-10">
        <h3 className="text-lg font-semibold mb-2">Event Study Coefficients</h3>
        <p className="text-sm mb-4 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
          Point estimates, standard errors, and 95% confidence intervals for each event-time
          coefficient across all specifications.
        </p>
        <div
          className="rounded-lg border p-4"
          style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
        >
          <div className="flex flex-wrap gap-2">
            {COEFFICIENT_FILES.map((f) => (
              <a
                key={f.name}
                href={f.href}
                download
                className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors duration-150"
                style={{
                  color: "var(--color-accent)",
                  borderColor: "var(--color-border)",
                  background: "transparent",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--color-accent)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--color-border)";
                }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                {f.name}
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* Other Datasets */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {DATASETS.map((ds) => (
          <DownloadCard key={ds.name} {...ds} />
        ))}
      </div>
    </Section>
  );
}

"use client";

import Section, { SectionTitle } from "@/components/Section";

export default function About() {
  return (
    <Section id="about">
      <SectionTitle subtitle="Author and acknowledgments">About</SectionTitle>

      <div className="grid md:grid-cols-2 gap-12">
        {/* Author */}
        <div>
          <h3 className="text-lg font-semibold mb-4">Author</h3>
          <div
            className="rounded-lg p-6"
            style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
          >
            <div className="text-xl font-semibold mb-1">Cameron Keith</div>
            <div className="text-sm mb-4" style={{ color: "var(--color-text-secondary)" }}>
              Econ 66 &middot; Dartmouth College
            </div>
            <div className="space-y-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
              <p>
                This research was conducted as part of the Economics 66 course.
                The full paper, data pipeline, and replication code are available
                on GitHub.
              </p>
            </div>
            <div className="mt-4 flex gap-3">
              <a
                href="https://github.com/ckeith26/fear-exposure-asset-repricing"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-md transition-colors"
                style={{
                  color: "var(--color-accent)",
                  border: "1px solid var(--color-accent)",
                }}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
                </svg>
                Repository
              </a>
            </div>
          </div>
        </div>

        {/* Methodology note */}
        <div>
          <h3 className="text-lg font-semibold mb-4">Methodology Note</h3>
          <div
            className="rounded-lg p-6 text-sm space-y-3"
            style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", color: "var(--color-text-secondary)" }}
          >
            <p>
              <strong style={{ color: "var(--color-text)" }}>Data pipeline:</strong>{" "}
              Python (pandas, geopandas) for data acquisition, spatial
              operations, and panel construction. All scripts are reproducible
              from raw inputs.
            </p>
            <p>
              <strong style={{ color: "var(--color-text)" }}>Econometrics:</strong>{" "}
              Stata (reghdfe) for high-dimensional fixed effects estimation.
              Callaway &amp; Sant&apos;Anna estimator via the csdid package.
            </p>
            <p>
              <strong style={{ color: "var(--color-text)" }}>This website:</strong>{" "}
              Next.js (static export), D3.js for charts, Tailwind CSS. Deployed
              on AWS S3 + CloudFront.
            </p>
            <p>
              <strong style={{ color: "var(--color-text)" }}>Data sources:</strong>{" "}
              FEMA NFHL (ArcGIS REST), NFIP policies and claims, Zillow ZHVI,
              BLS LAUS, Census TIGER/Line, MIT Election Lab, FRED CPI-U,
              NOAA coastal counties, state flood disclosure laws.
            </p>
          </div>
        </div>
      </div>
    </Section>
  );
}

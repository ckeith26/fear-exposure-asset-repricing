"use client";

import { useEffect, useRef, useState } from "react";
import Section, { SectionTitle } from "@/components/Section";
import EquationBlock from "@/components/EquationBlock";

function Expandable({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (contentRef.current) {
      setHeight(contentRef.current.scrollHeight);
    }
  }, [open, children]);

  return (
    <div
      className="rounded-lg mb-3 overflow-hidden"
      style={{ border: "1px solid var(--color-border)" }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium text-left transition-colors"
        style={{ background: "var(--color-surface)" }}
      >
        {title}
        <span
          className="transition-transform duration-300 ml-4"
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        >
          &#9662;
        </span>
      </button>
      <div
        style={{
          maxHeight: open ? `${height}px` : "0px",
          overflow: "hidden",
          transition: "max-height 0.3s ease",
        }}
      >
        <div
          ref={contentRef}
          className="px-5 py-4 text-sm leading-relaxed"
          style={{ color: "var(--color-text-secondary)", borderTop: "1px solid var(--color-border)" }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}

export default function Methodology() {
  return (
    <Section id="methodology">
      <SectionTitle subtitle="Identification strategy and econometric specification">
        Methodology
      </SectionTitle>

      <div className="max-w-3xl mx-auto">
        {/* Core design */}
        <div className="space-y-5 text-[15px] leading-relaxed mb-10" style={{ color: "var(--color-text-secondary)" }}>
          <p>
            This paper uses a{" "}
            <strong style={{ color: "var(--color-text)" }}>
              staggered difference-in-differences
            </strong>{" "}
            design that exploits variation in the timing of LOMR effective dates
            across zip codes. The key assumption is that, absent the LOMR, home
            values in treated and control zips would have followed parallel
            trends, which is testable in the pre-treatment period.
          </p>
          <p>
            The event study specification estimates dynamic treatment effects at
            each year relative to the LOMR:
          </p>
        </div>

        {/* Main equation */}
        <EquationBlock
          latex={String.raw`\ln(\text{Real ZHVI}_{z,t}) = \alpha_z + \delta_{c(z),\,y(t)} + \sum_{\tau \neq -1} \beta_\tau \cdot \mathbf{1}[t - E_z = \tau] + \gamma \mathbf{X}_{z,t} + \varepsilon_{z,t}`}
        />

        <div className="space-y-5 text-[15px] leading-relaxed mb-10" style={{ color: "var(--color-text-secondary)" }}>
          <p>
            where <em>z</em> indexes zip codes, <em>t</em> indexes
            quarters, <em>c(z)</em> maps zip to county, <em>y(t)</em> maps
            quarter to calendar year, and <em>E<sub>z</sub></em> is the LOMR effective date for
            treated zip <em>z</em>. The coefficients of interest are the{" "}
            <strong style={{ color: "var(--color-text)" }}>
              &beta;<sub>&tau;</sub>
            </strong>
            , which trace out the treatment effect at each event-time bin
            relative to the omitted reference period (&tau; = &minus;1, the year
            before the LOMR).
          </p>
        </div>

        {/* Expandable details */}
        <div className="mt-10">
          <Expandable title="Fixed Effects Structure">
            <p className="mb-3">
              <strong style={{ color: "var(--color-text)" }}>Zip fixed effects (&alpha;<sub>z</sub>)</strong>{" "}
              absorb all time-invariant characteristics of each zip code:
              location, geography, housing stock composition, neighborhood
              amenities, and baseline flood risk.
            </p>
            <p>
              <strong style={{ color: "var(--color-text)" }}>County &times; year fixed effects (&delta;<sub>c(z),y(t)</sub>)</strong>{" "}
              absorb county-level annual housing market cycles, local economic
              conditions, and county-wide policy changes. This is more demanding
              than simple calendar-time FE because it controls for any
              county-year-specific shock that might correlate with both LOMR
              timing and home values.
            </p>
          </Expandable>

          <Expandable title="Control Variables">
            <p className="mb-3">
              <strong style={{ color: "var(--color-text)" }}>County unemployment rate</strong>{" "}
              from the BLS Local Area Unemployment Statistics captures
              time-varying local economic conditions.
            </p>
            <p className="mb-3">
              <strong style={{ color: "var(--color-text)" }}>NFIP policy count</strong>{" "}
              measures flood insurance take-up in the zip, controlling for
              insurance market activity that may independently affect home
              values.
            </p>
          </Expandable>

          <Expandable title="Standard Errors and Weighting">
            <p className="mb-3">
              Standard errors are{" "}
              <strong style={{ color: "var(--color-text)" }}>
                clustered at the county level
              </strong>{" "}
              to account for spatial correlation in housing markets and LOMR
              assignments within counties. Regressions are weighted by zip code
              population to make estimates representative of the affected
              population.
            </p>
          </Expandable>

          <Expandable title="What are LOMRs?">
            <p className="mb-3">
              A <strong style={{ color: "var(--color-text)" }}>Letter of Map Revision (LOMR)</strong>{" "}
              is an official FEMA document that formally changes the flood zone
              designation for a specific area. When FEMA issues a LOMR, it
              officially updates the flood risk information for affected
              properties. Our main specification includes all effective LOMRs as
              informational shocks to flood risk designation, not just those
              that cross the SFHA boundary.
            </p>
            <p className="mb-3">
              Some LOMRs move properties into or out of Special Flood Hazard
              Areas (SFHAs), which triggers or removes a mandatory flood
              insurance purchase requirement for federally backed mortgages.
              These SFHA-crossing LOMRs are examined separately to test whether
              the insurance mandate or informational updating drives repricing.
            </p>
            <p>
              Roughly 34% of treated zip codes have &ldquo;stable&rdquo; LOMRs
              that update base flood elevations or sub-zone classifications
              without moving the SFHA boundary. Including them in the main
              specification captures the broad informational channel of flood
              map revisions.
            </p>
          </Expandable>
        </div>
      </div>
    </Section>
  );
}

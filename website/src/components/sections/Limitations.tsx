import Section, { SectionTitle } from "@/components/Section";

const IDENTIFICATION_LIMITS = [
  {
    title: "LOMR endogeneity",
    desc: "LOMRs aren\u2019t randomly assigned; FEMA prioritizes areas with recent flood events or development pressure, so reclassification timing may correlate with omitted local shocks.",
  },
  {
    title: "ZCTA boundary vintage",
    desc: "2020 Census ZCTA boundaries applied to a 2009\u20132022 panel. Some boundaries shifted between the 2010 and 2020 censuses, potentially misattributing spatial treatment.",
  },
  {
    title: "County-level clustering",
    desc: "Standard errors clustered at the county level, but treatment varies at the zip level. State-level clustering (shown in Robustness) produces wider confidence intervals.",
  },
];

const DATA_LIMITS = [
  {
    title: "Climate skepticism proxy",
    desc: "Republican vote share is a county-level, coarse proxy for individual climate beliefs.",
  },
  {
    title: "Disclosure law indicator",
    desc: "Binary, time-invariant, and limited to 9 states. Variation is purely cross-state.",
  },
  {
    title: "NFIP data quality",
    desc: "reportedCity is 100% unavailable; lat/lng has only 1-decimal precision (~11 km); elevation fields contain sentinel values.",
  },
];

function LimitCard({ title, desc }: { title: string; desc: string }) {
  return (
    <div
      className="rounded-lg p-4"
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
      }}
    >
      <p className="font-semibold text-sm mb-1">{title}</p>
      <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
        {desc}
      </p>
    </div>
  );
}

export default function Limitations() {
  return (
    <Section id="limitations">
      <SectionTitle subtitle="Threats to identification and data quality caveats">
        Limitations
      </SectionTitle>

      <div className="space-y-12">
        <div>
          <h3 className="text-lg font-semibold mb-4">
            Identification &amp; Design
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {IDENTIFICATION_LIMITS.map((l) => (
              <LimitCard key={l.title} {...l} />
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold mb-4">
            Data &amp; Proxy Quality
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {DATA_LIMITS.map((l) => (
              <LimitCard key={l.title} {...l} />
            ))}
          </div>
        </div>
      </div>
    </Section>
  );
}

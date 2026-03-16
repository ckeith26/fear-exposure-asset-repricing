"use client";

import Section, { SectionTitle } from "@/components/Section";
import StatTable from "@/components/StatTable";
import { summaryStats, balanceTable } from "@/lib/data";

export default function DataSample() {
  return (
    <Section id="data-sample">
      <SectionTitle subtitle="Sample construction and descriptive statistics">
        Data &amp; Sample
      </SectionTitle>

      {/* Methodology summary */}
      <div
        className="rounded-lg p-6 mb-12 text-sm leading-relaxed"
        style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
      >
        <p style={{ color: "var(--color-text-secondary)" }}>
          The sample consists of all US coastal zip codes (excluding Alaska,
          Hawaii, and territories) observed quarterly from 2009 to 2022.{" "}
          <strong style={{ color: "var(--color-text)" }}>Treatment zips</strong>{" "}
          are those that received their first (and only) LOMR within the
          2009 to 2022 window. ZIP codes with pre-2009 treatment or multiple
          LOMRs are excluded to ensure clean identification.{" "}
          <strong style={{ color: "var(--color-text)" }}>Control zips</strong>{" "}
          consist of never-treated ZIP codes (no LOMR ever) and not-yet-treated
          ZIP codes (first LOMR after the sample window).
        </p>
      </div>

      {/* Summary Statistics */}
      <div className="mb-16">
        <h3 className="text-lg font-semibold mb-6">Summary Statistics</h3>
        <StatTable type="summary" data={summaryStats} title={summaryStats.title} />
      </div>

      {/* Balance Table */}
      <div>
        <h3 className="text-lg font-semibold mb-2">Pre-Treatment Balance</h3>
        <p className="text-sm mb-6" style={{ color: "var(--color-text-secondary)" }}>
          Comparing pre-LOMR means for treated zips against all-period means
          for control zips. Significance: * p&lt;0.10, ** p&lt;0.05, *** p&lt;0.01 (Welch t-test).
        </p>
        <StatTable type="balance" data={balanceTable} title="Balance Table: Pre-Treatment Characteristics" />
      </div>
    </Section>
  );
}

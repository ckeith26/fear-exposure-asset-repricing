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
          The sample consists of all US coastal zip codes (excluding Alaska and
          territories) observed quarterly from 2009 to 2022.{" "}
          <strong style={{ color: "var(--color-text)" }}>Treatment zips</strong>{" "}
          are those whose ZCTA boundary intersects the ocean and received at
          least one LOMR during the analysis window.{" "}
          <strong style={{ color: "var(--color-text)" }}>Control zips</strong>{" "}
          are adjacent coastal zips that share a boundary with treatment zips but
          never received a LOMR. Zips treated before 2009 and those with
          multiple LOMRs are excluded from the event study to ensure clean
          identification.
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

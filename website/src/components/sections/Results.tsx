"use client";

import { useState } from "react";
import Section, { SectionTitle } from "@/components/Section";
import EquationBlock from "@/components/EquationBlock";
import EventStudyChart from "@/components/EventStudyChart";
import RegressionTable from "@/components/RegressionTable";
import {
  eventStudyMain,
  eventStudyIntensity,
  eventStudySignedIntensity,
  eventStudyIntensityQuartiles,
  regressionTables,
} from "@/lib/data";
import updownDecomposedJson from "../../../public/data/event_study_updown_decomposed.json";
import disclosureJson from "../../../public/data/event_study_disclosure.json";
import republicanJson from "../../../public/data/event_study_republican.json";
import sfhaCrossingJson from "../../../public/data/event_study_sfha_crossing.json";
import type { EventStudyData, EventStudyPoint } from "@/types";

// Parse two-series data - format: { series: [{label, points}] }
interface TwoSeriesData {
  title: string;
  y_label: string;
  reference_tau: number;
  series: Array<{
    label: string;
    points: Array<{ tau: number; coef: number; ci_lo: number; ci_hi: number }>;
  }>;
}
const updownDecomposedData = updownDecomposedJson as TwoSeriesData;
const disclosureData = disclosureJson as TwoSeriesData;
const republicanData = republicanJson as TwoSeriesData;
const sfhaCrossingData = sfhaCrossingJson as EventStudyData;

function addSE(
  pts: Array<{ tau: number; coef: number; ci_lo: number; ci_hi: number }>
): EventStudyPoint[] {
  return pts.map((p) => ({
    ...p,
    se: p.coef === 0 ? 0 : (p.ci_hi - p.ci_lo) / (2 * 1.96),
  }));
}

const TABS = [
  { key: "main", label: "Main Event Study" },
  { key: "intensity", label: "Policy Intensity" },
  { key: "quartiles", label: "Policy Intensity Quartiles" },
  { key: "updown", label: "Up vs. Down" },
  { key: "disclosure", label: "Disclosure Laws" },
  { key: "republican", label: "Political Lean" },
  { key: "sfha_crossing", label: "SFHA Crossing" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function TabContent({ tabKey }: { tabKey: TabKey }) {
  switch (tabKey) {
    case "main":
      return (
        <div>
          <p className="text-sm mb-8 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            The main event study shows the effect of LOMR flood zone
            reclassification on log real home values (Real ZHVI, adjusted to December
            2022 dollars). Pre-treatment coefficients near zero confirm the
            parallel trends assumption. Post-treatment, home values decline
            gradually, reaching <strong style={{ color: "var(--color-negative)" }}>
            &minus;2.8%</strong> after four or more years.
          </p>
          <EquationBlock
            compact
            latex={String.raw`\ln(\text{Real ZHVI}_{z,t}) = \alpha_z + \delta_{c(z),\,y(t)} + \sum_{\tau \neq -1} \beta_\tau \cdot \mathbf{1}[t - E_z = \tau] + \gamma' \mathbf{X}_{z,t} + \varepsilon_{z,t}`}
            labels={[
              { symbol: "\\alpha_z", description: "zip fixed effects" },
              { symbol: "\\delta_{c(z),\,y(t)}", description: "county\u00D7year FE" },
              { symbol: "\\beta_\\tau", description: "event-time coefficients" },
              { symbol: "E_z", description: "LOMR effective date" },
              { symbol: "\\mathbf{X}", description: "unemployment rate, NFIP policy count" },
            ]}
          />
          <EventStudyChart {...eventStudyMain} />
          <div className="mt-12">
            <RegressionTable data={regressionTables.main} />
          </div>
        </div>
      );

    case "intensity":
      return (
        <div>
          <p className="text-sm mb-8 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            The intensity specification replaces binary event-time dummies with
            dummies scaled by pre-LOMR NFIP policy penetration (policies /
            population), which is a proxy for the share of the zip&apos;s housing stock in the
            flood zone. The effect is significant from &tau;=+1 onward (though &tau;=+2
            only at 10%), with coefficients growing monotonically to <strong style={{ color: "var(--color-negative)" }}>
            &minus;7.15</strong> at &tau;=+4.
          </p>
          <EquationBlock
            compact
            latex={String.raw`\ln(\text{Real ZHVI}_{z,t}) = \alpha_z + \delta_{c(z),\,y(t)} + \sum_{\tau \neq -1} \beta_\tau \cdot \mathbf{1}[t - E_z = \tau] \times \underbrace{\frac{\overline{\text{Policies}}_z^{\,\text{pre}}}{\text{Pop}_z}}_{\text{Intensity}_z} + \gamma' \mathbf{X}_{z,t} + \varepsilon_{z,t}`}
            labels={[
              { symbol: "\\text{Intensity}_z", description: "pre-LOMR NFIP policies / zip population" },
              { symbol: "\\beta_\\tau", description: "effect at full policy penetration" },
              { symbol: "\\mathbf{X}", description: "county unemployment rate" },
            ]}
          />
          <EventStudyChart {...eventStudyIntensity} />
          <div className="mt-12">
            <RegressionTable data={regressionTables.intensity} />
          </div>
        </div>
      );

    case "quartiles":
      return (
        <div>
          <p className="text-sm mb-8 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            A non-parametric dose-response test: instead of a single linear
            intensity measure, treated zips are split into quartiles of
            pre-LOMR NFIP policy penetration. Q1 (lowest penetration)
            shows near-zero effects throughout. Among higher-penetration
            quartiles, Q2 exhibits the earliest and most precisely estimated
            declines (<strong style={{ color: "var(--color-negative)" }}>&minus;3.0%**</strong> at
            &tau;=+2), while Q4 shows the largest eventual decline
            (<strong style={{ color: "var(--color-negative)" }}>&minus;5.7%</strong> at &tau;=+4).
            The non-monotonic pattern suggests insurance exposure is necessary
            for repricing, but the relationship is not strictly linear across
            quartiles.
          </p>
          <EquationBlock
            compact
            latex={String.raw`\ln(\text{Real ZHVI}_{z,t}) = \alpha_z + \delta_{c(z),\,y(t)} + \sum_{q=1}^{4} \sum_{\tau \neq -1} \beta_{\tau}^{(q)} \cdot \mathbf{1}[t - E_z = \tau] \times \mathbf{1}[Q_z = q] + \gamma' \mathbf{X}_{z,t} + \varepsilon_{z,t}`}
            labels={[
              { symbol: "Q_z \\in \\{1,2,3,4\\}", description: "quartile of pre-LOMR policy penetration (policies / population)" },
              { symbol: "\\beta_{\\tau}^{(q)}", description: "quartile-specific effect at event time τ" },
              { symbol: "\\mathbf{X}", description: "county unemployment rate" },
            ]}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {eventStudyIntensityQuartiles.series.map((series) => (
              <EventStudyChart
                key={series.label}
                title={series.label}
                y_label={eventStudyIntensityQuartiles.y_label}
                reference_tau={eventStudyIntensityQuartiles.reference_tau}
                points={addSE(series.points)}
                seriesColors={[series.color, series.color]}
              />
            ))}
          </div>
          <div className="mt-12">
            <RegressionTable data={regressionTables.intensity_quartiles} />
          </div>
        </div>
      );

    case "updown": {
      const upSeries = updownDecomposedData.series[0];
      const downSeries = updownDecomposedData.series[1];
      const upPoints = addSE(upSeries.points);
      const downPoints = addSE(downSeries.points);
      return (
        <div>
          <p className="text-sm mb-8 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            Not all LOMRs are equivalent. Those that cross the SFHA boundary
            impose or remove a mandatory flood insurance requirement for
            federally backed mortgages, creating a direct cost channel. Home
            values should{" "}
            <strong style={{ color: "var(--color-negative)" }}>fall</strong> in{" "}
            <strong style={{ color: "var(--color-negative)" }}>upzoned</strong>{" "}
            areas (mapped into the SFHA, imposing new insurance costs) and{" "}
            <strong style={{ color: "var(--color-accent)" }}>rise</strong> in{" "}
            <strong style={{ color: "var(--color-accent)" }}>downzoned</strong>{" "}
            areas (mapped out, eliminating the mandate). The upzoned
            coefficients trend negative, reaching{" "}
            <strong style={{ color: "var(--color-negative)" }}>&minus;2.2</strong>{" "}
            at &tau;=+3, while downzoned coefficients are positive at shorter
            horizons. This decomposition tests whether the mandatory purchase
            requirement drives repricing, or whether informational updating
            alone is sufficient.
          </p>
          <EquationBlock
            compact
            latex={String.raw`\ln(\text{Real ZHVI}_{z,t}) = \alpha_z + \delta_{c(z),\,y(t)} + \sum_{\tau \neq -1} \beta_\tau^{\text{up}} \, \text{ibin}_\tau \times \mathbb{1}\{\text{Up}_z\} + \sum_{\tau \neq -1} \beta_\tau^{\text{down}} \, \text{ibin}_\tau \times \mathbb{1}\{\text{Down}_z\} + \gamma' \mathbf{X}_{z,t} + \varepsilon_{z,t}`}
            labels={[
              { symbol: "\\text{ibin}_\\tau", description: "event-time dummy \u00D7 policy intensity" },
              { symbol: "\\beta_\\tau^{\\text{up}}", description: "effect in upzoned areas (risk \u2191)" },
              { symbol: "\\beta_\\tau^{\\text{down}}", description: "effect in downzoned areas (risk \u2193)" },
              { symbol: "\\mathbb{1}\\{\\text{Up}_z\\}, \\mathbb{1}\\{\\text{Down}_z\\}", description: "= 1 if zip upzoned / downzoned (SFHA share change)" },
            ]}
          />
          <EventStudyChart
            title={updownDecomposedData.title}
            y_label={updownDecomposedData.y_label}
            reference_tau={updownDecomposedData.reference_tau}
            points={upPoints}
            secondSeries={downPoints}
            seriesLabels={["Upzoned (risk \u2191)", "Downzoned (risk \u2193)"]}
            seriesColors={["var(--color-negative)", "var(--color-accent)"]}
          />
          <div className="mt-12">
            <RegressionTable data={regressionTables.updown_intensity} />
          </div>
        </div>
      );
    }

    case "disclosure": {
      const discSeries = disclosureData.series[0];
      const nodiscSeries = disclosureData.series[1];
      const discPoints = addSE(discSeries.points);
      const nodiscPoints = addSE(nodiscSeries.points);
      return (
        <div>
          <p className="text-sm mb-8 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            Testing whether mandatory flood disclosure laws amplify the LOMR effect.
            The binary LOMR event dummies are interacted with a disclosure indicator.
            The chart below uses the strict 9-state definition; the regression table
            also reports a broad 13-state definition (adding FL, VA, NC, NY).
            The interaction terms are directionally consistent with
            disclosure attenuating the price decline, but do not reach statistical significance.
          </p>
          <EquationBlock
            compact
            latex={String.raw`\ln(\text{Real ZHVI}_{z,t}) = \alpha_z + \delta_{c(z),\,y(t)} + \sum_{\tau \neq -1} \beta_\tau \, \text{ebin}_{\tau} + \sum_{\tau \neq -1} \gamma_\tau \, \text{ebin}_{\tau} \times \mathbb{1}\{\text{Disc}_s\} + \delta' \mathbf{X}_{z,t} + \varepsilon_{z,t}`}
            labels={[
              { symbol: "\\text{ebin}_\\tau", description: "binary event-time dummy" },
              { symbol: "\\beta_\\tau", description: "baseline LOMR effect (non-disclosure)" },
              { symbol: "\\gamma_\\tau", description: "additional effect in disclosure states" },
              { symbol: "\\mathbb{1}\\{\\text{Disc}_s\\}", description: "= 1 if state has mandatory flood disclosure" },
            ]}
          />
          <EventStudyChart
            title={disclosureData.title}
            y_label={disclosureData.y_label}
            reference_tau={disclosureData.reference_tau}
            points={discPoints}
            secondSeries={nodiscPoints}
            seriesLabels={["Disclosure states (\u03b2+\u03b3)", "Non-disclosure states (\u03b2)"]}
            seriesColors={["var(--color-negative)", "var(--color-accent)"]}
          />
          <p className="text-xs mt-3 max-w-3xl" style={{ color: "var(--color-text-muted)" }}>
            <strong>Strict disclosure</strong> (9 states): CA, IL, IN, LA, MS, OR, SC, TX, WI &mdash;
            mandatory seller disclosure of flood zone designation.{" "}
            <strong>Broad disclosure</strong> (13 states) adds FL (common-law duty via <em>Johnson v. Davis</em>),
            VA (Residential Property Disclosure Act), NC (disclosure statement floodplain question),
            and NY (attorney-standard flood zone due diligence).
            Chart shows strict definition; regression table reports both.
          </p>
          <div className="mt-12">
            <RegressionTable data={regressionTables.disclosure} />
          </div>
        </div>
      );
    }

    case "republican": {
      const repSeries = republicanData.series[0];
      const demSeries = republicanData.series[1];
      const repPoints = addSE(repSeries.points);
      const demPoints = addSE(demSeries.points);
      return (
        <div>
          <p className="text-sm mb-8 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            Splitting the intensity specification by county political lean reveals a stark
            differential. In{" "}
            <strong style={{ color: "var(--color-accent)" }}>Democratic-leaning</strong>{" "}
            counties (2020 presidential vote), the intensity-weighted effect is large and
            highly significant, reaching{" "}
            <strong style={{ color: "var(--color-negative)" }}>&minus;12.7</strong> at
            &tau;=+4. In{" "}
            <strong style={{ color: "var(--color-negative)" }}>Republican-leaning</strong>{" "}
            counties, the effect is near zero across all post-treatment horizons. This is
            consistent with political ideology shaping how residents interpret flood risk
            information. Communities more skeptical of government risk assessments
            may discount FEMA reclassifications.
          </p>
          <EquationBlock
            compact
            latex={String.raw`\ln(\text{Real ZHVI}_{z,t}) = \alpha_z + \delta_{c(z),\,y(t)} + \sum_{\tau \neq -1} \beta_\tau \, \text{ibin}_{\tau} + \sum_{\tau \neq -1} \gamma_\tau \, \text{ibin}_{\tau} \times \mathbb{1}\{\text{Rep}_c\} + \delta' \mathbf{X}_{z,t} + \varepsilon_{z,t}`}
            labels={[
              { symbol: "\\text{ibin}_\\tau", description: "event-time dummy \u00D7 policy intensity" },
              { symbol: "\\beta_\\tau", description: "baseline intensity effect (Dem-leaning)" },
              { symbol: "\\gamma_\\tau", description: "differential effect in GOP-leaning counties" },
              { symbol: "\\mathbb{1}\\{\\text{Rep}_c\\}", description: "= 1 if county above-median R two-party share" },
            ]}
          />
          <EventStudyChart
            title={republicanData.title}
            y_label={republicanData.y_label}
            reference_tau={republicanData.reference_tau}
            points={repPoints}
            secondSeries={demPoints}
            seriesLabels={["Republican counties", "Democratic counties"]}
            seriesColors={["var(--color-negative)", "var(--color-accent)"]}
          />
          <div className="mt-12">
            <RegressionTable data={regressionTables.republican} />
          </div>
        </div>
      );
    }

    case "sfha_crossing":
      return (
        <div>
          <p className="text-sm mb-8 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            The main specification includes all effective LOMRs — both those
            that cross the SFHA boundary and &ldquo;stable&rdquo; LOMRs that
            update base flood elevations without changing insurance mandates.
            Here we restrict to SFHA-crossing LOMRs only, dropping the ~34% of
            treated zips with stable LOMRs. If the mandatory insurance channel
            drives capitalization, this restriction should sharpen the effect;
            if informational updating is the primary channel, results should
            resemble the full-sample estimate.
          </p>
          <EquationBlock
            compact
            latex={String.raw`\ln(\text{Real ZHVI}_{z,t}) = \alpha_z + \delta_{c(z),\,y(t)} + \sum_{\tau \neq -1} \beta_\tau \cdot \mathbf{1}[t - E_z = \tau] + \gamma' \mathbf{X}_{z,t} + \varepsilon_{z,t} \qquad \text{sample: SFHA-crossing LOMRs only}`}
            labels={[
              { symbol: "\\text{SFHA-crossing}", description: "LOMR shifts SFHA boundary (up or down, excludes stable BFE updates)" },
              { symbol: "\\beta_\\tau", description: "event-time coefficients for SFHA-crossing subsample" },
            ]}
          />
          <EventStudyChart {...sfhaCrossingData} />
        </div>
      );

  }
}

export default function Results() {
  const [activeTab, setActiveTab] = useState<TabKey>("main");

  return (
    <Section id="results">
      <SectionTitle subtitle="Event study estimates and regression tables">
        Results
      </SectionTitle>

      {/* Tabs */}
      <div
        className="flex gap-1 mb-10 overflow-x-auto pb-1"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors -mb-px ${
              activeTab === tab.key ? "tab-active" : ""
            }`}
            style={{
              color:
                activeTab === tab.key
                  ? "var(--color-accent)"
                  : "var(--color-text-secondary)",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <TabContent tabKey={activeTab} />
    </Section>
  );
}

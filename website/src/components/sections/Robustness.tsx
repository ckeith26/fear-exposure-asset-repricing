"use client";

import Image from "next/image";
import dynamic from "next/dynamic";
import Section, { SectionTitle } from "@/components/Section";
import EventStudyChart from "@/components/EventStudyChart";
import LeaveOneOutChart from "@/components/LeaveOneOutChart";
import RegressionTable from "@/components/RegressionTable";
import {
  regressionTables,
  eventStudyMainUrban,
  eventStudyIntensityUrban,
  eventStudyPlacebo,
  leaveOneOutState,
} from "@/lib/data";
import altClusteringJson from "../../../public/data/event_study_alt_clustering.json";
import trendsJson from "../../../public/data/home_value_trends.json";
import timingJson from "../../../public/data/treatment_timing.json";
import csJson from "../../../public/data/event_study_cs.json";
import type { MultiSeriesData, EventStudyPoint } from "@/types";

const TrendsChart = dynamic(() => import("@/components/TrendsChart"), { ssr: false });
const BarChart = dynamic(() => import("@/components/BarChart"), { ssr: false });

const altClusteringData = altClusteringJson as MultiSeriesData;

// Build C&S event study points from JSON (combining pre + post series into one)
const csPoints: EventStudyPoint[] = [
  ...csJson.series[0].points,
  ...csJson.series[1].points,
].map(p => ({
  ...p,
  se: p.coef === 0 ? 0 : (p.ci_hi - p.ci_lo) / (2 * 1.96),
}));

export default function Robustness() {
  return (
    <Section id="robustness">
      <SectionTitle subtitle="Diagnostics, parallel trends, and heterogeneity-robust estimation">
        Robustness
      </SectionTitle>

      <div className="space-y-16">
        {/* Parallel Trends */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Parallel Pre-Trends
          </h3>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            The identifying assumption requires that treated and control zip codes
            would have followed parallel home value trajectories absent the LOMR.
            The raw trends below show treated zips are higher in levels (coastal
            proximity), but the year-over-year movements track closely. This is
            consistent with the parallel trends assumption that the zip and
            county&times;year fixed effects absorb.
          </p>
          <TrendsChart {...trendsJson} />
        </div>

        {/* Pre-Period Joint F-Test */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Pre-Period Joint F-Test
          </h3>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            A formal joint test of whether all pre-treatment coefficients
            (&tau; = &minus;4, &minus;3, &minus;2) are simultaneously zero. Failure
            to reject supports the parallel trends assumption required for causal
            identification.
          </p>
          <div
            className="rounded-lg p-6 text-center"
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            <p className="font-mono text-2xl font-bold mb-2" style={{ color: "var(--color-accent)" }}>
              F(3, 338) = 1.04 &nbsp;&nbsp; p = 0.373
            </p>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
              Cannot reject the null that all pre-treatment coefficients jointly
              equal zero. This supports the parallel trends assumption.
            </p>
          </div>
        </div>

        {/* Treatment Timing */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Treatment Timing Distribution
          </h3>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            The staggered treatment design relies on variation in LOMR effective
            dates across zip codes. Treatment is spread across the full 2009&ndash;2022
            window, with increasing frequency in later years as FEMA&apos;s mapping
            modernization program accelerated. This variation identifies the
            event-time coefficients.
          </p>
          <BarChart {...timingJson} />
        </div>

        {/* TWFE DiD */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Two-Way Fixed Effects DiD
          </h3>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            A simple TWFE DiD with a binary post-treatment indicator estimates
            the average treatment effect. The coefficient is negative but
            imprecisely estimated, consistent with the event study showing
            effects that build gradually over time. A single-period pooled
            estimate averages early (near-zero) and late (large negative)
            effects, yielding a small, insignificant average.
          </p>
          <RegressionTable data={regressionTables.twfe} />
        </div>

        {/* Unweighted & Geographic Intensity */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Unweighted &amp; Geographic Intensity
          </h3>
          <p className="text-sm mb-4 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            <strong>Unweighted specification:</strong> Dropping population weights
            yields same-direction but smaller and insignificant effects
            (&tau;=+4: &minus;0.8% vs &minus;2.8%), consistent with the effect being
            concentrated in larger, more liquid housing markets where Zillow
            coverage is strongest.
          </p>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            <strong>Geographic intensity:</strong> Replacing NFIP policy
            penetration with the LOMR polygon area / ZCTA area ratio as the
            intensity measure. Coefficients flip positive and are
            insignificant, suggesting that raw spatial overlap with
            reclassified zones is not sufficient; the effect operates through
            channels tied to insurance exposure and risk information rather
            than geographic footprint alone.
          </p>
          <RegressionTable data={regressionTables.robustness} />
        </div>

        {/* Urban Subsample */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Urban Subsample (Density &ge; 1,000)
          </h3>
          <p className="text-sm mb-4 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            Restricting to zip codes with population density &ge; 1,000 per
            square mile reduces the sample by 44% (228,005 &rarr; 127,790 obs;
            339 &rarr; 155 county clusters) but tests whether the effect
            concentrates in denser, more liquid housing markets. The binary
            event study coefficients are uniformly larger in the urban
            subsample: &tau;=+4 reaches{" "}
            <strong style={{ color: "var(--color-negative)" }}>&minus;3.1%</strong>{" "}
            (vs &minus;2.8% in the full sample), and &tau;=+3 gains a
            significance star (**&thinsp;vs&thinsp;*). The intensity specification
            is even sharper: &tau;=+1 roughly doubles (&minus;1.69*** vs
            &minus;0.81**) and &tau;=+2 gains two stars.
          </p>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            Parallel trends still hold (F(3,&thinsp;154)&thinsp;=&thinsp;1.72,
            p&thinsp;=&thinsp;0.16) but with less margin than the full sample.
            The pattern is consistent with flood risk capitalization being
            strongest where housing is most liquid and Zillow coverage is most
            reliable.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <EventStudyChart {...eventStudyMainUrban} />
            <EventStudyChart {...eventStudyIntensityUrban} />
          </div>
        </div>

        {/* Bacon Decomposition */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Goodman-Bacon Decomposition
          </h3>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            With staggered treatment timing, the TWFE estimator is a weighted
            average of all 2&times;2 DiD comparisons, including potentially
            problematic comparisons that use already-treated units as controls{" "}
            <span className="font-mono text-xs">(Goodman-Bacon, 2021)</span>.
            The decomposition below shows the weight and estimate for each comparison
            type. The Bacon specification uses an annual balanced panel without controls
            or weights, yielding a positive overall estimate (+0.020) that differs from
            the main TWFE (&minus;0.007). The event study&apos;s intensity specification
            reveals the heterogeneity that a single DiD number obscures.
          </p>
          <div
            className="rounded-lg overflow-hidden"
            style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
          >
            <Image
              src="/images/bacon_decomposition.png"
              alt="Goodman-Bacon decomposition of TWFE DiD estimate"
              width={1200}
              height={750}
              className="w-full h-auto"
            />
          </div>
        </div>

        {/* Callaway & Sant'Anna */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Callaway &amp; Sant&apos;Anna Estimator
          </h3>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            The heterogeneity-robust{" "}
            <span className="font-mono text-xs">
              Callaway &amp; Sant&apos;Anna (2021)
            </span>{" "}
            estimator computes group-time average treatment effects separately for
            each cohort and aggregates them without the problematic comparisons
            identified by Goodman-Bacon. The ATT estimates are positive (+0.2% to
            +1.5%), opposite in sign to the main TWFE, and pre-treatment ATTs are
            significantly positive, suggesting the C&amp;S specification (annual,
            no controls, balanced panel) does not fully satisfy parallel trends.
            The discrepancy likely reflects the stripped-down specification required
            by the <span className="font-mono text-xs">csdid</span> package
            (no continuous controls, no weights, annual collapse).
          </p>
          <EventStudyChart
            title={csJson.title}
            y_label={csJson.y_label}
            reference_tau={csJson.reference_tau}
            points={csPoints}
          />
        </div>

        {/* Placebo Test */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Placebo Test: Unemployment as Outcome
          </h3>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            Running the main event study specification with county unemployment
            as the outcome provides a placebo check: if the housing effect is
            specific to home values, unemployment should be unaffected. However,
            the pre-treatment interaction test rejects parallel trends
            (F(3, 338) = 7.22, p = 0.0001), and the &tau;=+4 bin is
            significantly negative. This result should be read as a warning
            sign, not supportive evidence. It implies that the processes
            generating LOMRs may correlate with local economic changes not
            fully absorbed by a linear unemployment control. The housing
            estimates remain the paper&apos;s primary results, but readers
            should note that the placebo does not cleanly rule out
            macro-level confounds.
          </p>
          <EventStudyChart {...eventStudyPlacebo} />
        </div>

        {/* Leave-One-Out Stability */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Leave-One-Out by State
          </h3>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            Each row shows the &tau; = +4 coefficient when a single state is
            excluded from the sample. The dashed blue line marks the
            full-sample estimate. Stability across exclusions indicates that
            no single state drives the result.
          </p>
          <LeaveOneOutChart {...leaveOneOutState} />
        </div>

        {/* Alternative Clustering */}
        <div>
          <h3 className="text-lg font-semibold mb-2">
            Alternative Clustering: County vs State
          </h3>
          <p className="text-sm mb-6 max-w-3xl" style={{ color: "var(--color-text-secondary)" }}>
            The baseline specification clusters standard errors at the county
            level (339 clusters). Clustering at the state level (22 clusters)
            accounts for broader spatial correlation in shocks, producing wider
            confidence intervals. The &tau;=+4 coefficient remains significant
            under state-level clustering (CI: [&minus;0.055, &minus;0.003]),
            but &tau;=+3 loses its borderline significance. Point estimates are
            unchanged; only the standard errors differ.
          </p>
          <EventStudyChart
            title={altClusteringData.title}
            y_label={altClusteringData.y_label}
            reference_tau={altClusteringData.reference_tau}
            points={altClusteringData.series[0]?.points.map(p => ({ ...p, se: p.coef === 0 ? 0 : (p.ci_hi - p.ci_lo) / (2 * 1.96) })) ?? []}
            allSeries={altClusteringData.series}
          />
        </div>
      </div>
    </Section>
  );
}

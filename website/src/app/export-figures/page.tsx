"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  eventStudyMain,
  eventStudyIntensity,
  eventStudyIntensityQuartiles,
  eventStudyMainUrban,
  eventStudyIntensityUrban,
  eventStudyPlacebo,
  leaveOneOutState,
} from "@/lib/data";
import updownDecomposedJson from "../../../public/data/event_study_updown_decomposed.json";
import updownJson from "../../../public/data/event_study_updown.json";
import policiesJson from "../../../public/data/event_study_policies.json";
import policiesUpdownJson from "../../../public/data/event_study_policies_updown.json";
import disclosureJson from "../../../public/data/event_study_disclosure.json";
import republicanJson from "../../../public/data/event_study_republican.json";
import sfhaCrossingJson from "../../../public/data/event_study_sfha_crossing.json";
import altClusteringJson from "../../../public/data/event_study_alt_clustering.json";
import trendsJson from "../../../public/data/home_value_trends.json";
import timingJson from "../../../public/data/treatment_timing.json";
import csJson from "../../../public/data/event_study_cs.json";
import type { EventStudyData, EventStudyPoint, MultiSeriesData } from "@/types";

const EventStudyChart = dynamic(() => import("@/components/EventStudyChart"), { ssr: false });
const TrendsChart = dynamic(() => import("@/components/TrendsChart"), { ssr: false });
const BarChart = dynamic(() => import("@/components/BarChart"), { ssr: false });
const LeaveOneOutChart = dynamic(() => import("@/components/LeaveOneOutChart"), { ssr: false });
const TreatmentMap = dynamic(() => import("@/components/TreatmentMap"), { ssr: false });

// Two-series data types
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
const updownData = updownJson as TwoSeriesData;
const policiesData = policiesJson as EventStudyData;
const policiesUpdownData = policiesUpdownJson as TwoSeriesData;
const sfhaCrossingData = sfhaCrossingJson as EventStudyData;
const altClusteringData = altClusteringJson as MultiSeriesData;

function addSE(
  pts: Array<{ tau: number; coef: number; ci_lo: number; ci_hi: number }>
): EventStudyPoint[] {
  return pts.map((p) => ({
    ...p,
    se: p.coef === 0 ? 0 : (p.ci_hi - p.ci_lo) / (2 * 1.96),
  }));
}

const csPoints: EventStudyPoint[] = [
  ...csJson.series[0].points,
  ...csJson.series[1].points,
].map((p) => ({
  ...p,
  se: p.coef === 0 ? 0 : (p.ci_hi - p.ci_lo) / (2 * 1.96),
}));

// Chart container with fixed dimensions for consistent export
function FigureBox({
  id,
  width = 800,
  height,
  children,
}: {
  id: string;
  width?: number;
  height?: number;
  children: React.ReactNode;
}) {
  return (
    <div
      data-figure={id}
      style={{
        width: `${width}px`,
        height: height ? `${height}px` : undefined,
        padding: "24px",
        background: "#ffffff",
        marginBottom: "40px",
      }}
    >
      {children}
    </div>
  );
}

export default function ExportFigures() {
  const [ready, setReady] = useState(false);

  // Force light theme on mount
  useEffect(() => {
    document.documentElement.classList.add("light");
    document.documentElement.classList.remove("dark");
    // Allow time for all charts to render
    const timer = setTimeout(() => setReady(true), 4000);
    return () => clearTimeout(timer);
  }, []);

  const upSeries = updownDecomposedData.series[0];
  const downSeries = updownDecomposedData.series[1];
  const discSeries = disclosureData.series[0];
  const nodiscSeries = disclosureData.series[1];
  const repSeries = republicanData.series[0];
  const demSeries = republicanData.series[1];

  return (
    <div
      style={{
        background: "#ffffff",
        padding: "40px",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <h1 style={{ color: "#111", marginBottom: "8px" }}>Figure Export</h1>
      <p style={{ color: "#666", marginBottom: "40px" }}>
        {ready ? "Ready for capture" : "Rendering charts..."}
      </p>
      <div data-ready={ready ? "true" : "false"} />

      {/* s05 - Main Event Study */}
      <FigureBox id="s05_event_study_main">
        <EventStudyChart {...eventStudyMain} />
      </FigureBox>

      {/* s06 - Policy Intensity */}
      <FigureBox id="s06_event_study_intensity">
        <EventStudyChart {...eventStudyIntensity} />
      </FigureBox>

      {/* s06b - Intensity Quartiles (2x2 grid) */}
      <FigureBox id="s06b_event_study_intensity_quartiles" width={900}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
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
      </FigureBox>

      {/* s08 - Insurance Policies */}
      <FigureBox id="s08_event_study_policies">
        <EventStudyChart {...policiesData} />
      </FigureBox>

      {/* s08b - Insurance Policies by Up/Down */}
      <FigureBox id="s08b_event_study_policies_updown">
        <EventStudyChart
          title={policiesUpdownData.title}
          y_label={policiesUpdownData.y_label}
          reference_tau={policiesUpdownData.reference_tau}
          points={addSE(policiesUpdownData.series[0].points)}
          secondSeries={addSE(policiesUpdownData.series[1].points)}
          seriesLabels={[policiesUpdownData.series[0].label, policiesUpdownData.series[1].label]}
          seriesColors={["var(--color-negative)", "var(--color-accent)"]}
        />
      </FigureBox>

      {/* s09 - Up vs Down (binary) */}
      <FigureBox id="s09_event_study_updown">
        <EventStudyChart
          title={updownData.title}
          y_label={updownData.y_label}
          reference_tau={updownData.reference_tau}
          points={addSE(updownData.series[0].points)}
          secondSeries={addSE(updownData.series[1].points)}
          seriesLabels={[updownData.series[0].label, updownData.series[1].label]}
          seriesColors={["var(--color-negative)", "var(--color-accent)"]}
        />
      </FigureBox>

      {/* s09 - Up vs Down Decomposed */}
      <FigureBox id="s09_event_study_updown_decomposed">
        <EventStudyChart
          title={updownDecomposedData.title}
          y_label={updownDecomposedData.y_label}
          reference_tau={updownDecomposedData.reference_tau}
          points={addSE(upSeries.points)}
          secondSeries={addSE(downSeries.points)}
          seriesLabels={["Upzoned (risk \u2191)", "Downzoned (risk \u2193)"]}
          seriesColors={["var(--color-negative)", "var(--color-accent)"]}
        />
      </FigureBox>

      {/* s09b - Disclosure Laws */}
      <FigureBox id="s09b_event_study_disclosure">
        <EventStudyChart
          title={disclosureData.title}
          y_label={disclosureData.y_label}
          reference_tau={disclosureData.reference_tau}
          points={addSE(discSeries.points)}
          secondSeries={addSE(nodiscSeries.points)}
          seriesLabels={["Disclosure states (\u03b2+\u03b3)", "Non-disclosure states (\u03b2)"]}
          seriesColors={["var(--color-negative)", "var(--color-accent)"]}
        />
      </FigureBox>

      {/* s09c - Republican */}
      <FigureBox id="s09c_event_study_republican">
        <EventStudyChart
          title={republicanData.title}
          y_label={republicanData.y_label}
          reference_tau={republicanData.reference_tau}
          points={addSE(repSeries.points)}
          secondSeries={addSE(demSeries.points)}
          seriesLabels={["Republican counties", "Democratic counties"]}
          seriesColors={["var(--color-negative)", "var(--color-accent)"]}
        />
      </FigureBox>

      {/* s09d - SFHA Crossing */}
      <FigureBox id="s09d_event_study_sfha_crossing">
        <EventStudyChart {...sfhaCrossingData} />
      </FigureBox>

      {/* s10 - Parallel Trends */}
      <FigureBox id="s10_parallel_trends">
        <TrendsChart {...trendsJson} />
      </FigureBox>

      {/* s10 - Treatment Timing */}
      <FigureBox id="s10_treatment_timing_hist">
        <BarChart {...timingJson} />
      </FigureBox>

      {/* s13 - Callaway & Sant'Anna */}
      <FigureBox id="s13_event_study_cs">
        <EventStudyChart
          title={csJson.title}
          y_label={csJson.y_label}
          reference_tau={csJson.reference_tau}
          points={csPoints}
        />
      </FigureBox>

      {/* s14 - Placebo */}
      <FigureBox id="s14_event_study_placebo">
        <EventStudyChart {...eventStudyPlacebo} />
      </FigureBox>

      {/* Urban subsample - main */}
      <FigureBox id="event_study_main_urban">
        <EventStudyChart {...eventStudyMainUrban} />
      </FigureBox>

      {/* Urban subsample - intensity */}
      <FigureBox id="event_study_intensity_urban">
        <EventStudyChart {...eventStudyIntensityUrban} />
      </FigureBox>

      {/* Leave-One-Out */}
      <FigureBox id="leave_one_out_state" height={600}>
        <LeaveOneOutChart {...leaveOneOutState} />
      </FigureBox>

      {/* Alternative Clustering */}
      <FigureBox id="event_study_alt_clustering">
        <EventStudyChart
          title={altClusteringData.title}
          y_label={altClusteringData.y_label}
          reference_tau={altClusteringData.reference_tau}
          points={
            altClusteringData.series[0]?.points.map((p) => ({
              ...p,
              se: p.coef === 0 ? 0 : (p.ci_hi - p.ci_lo) / (2 * 1.96),
            })) ?? []
          }
          allSeries={altClusteringData.series}
        />
      </FigureBox>

      {/* Treatment Map */}
      <FigureBox id="treatment_map_presentation" width={1000} height={650}>
        <TreatmentMap />
      </FigureBox>
    </div>
  );
}

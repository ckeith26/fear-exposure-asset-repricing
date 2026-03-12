"use client";

import dynamic from "next/dynamic";
import { metadata, eventStudyMain } from "@/lib/data";

const TreatmentMap = dynamic(() => import("@/components/TreatmentMap"), {
  ssr: false,
  loading: () => (
    <div
      className="w-full rounded-lg animate-pulse"
      style={{
        background: "var(--color-surface)",
        aspectRatio: "100 / 58",
      }}
    />
  ),
});

const EventStudyChart = dynamic(() => import("@/components/EventStudyChart"), {
  ssr: false,
  loading: () => (
    <div
      className="w-full rounded-lg animate-pulse"
      style={{ background: "var(--color-surface)", height: "360px" }}
    />
  ),
});

export default function Hero() {
  return (
    <div className="relative flex flex-col items-center px-6 pt-20 pb-10 overflow-hidden">
      {/* Subtle background gradient */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          background:
            "radial-gradient(ellipse at 50% 80%, rgba(59,130,246,0.08) 0%, transparent 60%)",
        }}
      />

      <div className="relative z-10 text-center max-w-4xl mb-8">
        {/* Acronym expansion */}
        <p className="font-mono text-sm tracking-[0.15em] uppercase mb-3" style={{ color: "var(--color-accent)" }}>
          Flood Exposure and Asset Repricing
        </p>

        {/* Title */}
        <h1 className="text-3xl md:text-5xl font-bold tracking-tight leading-tight mb-4">
          {metadata.title}
        </h1>

        {/* Subtitle */}
        <p className="text-base md:text-lg mb-6" style={{ color: "var(--color-text-secondary)" }}>
          {metadata.subtitle}
        </p>

        {/* Key finding - inline compact */}
        <div className="flex items-center justify-center gap-4 mb-2">
          <span className="font-mono text-4xl md:text-5xl font-bold" style={{ color: "var(--color-negative)" }}>
            {metadata.headline_pct}%
          </span>
          <span className="text-sm text-left max-w-xs" style={{ color: "var(--color-text-secondary)" }}>
            {metadata.headline_description}
          </span>
        </div>
        <p className="text-xs font-mono mb-4" style={{ color: "var(--color-text-secondary)" }}>
          {metadata.n_observations_regression} zip-quarter obs &middot; {metadata.analysis_window.start}&ndash;{metadata.analysis_window.end}
        </p>

        {/* Author */}
        <p className="text-xs font-mono" style={{ color: "var(--color-text-secondary)" }}>
          by {metadata.author}
        </p>
        <p className="text-xs font-mono mt-1" style={{ color: "var(--color-text-secondary)" }}>
          Professor Apoorv Gupta &middot; Winter 2026
        </p>
        <p className="text-xs font-mono mt-1" style={{ color: "var(--color-text-secondary)" }}>
          {metadata.course}
        </p>
      </div>

      {/* Map */}
      <div className="relative z-10 w-full max-w-6xl">
        <TreatmentMap />
      </div>

      {/* Main result preview */}
      <div className="relative z-10 w-full max-w-4xl mt-12">
        <p
          className="text-sm mb-6 text-center max-w-2xl mx-auto"
          style={{ color: "var(--color-text-secondary)" }}
        >
          Home values decline gradually after LOMR flood zone reclassification,
          reaching &minus;2.8% after four or more years. Pre-treatment
          coefficients near zero confirm the parallel trends assumption.
        </p>
        <EventStudyChart {...eventStudyMain} />
      </div>
    </div>
  );
}

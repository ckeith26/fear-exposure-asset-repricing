"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Section, { SectionTitle } from "@/components/Section";

function useCountUp(end: number, duration = 1200) {
  const [value, setValue] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const hasAnimated = useRef(false);

  const animate = useCallback(() => {
    if (hasAnimated.current) return;
    hasAnimated.current = true;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(Math.round(eased * end));
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [end, duration]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) animate(); },
      { threshold: 0.3 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [animate]);

  return { ref, value };
}

interface StatItem {
  label: string;
  numericValue: number;
  suffix: string;
  sub: string;
}

const STATS: StatItem[] = [
  { label: "LOMR polygons analyzed", numericValue: 9473, suffix: "", sub: "Effective LOMRs from FEMA NFHL" },
  { label: "Coastal zip codes", numericValue: 4272, suffix: "", sub: "Estimation sample after restrictions" },
  { label: "Panel observations", numericValue: 228005, suffix: "", sub: "Zip-quarter, 2009\u20132022" },
  { label: "Data sources", numericValue: 13, suffix: "", sub: "FEMA, NFIP, Zillow, BLS, Census, MIT, FRED, NOAA, State laws" },
];

function AnimatedStat({ item, delay }: { item: StatItem; delay: number }) {
  const { ref, value } = useCountUp(item.numericValue, 1200 + delay);
  const formatted = value.toLocaleString("en-US");

  return (
    <div
      ref={ref}
      className="rounded-lg p-4"
      style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
    >
      <div className="font-mono text-2xl font-bold" style={{ color: "var(--color-accent)" }}>
        {formatted}{item.suffix}
      </div>
      <div className="text-sm font-medium mt-1">{item.label}</div>
      <div className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>
        {item.sub}
      </div>
    </div>
  );
}

export default function ResearchQuestion() {
  return (
    <Section id="research-question">
      <SectionTitle subtitle="Motivation and contribution">
        Research Question
      </SectionTitle>

      <div className="grid md:grid-cols-5 gap-12">
        {/* Main text */}
        <div className="md:col-span-3 space-y-5 text-[15px] leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
          <p>
            When FEMA updates a flood map through a{" "}
            <strong style={{ color: "var(--color-text)" }}>
              Letter of Map Revision (LOMR)
            </strong>
            , it officially changes the flood risk classification for properties
            in the affected area. Properties newly designated as high-risk must
            carry flood insurance if they have a federally backed mortgage - an
            immediate, tangible cost. Properties removed from high-risk zones see
            the opposite: reduced insurance burdens and an implicit signal that
            flood risk has diminished.
          </p>
          <p>
            This paper asks a simple question:{" "}
            <strong style={{ color: "var(--color-text)" }}>
              do housing markets actually capitalize these flood risk signals?
            </strong>{" "}
            If home prices respond to LOMR reclassifications, it suggests buyers
            and sellers are pricing in government-assessed flood risk. If prices
            don&apos;t respond, it raises questions about whether flood risk
            information reaches or influences market participants.
          </p>
          <p>
            Using a staggered difference-in-differences design, this paper exploits
            the quasi-random timing of LOMR effective dates across U.S. coastal zip
            codes from 2009 to 2022 to estimate the causal effect of flood zone
            reclassification on home values.
          </p>
        </div>

        {/* Key numbers */}
        <div className="md:col-span-2 space-y-4">
          {STATS.map((item, i) => (
            <AnimatedStat key={item.label} item={item} delay={i * 150} />
          ))}
        </div>
      </div>
    </Section>
  );
}

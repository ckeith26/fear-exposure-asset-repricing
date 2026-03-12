"use client";

import { useEffect, useRef } from "react";

interface SectionProps {
  id: string;
  children: React.ReactNode;
  className?: string;
  fullWidth?: boolean;
}

export default function Section({
  id,
  children,
  className = "",
  fullWidth = false,
}: SectionProps) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("visible");
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section
      ref={ref}
      id={id}
      className={`py-20 ${fullWidth ? "" : "max-w-6xl mx-auto px-6"} ${className}`}
    >
      {children}
    </section>
  );
}

export function SectionTitle({
  children,
  subtitle,
}: {
  children: React.ReactNode;
  subtitle?: string;
}) {
  return (
    <div className="mb-12">
      <h2 className="text-2xl font-semibold tracking-tight">{children}</h2>
      {subtitle && (
        <p className="mt-2 text-[var(--color-text-secondary)] text-sm">
          {subtitle}
        </p>
      )}
      <div
        className="mt-4 h-px w-16"
        style={{ background: "var(--color-accent)" }}
      />
    </div>
  );
}

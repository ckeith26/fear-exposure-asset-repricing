"use client";

import { useEffect, useRef, useState } from "react";

function InlineKatex({ latex }: { latex: string }) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    import("katex").then((katex) => {
      if (ref.current) {
        katex.default.render(latex, ref.current, {
          displayMode: false,
          throwOnError: false,
          output: "html",
        });
      }
    });
  }, [latex]);

  return <span ref={ref} />;
}

export default function EquationBlock({
  latex,
  compact = false,
  labels,
}: {
  latex: string;
  compact?: boolean;
  labels?: Array<{ symbol: string; description: string }>;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    import("katex").then((katex) => {
      if (ref.current) {
        while (ref.current.firstChild) {
          ref.current.removeChild(ref.current.firstChild);
        }
        const span = document.createElement("span");
        ref.current.appendChild(span);
        katex.default.render(latex, span, {
          displayMode: true,
          throwOnError: false,
          output: "html",
        });
        setReady(true);
      }
    });
  }, [latex]);

  return (
    <div
      className={`${compact ? "py-4 px-3 my-5" : "py-6 px-4 my-8"} rounded-lg overflow-x-auto transition-opacity duration-300`}
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        opacity: ready ? 1 : 0,
        minHeight: compact ? "56px" : "80px",
      }}
    >
      <div ref={ref} className="text-center" />
      {labels && labels.length > 0 && (
        <div
          className="flex flex-wrap justify-center gap-x-5 gap-y-1 px-4 pb-3 text-xs"
          style={{
            color: "var(--color-text-secondary)",
            borderTop: "1px solid var(--color-border)",
            paddingTop: "0.6rem",
            marginTop: "0.25rem",
          }}
        >
          {labels.map((l, i) => (
            <span key={i} className="inline-flex items-baseline gap-1">
              <InlineKatex latex={l.symbol} />
              <span>{" = " + l.description}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

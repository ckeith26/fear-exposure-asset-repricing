'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { SummaryStatsData, BalanceTableData, HistogramBin, SummaryStatVariable, SummaryStatsPanel } from '@/types';

/**
 * StatTable - a generic statistics table for both summary statistics and
 * balance (covariate comparison) tables.
 *
 * For type 'summary', renders the standard descriptive-statistics layout:
 *   Variable | N | Mean | Std Dev | Min | P25 | Median | P75 | Max
 *
 * For type 'balance', renders a treatment/control comparison:
 *   Variable | Control | Treated | Difference
 *
 * Styling mirrors the RegressionTable aesthetic: dark surface, monospace
 * numbers, hover-highlighted rows, and horizontal scroll on small screens.
 */

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

/** Rows whose variable name contains these substrings are formatted as
 *  dollar amounts (prefixed with "$"). Case-insensitive match. */
const DOLLAR_KEYWORDS = ['home value', 'zhvi', 'premium', 'price', 'income'];

function isDollarRow(variable: string): boolean {
  const lower = variable.toLowerCase();
  return DOLLAR_KEYWORDS.some((kw) => lower.includes(kw));
}

/** Format a count (N) with locale-aware thousands separators. */
function formatCount(n: number): string {
  return n.toLocaleString('en-US');
}

/** Format a numeric statistic to 2 decimal places, optionally with a
 *  leading "$" for dollar-denominated rows. */
function formatStat(value: number, dollar: boolean): string {
  const formatted = value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return dollar ? `$${formatted}` : formatted;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  title: string;
  type: 'summary' | 'balance';
  data: SummaryStatsData | BalanceTableData;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function StatTable({ title, type, data }: Props) {
  return (
    <div className="w-full overflow-x-auto">
      {type === 'summary' ? (
        <SummaryTable title={title} data={data as SummaryStatsData} />
      ) : (
        <BalanceTable title={title} data={data as BalanceTableData} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared Histogram SVG renderer
// ---------------------------------------------------------------------------

function formatAxisLabel(value: number, dollar: boolean): string {
  if (Math.abs(value) >= 1_000_000) {
    const m = value / 1_000_000;
    return dollar ? `$${m.toFixed(1)}M` : `${m.toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    const k = value / 1_000;
    return dollar ? `$${k.toFixed(0)}K` : `${k.toFixed(0)}K`;
  }
  return dollar ? `$${value.toFixed(1)}` : value.toFixed(1);
}

function HistogramSVG({
  bins,
  mean,
  dollar,
  width,
  height,
  padding,
}: {
  bins: HistogramBin[];
  mean: number;
  dollar: boolean;
  width: number;
  height: number;
  padding: { top: number; right: number; bottom: number; left: number };
}) {
  const maxCount = Math.max(...bins.map((b) => b.count));
  const xMin = bins[0].x0;
  const xMax = bins[bins.length - 1].x1;
  const xRange = xMax - xMin;
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const barColor = 'var(--color-accent, #6366f1)';

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <g transform={`translate(${padding.left},${padding.top})`}>
        {bins.map((bin, i) => {
          const x = ((bin.x0 - xMin) / xRange) * plotW;
          const w = ((bin.x1 - bin.x0) / xRange) * plotW;
          const h = (bin.count / maxCount) * plotH;
          return (
            <rect
              key={i}
              x={x}
              y={plotH - h}
              width={Math.max(w - 0.5, 0.5)}
              height={h}
              fill={barColor}
              opacity={0.8}
            />
          );
        })}

        {/* Mean line */}
        {mean >= xMin && mean <= xMax && (
          <>
            <line
              x1={((mean - xMin) / xRange) * plotW}
              x2={((mean - xMin) / xRange) * plotW}
              y1={0}
              y2={plotH}
              stroke="var(--color-text)"
              strokeWidth={1.5}
              strokeDasharray="3,2"
              opacity={0.7}
            />
            <text
              x={((mean - xMin) / xRange) * plotW}
              y={-6}
              textAnchor="middle"
              fill="var(--color-text)"
              fontSize={9}
              fontFamily="sans-serif"
            >
              mean
            </text>
          </>
        )}

        {/* X-axis */}
        <line x1={0} x2={plotW} y1={plotH} y2={plotH} stroke="var(--color-text)" opacity={0.3} />
        <text
          x={0}
          y={plotH + 14}
          textAnchor="start"
          fill="var(--color-text-secondary)"
          fontSize={9}
          fontFamily="monospace"
        >
          {formatAxisLabel(xMin, dollar)}
        </text>
        <text
          x={plotW}
          y={plotH + 14}
          textAnchor="end"
          fill="var(--color-text-secondary)"
          fontSize={9}
          fontFamily="monospace"
        >
          {formatAxisLabel(xMax, dollar)}
        </text>
      </g>
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Hover tooltip (small, follows cursor, portaled)
// ---------------------------------------------------------------------------

function HistogramTooltip({
  bins,
  variableName,
  mean,
  dollar,
  mouseX,
  mouseY,
}: {
  bins: HistogramBin[];
  variableName: string;
  mean: number;
  dollar: boolean;
  mouseX: number;
  mouseY: number;
}) {
  const w = 296;
  const h = 180;

  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let left = mouseX + 16;
  let top = mouseY - h / 2;

  if (left + w > vw - 8) left = mouseX - w - 8;
  if (top + h > vh - 8) top = vh - h - 8;
  if (top < 8) top = 8;
  if (left < 8) left = 8;

  return createPortal(
    <div
      className="rounded-lg border shadow-lg pointer-events-none"
      style={{
        position: 'fixed',
        zIndex: 9999,
        background: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        left,
        top,
        padding: '8px',
        width: w,
      }}
    >
      <div
        className="mb-1 px-1 font-sans text-xs font-medium truncate"
        style={{ color: 'var(--color-text)' }}
        title={variableName}
      >
        {variableName}
      </div>
      <HistogramSVG
        bins={bins}
        mean={mean}
        dollar={dollar}
        width={280}
        height={140}
        padding={{ top: 24, right: 12, bottom: 28, left: 12 }}
      />
      <div
        className="mt-1 px-1 font-sans text-[10px]"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        Click for details
      </div>
    </div>,
    document.body,
  );
}

// ---------------------------------------------------------------------------
// Click modal (large, centered, portaled)
// ---------------------------------------------------------------------------

function HistogramModal({
  row,
  dollar,
  onClose,
}: {
  row: SummaryStatVariable;
  dollar: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const stats = [
    { label: 'N', value: formatCount(row.count) },
    { label: 'Mean', value: formatStat(row.mean, dollar) },
    { label: 'Std Dev', value: formatStat(row.sd, dollar) },
    { label: 'Min', value: formatStat(row.min, dollar) },
    { label: 'Max', value: formatStat(row.max, dollar) },
  ];

  return createPortal(
    <div
      className="fixed inset-0 flex items-center justify-center"
      style={{ zIndex: 10000, background: 'rgba(0,0,0,0.5)' }}
      onClick={onClose}
    >
      <div
        className="rounded-xl border shadow-2xl"
        style={{
          background: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          padding: '20px 24px',
          maxWidth: '90vw',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="mb-3 font-sans text-sm font-semibold"
          style={{ color: 'var(--color-text)' }}
        >
          {row.variable}
        </div>
        <HistogramSVG
          bins={row.histogram!}
          mean={row.mean}
          dollar={dollar}
          width={480}
          height={260}
          padding={{ top: 32, right: 20, bottom: 36, left: 20 }}
        />
        <div
          className="mt-3 flex gap-6 font-mono text-xs"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {stats.map((s) => (
            <span key={s.label}>
              <span className="font-sans font-medium" style={{ color: 'var(--color-text)' }}>
                {s.label}
              </span>{' '}
              {s.value}
            </span>
          ))}
        </div>
      </div>
    </div>,
    document.body,
  );
}

// ---------------------------------------------------------------------------
// Summary Statistics sub-component
// ---------------------------------------------------------------------------

const SUMMARY_HEADERS = ['Variable', 'N', 'Mean', 'Std Dev', 'Min', 'P25', 'Median', 'P75', 'Max'];

function SummaryTable({ title, data }: { title: string; data: SummaryStatsData }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const [modalIdx, setModalIdx] = useState<number | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [mounted, setMounted] = useState(false);
  const handleModalClose = useCallback(() => setModalIdx(null), []);

  useEffect(() => setMounted(true), []);

  return (
    <>
      <table
        className="reg-table w-full border-collapse"
        style={{ minWidth: '720px', color: 'var(--color-text)' }}
      >
        {/* Caption */}
        <caption
          className="mb-4 text-left font-sans text-base font-semibold tracking-tight"
          style={{ color: 'var(--color-text)' }}
        >
          {title}
        </caption>

        {/* Header */}
        <thead>
          <tr style={{ borderBottom: '2px solid var(--color-text)' }}>
            {SUMMARY_HEADERS.map((header, i) => (
              <th
                key={header}
                className={`px-4 py-2 font-sans text-sm font-medium ${
                  i === 0 ? 'text-left' : 'text-right'
                }`}
                style={{ color: i === 0 ? 'var(--color-text-secondary)' : 'var(--color-text)' }}
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>

        {/* Body */}
        <tbody>
          {(data.panels && data.panels.length > 0 ? data.panels : [{ label: '', variables: data.variables }] as SummaryStatsPanel[]).map((panel, pi) => {
            // Build a flat index so hover/modal still work across panels
            const panelStartIdx = data.panels
              ? data.panels.slice(0, pi).reduce((sum, p) => sum + p.variables.length, 0)
              : 0;

            return (
              <React.Fragment key={pi}>
                {/* Panel header row */}
                {panel.label && (
                  <tr>
                    <td
                      colSpan={SUMMARY_HEADERS.length}
                      className="pt-4 pb-1 text-left font-sans text-sm font-semibold italic"
                      style={{ color: 'var(--color-text)' }}
                    >
                      {panel.label}
                    </td>
                  </tr>
                )}

                {panel.variables.map((row, ri) => {
                  const globalIdx = panelStartIdx + ri;
                  const dollar = isDollarRow(row.variable);
                  const hasHist = !!(row.histogram && row.histogram.length > 0);
                  return (
                    <tr
                      key={globalIdx}
                      className="transition-colors duration-150"
                      style={{
                        cursor: hasHist ? 'pointer' : 'default',
                        background: hoverIdx === globalIdx ? 'var(--color-surface-hover, rgba(255,255,255,0.04))' : undefined,
                      }}
                      onMouseEnter={() => hasHist && setHoverIdx(globalIdx)}
                      onMouseLeave={() => setHoverIdx(null)}
                      onMouseMove={(e) => {
                        if (hasHist) setMousePos({ x: e.clientX, y: e.clientY });
                      }}
                      onClick={() => {
                        if (hasHist) {
                          setHoverIdx(null);
                          setModalIdx(globalIdx);
                        }
                      }}
                    >
                      <td
                        className="py-2 pr-6 text-left font-sans text-sm"
                        style={{ color: 'var(--color-text)', paddingLeft: panel.label ? '16px' : undefined }}
                      >
                        {hasHist ? (
                          <span className="underline decoration-dotted underline-offset-2">
                            {row.variable}
                          </span>
                        ) : (
                          row.variable
                        )}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm">
                        {formatCount(row.count)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm">
                        {formatStat(row.mean, dollar)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm">
                        {formatStat(row.sd, dollar)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm">
                        {formatStat(row.min, dollar)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm">
                        {formatStat(row.p25, dollar)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm">
                        {formatStat(row.p50, dollar)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm">
                        {formatStat(row.p75, dollar)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-sm">
                        {formatStat(row.max, dollar)}
                      </td>
                    </tr>
                  );
                })}
              </React.Fragment>
            );
          })}

          {/* Bottom rule */}
          <tr aria-hidden="true">
            <td
              colSpan={SUMMARY_HEADERS.length}
              className="py-0"
              style={{ borderBottom: '2px solid var(--color-text)', height: 0 }}
            />
          </tr>
        </tbody>

        {/* Notes footer */}
        {data.notes && data.notes.length > 0 && (
          <tfoot>
            {data.notes.map((note, i) => (
              <tr key={i}>
                <td
                  colSpan={SUMMARY_HEADERS.length}
                  className={`${i === 0 ? 'pt-3' : 'pt-0'} text-left font-sans text-xs italic leading-relaxed`}
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {note}
                </td>
              </tr>
            ))}
          </tfoot>
        )}
      </table>

      {/* Hover tooltip — portaled to body */}
      {(() => {
        const allVars = data.panels && data.panels.length > 0
          ? data.panels.flatMap(p => p.variables)
          : data.variables;
        return (
          <>
            {mounted &&
              hoverIdx !== null &&
              modalIdx === null &&
              allVars[hoverIdx]?.histogram?.length && (
                <HistogramTooltip
                  bins={allVars[hoverIdx].histogram!}
                  variableName={allVars[hoverIdx].variable}
                  mean={allVars[hoverIdx].mean}
                  dollar={isDollarRow(allVars[hoverIdx].variable)}
                  mouseX={mousePos.x}
                  mouseY={mousePos.y}
                />
              )}

            {/* Click modal — portaled to body */}
            {mounted &&
              modalIdx !== null &&
              allVars[modalIdx]?.histogram?.length && (
                <HistogramModal
                  row={allVars[modalIdx]}
                  dollar={isDollarRow(allVars[modalIdx].variable)}
                  onClose={handleModalClose}
                />
              )}
          </>
        );
      })()}
    </>
  );
}

// ---------------------------------------------------------------------------
// Balance Table sub-component
// ---------------------------------------------------------------------------

const BALANCE_HEADERS = ['Variable', 'Control', 'Treated', 'Difference'];

function BalanceTable({ title, data }: { title: string; data: BalanceTableData }) {
  return (
    <table
      className="reg-table w-full border-collapse"
      style={{ minWidth: '480px', color: 'var(--color-text)' }}
    >
      {/* Caption */}
      <caption
        className="mb-4 text-left font-sans text-base font-semibold tracking-tight"
        style={{ color: 'var(--color-text)' }}
      >
        {title}
      </caption>

      {/* Header */}
      <thead>
        <tr style={{ borderBottom: '2px solid var(--color-text)' }}>
          {BALANCE_HEADERS.map((header, i) => (
            <th
              key={header}
              className={`px-4 py-2 font-sans text-sm font-medium ${
                i === 0 ? 'text-left' : 'text-right'
              }`}
              style={{ color: i === 0 ? 'var(--color-text-secondary)' : 'var(--color-text)' }}
            >
              {header}
            </th>
          ))}
        </tr>
      </thead>

      {/* Body */}
      <tbody>
        {data.variables.map((row, ri) => {
          const dollar = isDollarRow(row.variable);
          return (
            <tr
              key={ri}
              className="transition-colors duration-150"
              style={{ cursor: 'default' }}
            >
              <td
                className="py-2 pr-6 text-left font-sans text-sm"
                style={{ color: 'var(--color-text)' }}
              >
                {row.variable}
              </td>
              <td className="px-4 py-2 text-right font-mono text-sm">
                {formatStat(row.control, dollar)}
              </td>
              <td className="px-4 py-2 text-right font-mono text-sm">
                {formatStat(row.treated, dollar)}
              </td>
              <td className="px-4 py-2 text-right font-mono text-sm">
                {formatStat(row.difference, dollar)}{row.stars && <span className="text-xs align-super">{row.stars}</span>}
              </td>
            </tr>
          );
        })}

        {/* Bottom rule */}
        <tr aria-hidden="true">
          <td
            colSpan={BALANCE_HEADERS.length}
            className="py-0"
            style={{ borderBottom: '2px solid var(--color-text)', height: 0 }}
          />
        </tr>
      </tbody>

      {/* Notes footer */}
      <tfoot>
        {data.notes.map((note, i) => (
          <tr key={i}>
            <td
              colSpan={BALANCE_HEADERS.length}
              className={`${i === 0 ? 'pt-3' : 'pt-0'} text-left font-sans text-xs italic leading-relaxed`}
              style={{ color: 'var(--color-text-secondary)' }}
            >
              {note}
            </td>
          </tr>
        ))}
        <tr>
          <td
            colSpan={BALANCE_HEADERS.length}
            className="pt-1 text-left font-sans text-xs italic leading-relaxed"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Significance: *** p&lt;0.01, ** p&lt;0.05, * p&lt;0.1
          </td>
        </tr>
      </tfoot>
    </table>
  );
}

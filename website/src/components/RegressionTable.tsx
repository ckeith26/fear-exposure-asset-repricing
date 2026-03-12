'use client';

import type { RegressionTableData } from '@/types';

/**
 * RegressionTable - renders a LaTeX estout-styled econometric regression table.
 *
 * Each variable row expands into two HTML rows: a coefficient row (value + stars)
 * and a standard-error row (parenthesised, muted). Stats (Observations, R-squared)
 * appear below a double-rule separator. Notes render as small italic footer text.
 */

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

/** Format a coefficient value to 4 decimal places, falling back to scientific
 *  notation for very small absolute values (< 0.00005). */
function formatCoefficient(value: number | null): string {
  if (value === null) return '';
  const abs = Math.abs(value);
  if (abs !== 0 && abs < 0.00005) {
    // Scientific notation - keep 3 significant figures
    return value.toExponential(3);
  }
  return value.toFixed(4);
}

/** Format a standard error in parentheses. Same precision rules as coefficients. */
function formatSE(value: number | null): string {
  if (value === null) return '';
  const abs = Math.abs(value);
  if (abs !== 0 && abs < 0.00005) {
    return `(${value.toExponential(3)})`;
  }
  return `(${value.toFixed(4)})`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  data: RegressionTableData;
}

export default function RegressionTable({ data }: Props) {
  const { title, notes, columns, variables, stats } = data;
  const numCols = columns.length;

  return (
    <div className="w-full overflow-x-auto">
      <table
        className="reg-table w-full border-collapse"
        style={{
          minWidth: `${Math.max(480, 180 + numCols * 160)}px`,
          color: 'var(--color-text)',
        }}
      >
        {/* ---- Caption / title ---- */}
        <caption
          className="mb-4 text-left font-sans text-base font-semibold tracking-tight"
          style={{ color: 'var(--color-text)' }}
        >
          {title}
        </caption>

        {/* ---- Column headers ---- */}
        <thead>
          <tr
            style={{
              borderBottom: '2px solid var(--color-text)',
            }}
          >
            {/* Empty top-left cell */}
            <th
              className="py-2 pr-6 text-left font-sans text-sm font-normal"
              style={{ color: 'var(--color-text-secondary)' }}
            />
            {columns.map((col, i) => (
              <th
                key={i}
                className="px-4 py-2 text-center font-sans text-sm font-medium"
                style={{ color: 'var(--color-text)' }}
              >
                ({i + 1})
                <br />
                <span
                  className="text-xs font-normal"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {col}
                </span>
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {/* ---- Variable rows ---- */}
          {variables.map((v, vi) => (
            <VariableRows key={vi} variable={v} numCols={numCols} isLast={vi === variables.length - 1} />
          ))}

          {/* ---- Separator before stats ---- */}
          <tr aria-hidden="true">
            <td
              colSpan={numCols + 1}
              className="py-0"
              style={{
                borderTop: '1px solid var(--color-border)',
                borderBottom: '1px solid var(--color-border)',
                height: '3px',
              }}
            />
          </tr>

          {/* ---- Stats rows ---- */}
          {stats.map((stat, si) => (
            <tr key={`stat-${si}`}>
              <td
                className="py-1.5 pr-6 text-left font-sans text-sm"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                {stat.label}
              </td>
              {stat.values.map((val, ci) => (
                <td
                  key={ci}
                  className="px-4 py-1.5 text-center font-mono text-sm"
                  style={{ color: 'var(--color-text)' }}
                >
                  {val}
                </td>
              ))}
              {/* Pad remaining cells if fewer values than columns */}
              {Array.from({ length: numCols - stat.values.length }).map((_, ci) => (
                <td key={`pad-${ci}`} />
              ))}
            </tr>
          ))}

          {/* ---- Bottom rule ---- */}
          <tr aria-hidden="true">
            <td
              colSpan={numCols + 1}
              className="py-0"
              style={{
                borderBottom: '2px solid var(--color-text)',
                height: 0,
              }}
            />
          </tr>
        </tbody>

        {/* ---- Notes footer ---- */}
        {notes.length > 0 && (
          <tfoot>
            <tr>
              <td
                colSpan={numCols + 1}
                className="pt-3 text-left font-sans text-xs italic leading-relaxed"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                {notes.map((note, ni) => (
                  <span key={ni}>
                    {note}
                    {ni < notes.length - 1 && <br />}
                  </span>
                ))}
                <br />
                <span>
                  Significance: *** p&lt;0.01, ** p&lt;0.05, * p&lt;0.1
                </span>
              </td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: two rows per variable (coefficient + SE)
// ---------------------------------------------------------------------------

interface VariableRowsProps {
  variable: {
    label: string;
    coefficients: Array<{ value: number | null; stars: string }>;
    standard_errors: (number | null)[];
  };
  numCols: number;
  isLast: boolean;
}

function VariableRows({ variable, numCols, isLast }: VariableRowsProps) {
  const { label, coefficients, standard_errors } = variable;

  return (
    <>
      {/* Coefficient row */}
      <tr
        className="transition-colors duration-150"
        style={{ cursor: 'default' }}
      >
        <td
          className="py-1 pr-6 text-left font-sans text-sm"
          style={{ color: 'var(--color-text)' }}
        >
          {label}
        </td>
        {coefficients.map((coef, ci) => (
          <td
            key={ci}
            className="px-4 py-1 text-center font-mono text-sm"
            style={{ color: 'var(--color-text)' }}
          >
            {coef.value !== null && (
              <>
                {formatCoefficient(coef.value)}
                {coef.stars && (
                  <span
                    className="font-sans font-semibold"
                    style={{ color: 'var(--color-accent)' }}
                  >
                    {coef.stars}
                  </span>
                )}
              </>
            )}
          </td>
        ))}
        {/* Pad if fewer coefficients than columns */}
        {Array.from({ length: numCols - coefficients.length }).map((_, ci) => (
          <td key={`coef-pad-${ci}`} />
        ))}
      </tr>

      {/* Standard-error row */}
      <tr
        className="transition-colors duration-150"
        style={{ cursor: 'default' }}
      >
        <td />
        {standard_errors.map((se, ci) => (
          <td
            key={ci}
            className="px-4 pb-2 pt-0 text-center font-mono text-xs"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            {formatSE(se)}
          </td>
        ))}
        {/* Pad if fewer SEs than columns */}
        {Array.from({ length: numCols - standard_errors.length }).map((_, ci) => (
          <td key={`se-pad-${ci}`} />
        ))}
      </tr>
    </>
  );
}

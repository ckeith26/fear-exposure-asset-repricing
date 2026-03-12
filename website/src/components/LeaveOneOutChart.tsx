'use client';

import { useRef, useEffect, useCallback, useState } from 'react';
import * as d3 from 'd3';
import type { LeaveOneOutData } from '@/types';

const STATE_FIPS_TO_ABBR: Record<number, string> = {
  1: "AL", 2: "AK", 4: "AZ", 5: "AR", 6: "CA", 8: "CO", 9: "CT",
  10: "DE", 11: "DC", 12: "FL", 13: "GA", 15: "HI", 16: "ID", 17: "IL",
  18: "IN", 19: "IA", 20: "KS", 21: "KY", 22: "LA", 23: "ME", 24: "MD",
  25: "MA", 26: "MI", 27: "MN", 28: "MS", 29: "MO", 30: "MT", 31: "NE",
  32: "NV", 33: "NH", 34: "NJ", 35: "NM", 36: "NY", 37: "NC", 38: "ND",
  39: "OH", 40: "OK", 41: "OR", 42: "PA", 44: "RI", 45: "SC", 46: "SD",
  47: "TN", 48: "TX", 49: "UT", 50: "VT", 51: "VA", 53: "WA", 54: "WV",
  55: "WI", 56: "WY",
};

const MARGIN = { top: 20, right: 30, bottom: 60, left: 50 };
const ROW_HEIGHT = 18;

export default function LeaveOneOutChart({ title, full_sample_coef, points }: LeaveOneOutData) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [theme, setTheme] = useState('dark');

  const sorted = [...points].sort((a, b) => a.coef - b.coef);
  const chartHeight = MARGIN.top + MARGIN.bottom + sorted.length * ROW_HEIGHT;

  useEffect(() => {
    const el = document.documentElement;
    setTheme(el.classList.contains('light') ? 'light' : 'dark');
    const observer = new MutationObserver(() => {
      setTheme(el.classList.contains('light') ? 'light' : 'dark');
    });
    observer.observe(el, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(entry.contentRect.width);
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const getCSSVar = useCallback((name: string, fallback: string): string => {
    if (typeof window === 'undefined') return fallback;
    const value = getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
    return value || fallback;
  }, []);

  useEffect(() => {
    const svg = svgRef.current;
    const tooltip = tooltipRef.current;
    if (!svg || !tooltip || width === 0) return;

    const innerW = width - MARGIN.left - MARGIN.right;
    const innerH = chartHeight - MARGIN.top - MARGIN.bottom;

    const colorText = getCSSVar('--color-text', '#e4e4e7');
    const colorTextSecondary = getCSSVar('--color-text-secondary', '#9ca3af');
    const colorBorder = getCSSVar('--color-border', '#2a2d3a');
    const colorSurface = getCSSVar('--color-surface', '#1a1d27');
    const colorAccent = getCSSVar('--color-accent', '#3b82f6');
    const colorDot = theme === 'light' ? '#1e3a5f' : '#93c5fd';
    const colorCI = theme === 'light' ? '#1e3a5f' : '#60a5fa';

    const root = d3.select(svg);
    root.selectAll('*').remove();
    root
      .attr('width', width)
      .attr('height', chartHeight)
      .attr('viewBox', `0 0 ${width} ${chartHeight}`);

    const g = root
      .append('g')
      .attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

    // Scales
    const xMin = d3.min(sorted, (d) => d.ci_lo)!;
    const xMax = d3.max(sorted, (d) => d.ci_hi)!;
    const xPad = (xMax - xMin) * 0.1;

    const xScale = d3
      .scaleLinear()
      .domain([xMin - xPad, xMax + xPad])
      .range([0, innerW]);

    const yScale = d3
      .scaleBand<number>()
      .domain(sorted.map((_, i) => i))
      .range([0, innerH])
      .padding(0.2);

    // Grid lines
    const xTicks = xScale.ticks(6);
    g.selectAll('.grid')
      .data(xTicks)
      .join('line')
      .attr('x1', (d) => xScale(d))
      .attr('x2', (d) => xScale(d))
      .attr('y1', 0)
      .attr('y2', innerH)
      .attr('stroke', colorBorder)
      .attr('stroke-opacity', 0.3)
      .attr('stroke-dasharray', '2,3');

    // Zero reference line
    if (xScale.domain()[0] <= 0 && xScale.domain()[1] >= 0) {
      g.append('line')
        .attr('x1', xScale(0))
        .attr('x2', xScale(0))
        .attr('y1', 0)
        .attr('y2', innerH)
        .attr('stroke', colorTextSecondary)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '6,4');
    }

    // Full-sample reference line
    if (full_sample_coef !== null) {
      g.append('line')
        .attr('x1', xScale(full_sample_coef))
        .attr('x2', xScale(full_sample_coef))
        .attr('y1', 0)
        .attr('y2', innerH)
        .attr('stroke', colorAccent)
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '8,4')
        .attr('stroke-opacity', 0.8);

      g.append('text')
        .attr('x', xScale(full_sample_coef) + 4)
        .attr('y', -6)
        .attr('fill', colorAccent)
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .attr('font-size', '10px')
        .text('Full sample');
    }

    // CI bars + dots
    sorted.forEach((d, i) => {
      const cy = (yScale(i) ?? 0) + yScale.bandwidth() / 2;

      // Horizontal CI bar
      g.append('line')
        .attr('x1', xScale(d.ci_lo))
        .attr('x2', xScale(d.ci_hi))
        .attr('y1', cy)
        .attr('y2', cy)
        .attr('stroke', colorCI)
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.7);

      // Dot
      g.append('circle')
        .attr('cx', xScale(d.coef))
        .attr('cy', cy)
        .attr('r', 3.5)
        .attr('fill', colorDot)
        .attr('stroke', colorSurface)
        .attr('stroke-width', 1)
        .attr('cursor', 'pointer')
        .on('mouseenter', function (event: MouseEvent) {
          d3.select(this).transition().duration(100).attr('r', 5.5);
          const abbr = STATE_FIPS_TO_ABBR[d.excluded_state] ?? String(d.excluded_state);
          const tooltipEl = d3.select(tooltip);
          tooltipEl
            .style('opacity', '1')
            .style('pointer-events', 'auto')
            .html(
              `<div style="font-family: Inter, system-ui, sans-serif; font-size: 12px; line-height: 1.6;">` +
                `<div style="font-weight: 600; margin-bottom: 2px;">Excluding ${abbr}</div>` +
                `<div style="color: ${colorTextSecondary};">Coef: <span style="font-family: JetBrains Mono, monospace; color: ${colorText};">${d.coef.toFixed(4)}</span></div>` +
                `<div style="color: ${colorTextSecondary};">SE: <span style="font-family: JetBrains Mono, monospace; color: ${colorText};">${d.se.toFixed(4)}</span></div>` +
                `<div style="color: ${colorTextSecondary};">95% CI: <span style="font-family: JetBrains Mono, monospace; color: ${colorText};">[${d.ci_lo.toFixed(4)}, ${d.ci_hi.toFixed(4)}]</span></div>` +
                `<div style="color: ${colorTextSecondary};">N: <span style="font-family: JetBrains Mono, monospace; color: ${colorText};">${d.n_obs.toLocaleString()}</span></div>` +
                `</div>`,
            );
          const containerRect = containerRef.current!.getBoundingClientRect();
          const px = event.clientX - containerRect.left;
          const py = event.clientY - containerRect.top;
          const tooltipWidth = 220;
          const flipX = px + tooltipWidth + 16 > containerRect.width;
          tooltipEl
            .style('left', flipX ? `${px - tooltipWidth - 8}px` : `${px + 16}px`)
            .style('top', `${py - 20}px`);
        })
        .on('mouseleave', function () {
          d3.select(this).transition().duration(100).attr('r', 3.5);
          d3.select(tooltip)
            .style('opacity', '0')
            .style('pointer-events', 'none');
        });

      // State label
      const abbr = STATE_FIPS_TO_ABBR[d.excluded_state] ?? String(d.excluded_state);
      g.append('text')
        .attr('x', -6)
        .attr('y', cy)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'end')
        .attr('fill', colorText)
        .attr('font-family', 'JetBrains Mono, monospace')
        .attr('font-size', '10px')
        .text(abbr);
    });

    // X axis
    const xAxis = d3.axisBottom(xScale).ticks(6).tickFormat(d3.format('.3f'));
    const xAxisGroup = g
      .append('g')
      .attr('transform', `translate(0,${innerH})`)
      .call(xAxis);

    xAxisGroup.selectAll('text')
      .attr('fill', colorText)
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', '10px')
      .attr('text-anchor', 'end')
      .attr('transform', 'rotate(-45)')
      .attr('dx', '-0.5em')
      .attr('dy', '0.25em');
    xAxisGroup.selectAll('line').attr('stroke', colorBorder);
    xAxisGroup.select('.domain').attr('stroke', colorBorder);

    // X axis label
    g.append('text')
      .attr('x', innerW / 2)
      .attr('y', innerH + 52)
      .attr('text-anchor', 'middle')
      .attr('fill', colorTextSecondary)
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .attr('font-size', '12px')
      .text('\u03c4 = +4 Coefficient');
  }, [width, sorted, full_sample_coef, chartHeight, getCSSVar, theme]);

  return (
    <div style={{ width: '100%' }}>
      <h3
        style={{
          fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: '15px',
          fontWeight: 600,
          color: 'var(--color-text)',
          marginBottom: '12px',
          textAlign: 'center',
        }}
      >
        {title}
      </h3>
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          width: '100%',
          minHeight: '200px',
        }}
      >
        <svg
          ref={svgRef}
          style={{
            display: 'block',
            width: '100%',
            height: chartHeight || 'auto',
            overflow: 'visible',
          }}
        />
        <div
          ref={tooltipRef}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            opacity: 0,
            pointerEvents: 'none',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: '6px',
            padding: '10px 14px',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
            zIndex: 50,
            transition: 'opacity 0.15s ease',
            maxWidth: '240px',
          }}
        />
      </div>
    </div>
  );
}

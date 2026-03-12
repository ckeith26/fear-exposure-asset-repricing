'use client';

import { useRef, useEffect, useCallback, useState } from 'react';
import * as d3 from 'd3';
import type { EventStudyPoint, EventStudyData, SeriesConfig } from '@/types';

// ============================================================
// EventStudyChart - D3-powered interactive event study plot
// ============================================================
// Renders coefficient estimates with confidence intervals for
// a difference-in-differences event study design. Supports a
// single series or two overlaid series (e.g., up-zoned vs.
// down-zoned heterogeneity analysis).
// ============================================================

interface EventStudyChartProps extends EventStudyData {
  secondSeries?: EventStudyPoint[];
  seriesLabels?: [string, string];
  seriesColors?: [string, string];
  allSeries?: SeriesConfig[];
}

const MARGIN = { top: 20, right: 30, bottom: 50, left: 72 };

export default function EventStudyChart({
  title,
  y_label,
  reference_tau,
  points,
  secondSeries,
  seriesLabels,
  seriesColors,
  allSeries,
}: EventStudyChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [theme, setTheme] = useState('dark');

  // ----------------------------------------------------------
  // Theme observer - re-render chart when theme changes
  // ----------------------------------------------------------
  useEffect(() => {
    const el = document.documentElement;
    setTheme(el.classList.contains('light') ? 'light' : 'dark');
    const observer = new MutationObserver(() => {
      setTheme(el.classList.contains('light') ? 'light' : 'dark');
    });
    observer.observe(el, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  // ----------------------------------------------------------
  // Resize observer - tracks container size
  // ----------------------------------------------------------
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect;
        const height = Math.min(width * 0.55, 480);
        setDimensions({ width, height });
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // ----------------------------------------------------------
  // Read CSS custom properties at render time
  // ----------------------------------------------------------
  const getCSSVar = useCallback((name: string, fallback: string): string => {
    if (typeof window === 'undefined') return fallback;
    const value = getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
    return value || fallback;
  }, []);

  // ----------------------------------------------------------
  // Significance label from z-score
  // ----------------------------------------------------------
  const significanceLabel = useCallback((coef: number, se: number): string => {
    if (se === 0) return '';
    const z = Math.abs(coef / se);
    if (z > 2.576) return 'p < 0.01 (***)';
    if (z > 1.96) return 'p < 0.05 (**)';
    if (z > 1.645) return 'p < 0.10 (*)';
    return 'Not significant';
  }, []);

  // ----------------------------------------------------------
  // Main D3 render
  // ----------------------------------------------------------
  useEffect(() => {
    const svg = svgRef.current;
    const tooltip = tooltipRef.current;
    if (!svg || !tooltip || dimensions.width === 0) return;

    const { width, height } = dimensions;
    const innerW = width - MARGIN.left - MARGIN.right;
    const innerH = height - MARGIN.top - MARGIN.bottom;

    // Colors from CSS variables
    const colorAccent = seriesColors?.[0] ?? getCSSVar('--color-accent', '#3b82f6');
    const colorSecond = seriesColors?.[1] ?? getCSSVar('--color-negative', '#ef4444');
    const colorText = getCSSVar('--color-text', '#e4e4e7');
    const colorTextSecondary = getCSSVar('--color-text-secondary', '#9ca3af');
    const colorBorder = getCSSVar('--color-border', '#2a2d3a');
    const colorSurface = getCSSVar('--color-surface', '#1a1d27');
    const colorNegative = getCSSVar('--color-negative', '#ef4444');

    const isMultiSeries = !!allSeries && allSeries.length > 0;
    const isTwoSeries = !isMultiSeries && !!secondSeries && secondSeries.length > 0;
    const TAU_OFFSET = 0.12;

    // --- Clear previous render ---
    const root = d3.select(svg);
    root.selectAll('*').remove();

    root
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', `0 0 ${width} ${height}`);

    const g = root
      .append('g')
      .attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

    // --- Compute domains ---
    const allPoints = isMultiSeries
      ? allSeries.flatMap((s) => s.points.map((p) => ({ ...p, se: 0 })) as EventStudyPoint[])
      : isTwoSeries ? [...points, ...secondSeries] : points;
    const tauExtent = d3.extent(allPoints, (d) => d.tau) as [number, number];
    const yMin = d3.min(allPoints, (d) => d.ci_lo)!;
    const yMax = d3.max(allPoints, (d) => d.ci_hi)!;
    const yPad = (yMax - yMin) * 0.12;

    const xScale = d3
      .scaleLinear()
      .domain([tauExtent[0] - 0.5, tauExtent[1] + 0.5])
      .range([0, innerW]);

    const yScale = d3
      .scaleLinear()
      .domain([yMin - yPad, yMax + yPad])
      .nice()
      .range([innerH, 0]);

    // --- Grid lines ---
    const yTicks = yScale.ticks(6);
    g.selectAll('.grid-line')
      .data(yTicks)
      .join('line')
      .attr('class', 'grid-line')
      .attr('x1', 0)
      .attr('x2', innerW)
      .attr('y1', (d) => yScale(d))
      .attr('y2', (d) => yScale(d))
      .attr('stroke', colorBorder)
      .attr('stroke-opacity', 0.4)
      .attr('stroke-dasharray', '2,3');

    // --- Zero reference line (y = 0) ---
    if (yScale.domain()[0] <= 0 && yScale.domain()[1] >= 0) {
      g.append('line')
        .attr('x1', 0)
        .attr('x2', innerW)
        .attr('y1', yScale(0))
        .attr('y2', yScale(0))
        .attr('stroke', colorTextSecondary)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '6,4');
    }

    // --- Treatment cutoff line (tau = -0.5) ---
    g.append('line')
      .attr('x1', xScale(-0.5))
      .attr('x2', xScale(-0.5))
      .attr('y1', 0)
      .attr('y2', innerH)
      .attr('stroke', colorNegative)
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '6,4')
      .attr('stroke-opacity', 0.7);

    // "Pre" and "Post" labels
    g.append('text')
      .attr('x', xScale(-0.5) - 8)
      .attr('y', 12)
      .attr('text-anchor', 'end')
      .attr('fill', colorTextSecondary)
      .attr('font-size', '10px')
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .text('Pre');

    g.append('text')
      .attr('x', xScale(-0.5) + 8)
      .attr('y', 12)
      .attr('text-anchor', 'start')
      .attr('fill', colorTextSecondary)
      .attr('font-size', '10px')
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .text('Post');

    // --- Axes ---
    const xAxis = d3
      .axisBottom(xScale)
      .tickValues(allPoints.map((d) => d.tau).filter((v, i, a) => a.indexOf(v) === i))
      .tickFormat(d3.format('d'));

    const yAxis = d3
      .axisLeft(yScale)
      .ticks(6)
      .tickFormat(d3.format('.3f'));

    const xAxisGroup = g
      .append('g')
      .attr('transform', `translate(0,${innerH})`)
      .call(xAxis);

    xAxisGroup
      .selectAll('text')
      .attr('fill', colorText)
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', '11px');
    xAxisGroup.selectAll('line').attr('stroke', colorBorder);
    xAxisGroup.select('.domain').attr('stroke', colorBorder);

    const yAxisGroup = g.append('g').call(yAxis);

    yAxisGroup
      .selectAll('text')
      .attr('fill', colorText)
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', '11px');
    yAxisGroup.selectAll('line').attr('stroke', colorBorder);
    yAxisGroup.select('.domain').attr('stroke', colorBorder);

    // --- Axis labels ---
    g.append('text')
      .attr('x', innerW / 2)
      .attr('y', innerH + 42)
      .attr('text-anchor', 'middle')
      .attr('fill', colorTextSecondary)
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .attr('font-size', '12px')
      .text('Years Relative to LOMR Effective Date');

    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -innerH / 2)
      .attr('y', -58)
      .attr('text-anchor', 'middle')
      .attr('fill', colorTextSecondary)
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .attr('font-size', '12px')
      .text(y_label);

    // ----------------------------------------------------------
    // Render a single series (CI band + error bars + dots)
    // ----------------------------------------------------------
    const renderSeries = (
      data: EventStudyPoint[],
      color: string,
      offset: number,
    ) => {
      const sorted = [...data].sort((a, b) => a.tau - b.tau);

      // Error bars with caps
      const hasMultiple = isTwoSeries || isMultiSeries;
      const capWidth = hasMultiple ? 4 : 6;

      g.selectAll(null)
        .data(data)
        .join('g')
        .each(function (d) {
          const el = d3.select(this);
          const cx = xScale(d.tau + offset);

          // Vertical stem
          el.append('line')
            .attr('x1', cx)
            .attr('x2', cx)
            .attr('y1', yScale(d.ci_lo))
            .attr('y2', yScale(d.ci_hi))
            .attr('stroke', color)
            .attr('stroke-width', 1.5)
            .attr('stroke-opacity', 0.7);

          // Bottom cap
          el.append('line')
            .attr('x1', cx - capWidth)
            .attr('x2', cx + capWidth)
            .attr('y1', yScale(d.ci_lo))
            .attr('y2', yScale(d.ci_lo))
            .attr('stroke', color)
            .attr('stroke-width', 1.5)
            .attr('stroke-opacity', 0.7);

          // Top cap
          el.append('line')
            .attr('x1', cx - capWidth)
            .attr('x2', cx + capWidth)
            .attr('y1', yScale(d.ci_hi))
            .attr('y2', yScale(d.ci_hi))
            .attr('stroke', color)
            .attr('stroke-width', 1.5)
            .attr('stroke-opacity', 0.7);
        });

      // Connecting line through point estimates
      const line = d3
        .line<EventStudyPoint>()
        .x((d) => xScale(d.tau + offset))
        .y((d) => yScale(d.coef))
        .curve(d3.curveMonotoneX);

      g.append('path')
        .datum(sorted)
        .attr('d', line)
        .attr('fill', 'none')
        .attr('stroke', color)
        .attr('stroke-width', 2);

      // Point markers
      g.selectAll(null)
        .data(data)
        .join('circle')
        .attr('cx', (d) => xScale(d.tau + offset))
        .attr('cy', (d) => yScale(d.coef))
        .attr('r', hasMultiple ? 4 : 5)
        .attr('fill', color)
        .attr('stroke', colorSurface)
        .attr('stroke-width', 1.5)
        .attr('cursor', 'pointer')
        .on('mouseenter', function (event: MouseEvent, d: EventStudyPoint) {
          d3.select(this)
            .transition()
            .duration(120)
            .attr('r', hasMultiple ? 6 : 7);

          const seriesLabel =
            isMultiSeries && allSeries
              ? allSeries.find((s) => s.color === color)?.label ?? null
              : isTwoSeries && seriesLabels
                ? color === colorAccent
                  ? seriesLabels[0]
                  : seriesLabels[1]
                : null;

          const tooltipEl = d3.select(tooltip);
          tooltipEl
            .style('opacity', '1')
            .style('pointer-events', 'auto')
            .html(
              `<div style="font-family: Inter, system-ui, sans-serif; font-size: 12px; line-height: 1.6;">` +
                (seriesLabel
                  ? `<div style="font-weight: 600; margin-bottom: 2px; color: ${color};">${seriesLabel}</div>`
                  : '') +
                `<div style="color: ${colorTextSecondary};">\u03C4 = <span style="font-family: JetBrains Mono, monospace; color: ${colorText};">${d.tau}</span></div>` +
                `<div style="color: ${colorTextSecondary};">Coefficient: <span style="font-family: JetBrains Mono, monospace; color: ${colorText};">${d.coef.toFixed(4)}</span></div>` +
                `<div style="color: ${colorTextSecondary};">SE: <span style="font-family: JetBrains Mono, monospace; color: ${colorText};">${d.se.toFixed(4)}</span></div>` +
                `<div style="color: ${colorTextSecondary};">95% CI: <span style="font-family: JetBrains Mono, monospace; color: ${colorText};">[${d.ci_lo.toFixed(4)}, ${d.ci_hi.toFixed(4)}]</span></div>` +
                `<div style="margin-top: 3px; font-weight: 500; color: ${
                  Math.abs(d.coef / d.se) > 1.96 ? colorAccent : colorTextSecondary
                };">${significanceLabel(d.coef, d.se)}</div>` +
                `</div>`,
            );

          // Position tooltip near the point
          const svgRect = svgRef.current!.getBoundingClientRect();
          const containerRect = containerRef.current!.getBoundingClientRect();
          const px = event.clientX - containerRect.left;
          const py = event.clientY - containerRect.top;

          // Flip left if near right edge
          const tooltipWidth = 220;
          const flipX = px + tooltipWidth + 16 > containerRect.width;

          tooltipEl
            .style('left', flipX ? `${px - tooltipWidth - 8}px` : `${px + 16}px`)
            .style('top', `${py - 20}px`);
        })
        .on('mouseleave', function () {
          d3.select(this)
            .transition()
            .duration(120)
            .attr('r', hasMultiple ? 4 : 5);

          d3.select(tooltip)
            .style('opacity', '0')
            .style('pointer-events', 'none');
        });
    };

    // --- Render series ---
    if (isMultiSeries && allSeries) {
      // N-series mode: jitter offsets spread evenly
      const n = allSeries.length;
      const spread = 0.3; // total spread across tau
      const offsets = allSeries.map((_, i) => -spread / 2 + (spread / (n - 1)) * i);

      allSeries.forEach((series, idx) => {
        const seriesPoints: EventStudyPoint[] = series.points.map((p) => ({
          ...p,
          se: p.coef === 0 ? 0 : (p.ci_hi - p.ci_lo) / (2 * 1.96),
        }));
        renderSeries(seriesPoints, series.color, offsets[idx]);
      });

      // Legend for N series
      const legendX = innerW - 160;
      const legendY = 6;
      const rowH = 18;
      const legendG = g.append('g').attr('transform', `translate(${legendX},${legendY})`);

      legendG
        .append('rect')
        .attr('x', -10)
        .attr('y', -6)
        .attr('width', 170)
        .attr('height', n * rowH + 10)
        .attr('rx', 4)
        .attr('fill', colorSurface)
        .attr('stroke', colorBorder)
        .attr('stroke-width', 1)
        .attr('fill-opacity', 0.9);

      allSeries.forEach((series, i) => {
        legendG
          .append('circle')
          .attr('cx', 6)
          .attr('cy', 8 + i * rowH)
          .attr('r', 4)
          .attr('fill', series.color);

        legendG
          .append('text')
          .attr('x', 18)
          .attr('y', 12 + i * rowH)
          .attr('fill', colorText)
          .attr('font-family', 'Inter, system-ui, sans-serif')
          .attr('font-size', '11px')
          .text(series.label);
      });
    } else if (isTwoSeries && secondSeries) {
      renderSeries(points, colorAccent, -TAU_OFFSET);
      renderSeries(secondSeries, colorSecond, TAU_OFFSET);

      // Legend
      const legendX = innerW - 150;
      const legendY = 6;
      const legendG = g.append('g').attr('transform', `translate(${legendX},${legendY})`);

      legendG
        .append('rect')
        .attr('x', -10)
        .attr('y', -6)
        .attr('width', 160)
        .attr('height', 48)
        .attr('rx', 4)
        .attr('fill', colorSurface)
        .attr('stroke', colorBorder)
        .attr('stroke-width', 1)
        .attr('fill-opacity', 0.9);

      // Series 1
      legendG
        .append('circle')
        .attr('cx', 6)
        .attr('cy', 10)
        .attr('r', 4)
        .attr('fill', colorAccent);

      legendG
        .append('text')
        .attr('x', 18)
        .attr('y', 14)
        .attr('fill', colorText)
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .attr('font-size', '11px')
        .text(seriesLabels?.[0] ?? 'Series 1');

      // Series 2
      legendG
        .append('circle')
        .attr('cx', 6)
        .attr('cy', 30)
        .attr('r', 4)
        .attr('fill', colorSecond);

      legendG
        .append('text')
        .attr('x', 18)
        .attr('y', 34)
        .attr('fill', colorText)
        .attr('font-family', 'Inter, system-ui, sans-serif')
        .attr('font-size', '11px')
        .text(seriesLabels?.[1] ?? 'Series 2');
    } else {
      renderSeries(points, colorAccent, 0);
    }

    // --- Reference period marker ---
    const refPoint = isMultiSeries ? null : points.find((p) => p.tau === reference_tau);
    if (refPoint) {
      const refOffset = isTwoSeries ? -TAU_OFFSET : 0;
      g.append('circle')
        .attr('cx', xScale(refPoint.tau + refOffset))
        .attr('cy', yScale(refPoint.coef))
        .attr('r', isTwoSeries ? 6 : 8)
        .attr('fill', 'none')
        .attr('stroke', colorTextSecondary)
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '3,2');
    }
  }, [
    dimensions,
    points,
    secondSeries,
    seriesLabels,
    seriesColors,
    allSeries,
    y_label,
    reference_tau,
    getCSSVar,
    significanceLabel,
    theme,
  ]);

  return (
    <div style={{ width: '100%' }}>
      {/* Title */}
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

      {/* Chart container */}
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
            height: dimensions.height || 'auto',
            overflow: 'visible',
          }}
        />

        {/* Tooltip */}
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

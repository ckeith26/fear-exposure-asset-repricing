'use client';

import { useRef, useEffect, useCallback, useState } from 'react';
import * as d3 from 'd3';

interface TrendPoint {
  year: number;
  value: number;
}

interface TrendSeries {
  label: string;
  points: TrendPoint[];
}

interface TrendsChartProps {
  title: string;
  y_label: string;
  x_label: string;
  series: TrendSeries[];
}

const MARGIN = { top: 20, right: 30, bottom: 50, left: 72 };

export default function TrendsChart({ title, y_label, x_label, series }: TrendsChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [theme, setTheme] = useState('dark');

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
        const { width } = entry.contentRect;
        setDimensions({ width, height: Math.min(width * 0.55, 480) });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const getCSSVar = useCallback((name: string, fallback: string): string => {
    if (typeof window === 'undefined') return fallback;
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  }, []);

  useEffect(() => {
    const svg = svgRef.current;
    const tooltip = tooltipRef.current;
    if (!svg || !tooltip || dimensions.width === 0) return;

    const { width, height } = dimensions;
    const innerW = width - MARGIN.left - MARGIN.right;
    const innerH = height - MARGIN.top - MARGIN.bottom;

    const colorAccent = getCSSVar('--color-accent', '#3b82f6');
    const colorNegative = getCSSVar('--color-negative', '#ef4444');
    const colorText = getCSSVar('--color-text', '#e4e4e7');
    const colorTextSecondary = getCSSVar('--color-text-secondary', '#9ca3af');
    const colorBorder = getCSSVar('--color-border', '#2a2d3a');
    const colorSurface = getCSSVar('--color-surface', '#1a1d27');
    const seriesColors = [colorNegative, colorAccent];

    const root = d3.select(svg);
    root.selectAll('*').remove();
    root.attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
    const g = root.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

    const allPoints = series.flatMap(s => s.points);
    const xExtent = d3.extent(allPoints, d => d.year) as [number, number];
    const yMin = d3.min(allPoints, d => d.value)!;
    const yMax = d3.max(allPoints, d => d.value)!;
    const yPad = (yMax - yMin) * 0.1;

    const xScale = d3.scaleLinear().domain(xExtent).range([0, innerW]);
    const yScale = d3.scaleLinear().domain([yMin - yPad, yMax + yPad]).nice().range([innerH, 0]);

    // Grid
    yScale.ticks(6).forEach(t => {
      g.append('line').attr('x1', 0).attr('x2', innerW)
        .attr('y1', yScale(t)).attr('y2', yScale(t))
        .attr('stroke', colorBorder).attr('stroke-opacity', 0.4).attr('stroke-dasharray', '2,3');
    });

    // Axes
    const xAxis = d3.axisBottom(xScale).ticks(7).tickFormat(d3.format('d'));
    const yAxis = d3.axisLeft(yScale).ticks(6).tickFormat(d => `$${d3.format(',.0f')(d as number)}k`);

    const xG = g.append('g').attr('transform', `translate(0,${innerH})`).call(xAxis);
    xG.selectAll('text').attr('fill', colorText).attr('font-family', 'JetBrains Mono, monospace').attr('font-size', '11px');
    xG.selectAll('line').attr('stroke', colorBorder);
    xG.select('.domain').attr('stroke', colorBorder);

    const yG = g.append('g').call(yAxis);
    yG.selectAll('text').attr('fill', colorText).attr('font-family', 'JetBrains Mono, monospace').attr('font-size', '11px');
    yG.selectAll('line').attr('stroke', colorBorder);
    yG.select('.domain').attr('stroke', colorBorder);

    // Axis labels
    g.append('text').attr('x', innerW / 2).attr('y', innerH + 42).attr('text-anchor', 'middle')
      .attr('fill', colorTextSecondary).attr('font-family', 'Inter, system-ui, sans-serif').attr('font-size', '12px').text(x_label);
    g.append('text').attr('transform', 'rotate(-90)').attr('x', -innerH / 2).attr('y', -58).attr('text-anchor', 'middle')
      .attr('fill', colorTextSecondary).attr('font-family', 'Inter, system-ui, sans-serif').attr('font-size', '12px').text(y_label);

    // Lines + dots
    series.forEach((s, si) => {
      const color = seriesColors[si % seriesColors.length];
      const sorted = [...s.points].sort((a, b) => a.year - b.year);

      const line = d3.line<TrendPoint>().x(d => xScale(d.year)).y(d => yScale(d.value)).curve(d3.curveMonotoneX);
      g.append('path').datum(sorted).attr('d', line).attr('fill', 'none').attr('stroke', color).attr('stroke-width', 2);

      g.selectAll(null).data(sorted).join('circle')
        .attr('cx', d => xScale(d.year)).attr('cy', d => yScale(d.value))
        .attr('r', 4).attr('fill', color).attr('stroke', colorSurface).attr('stroke-width', 1.5).attr('cursor', 'pointer')
        .on('mouseenter', function (event: MouseEvent, d: TrendPoint) {
          d3.select(this).transition().duration(120).attr('r', 6);
          const tooltipEl = d3.select(tooltip);
          tooltipEl.style('opacity', '1').style('pointer-events', 'auto')
            .html(`<div style="font-family:Inter,system-ui,sans-serif;font-size:12px;line-height:1.6;">` +
              `<div style="font-weight:600;color:${color};">${s.label}</div>` +
              `<div style="color:${colorTextSecondary};">Year: <span style="font-family:JetBrains Mono,monospace;color:${colorText};">${d.year}</span></div>` +
              `<div style="color:${colorTextSecondary};">ZHVI: <span style="font-family:JetBrains Mono,monospace;color:${colorText};">$${d.value.toFixed(1)}k</span></div></div>`);
          const containerRect = containerRef.current!.getBoundingClientRect();
          const px = event.clientX - containerRect.left;
          const py = event.clientY - containerRect.top;
          const flipX = px + 220 > containerRect.width;
          tooltipEl.style('left', flipX ? `${px - 220}px` : `${px + 16}px`).style('top', `${py - 20}px`);
        })
        .on('mouseleave', function () {
          d3.select(this).transition().duration(120).attr('r', 4);
          d3.select(tooltip).style('opacity', '0').style('pointer-events', 'none');
        });
    });

    // Legend
    const legendG = g.append('g').attr('transform', `translate(${innerW - 200},${6})`);
    legendG.append('rect').attr('x', -10).attr('y', -6).attr('width', 210).attr('height', series.length * 20 + 10).attr('rx', 4)
      .attr('fill', colorSurface).attr('stroke', colorBorder).attr('fill-opacity', 0.9);
    series.forEach((s, i) => {
      legendG.append('circle').attr('cx', 6).attr('cy', 8 + i * 20).attr('r', 4).attr('fill', seriesColors[i % seriesColors.length]);
      legendG.append('text').attr('x', 18).attr('y', 12 + i * 20).attr('fill', colorText)
        .attr('font-family', 'Inter, system-ui, sans-serif').attr('font-size', '11px').text(s.label);
    });
  }, [dimensions, series, y_label, x_label, getCSSVar, theme]);

  return (
    <div style={{ width: '100%' }}>
      <h3 style={{ fontFamily: 'Inter, system-ui, sans-serif', fontSize: '15px', fontWeight: 600, color: 'var(--color-text)', marginBottom: '12px', textAlign: 'center' }}>
        {title}
      </h3>
      <div ref={containerRef} style={{ position: 'relative', width: '100%', minHeight: '200px' }}>
        <svg ref={svgRef} style={{ display: 'block', width: '100%', height: dimensions.height || 'auto', overflow: 'visible' }} />
        <div ref={tooltipRef} style={{ position: 'absolute', top: 0, left: 0, opacity: 0, pointerEvents: 'none', background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '6px', padding: '10px 14px', boxShadow: '0 4px 20px rgba(0,0,0,0.4)', zIndex: 50, transition: 'opacity 0.15s ease', maxWidth: '240px' }} />
      </div>
    </div>
  );
}

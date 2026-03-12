'use client';

import { useRef, useEffect, useCallback, useState } from 'react';
import * as d3 from 'd3';

interface BarData {
  year: number;
  count: number;
}

interface BarChartProps {
  title: string;
  y_label: string;
  x_label: string;
  bars: BarData[];
}

const MARGIN = { top: 20, right: 30, bottom: 65, left: 60 };

export default function BarChart({ title, y_label, x_label, bars }: BarChartProps) {
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
        setDimensions({ width, height: Math.min(width * 0.5, 400) });
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
    const colorText = getCSSVar('--color-text', '#e4e4e7');
    const colorTextSecondary = getCSSVar('--color-text-secondary', '#9ca3af');
    const colorBorder = getCSSVar('--color-border', '#2a2d3a');
    const colorSurface = getCSSVar('--color-surface', '#1a1d27');

    const root = d3.select(svg);
    root.selectAll('*').remove();
    root.attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
    const g = root.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

    const xScale = d3.scaleBand()
      .domain(bars.map(d => String(d.year)))
      .range([0, innerW])
      .padding(0.15);

    const yMax = d3.max(bars, d => d.count)!;
    const yScale = d3.scaleLinear().domain([0, yMax * 1.1]).nice().range([innerH, 0]);

    // Grid
    yScale.ticks(6).forEach(t => {
      g.append('line').attr('x1', 0).attr('x2', innerW)
        .attr('y1', yScale(t)).attr('y2', yScale(t))
        .attr('stroke', colorBorder).attr('stroke-opacity', 0.4).attr('stroke-dasharray', '2,3');
    });

    // Axes
    const xG = g.append('g').attr('transform', `translate(0,${innerH})`).call(d3.axisBottom(xScale));
    xG.selectAll('text').attr('fill', colorText).attr('font-family', 'JetBrains Mono, monospace').attr('font-size', '11px')
      .attr('text-anchor', 'end').attr('transform', 'rotate(-45)').attr('dx', '-0.5em').attr('dy', '0.25em');
    xG.selectAll('line').attr('stroke', colorBorder);
    xG.select('.domain').attr('stroke', colorBorder);

    const yG = g.append('g').call(d3.axisLeft(yScale).ticks(6));
    yG.selectAll('text').attr('fill', colorText).attr('font-family', 'JetBrains Mono, monospace').attr('font-size', '11px');
    yG.selectAll('line').attr('stroke', colorBorder);
    yG.select('.domain').attr('stroke', colorBorder);

    // Axis labels
    g.append('text').attr('x', innerW / 2).attr('y', innerH + 58).attr('text-anchor', 'middle')
      .attr('fill', colorTextSecondary).attr('font-family', 'Inter, system-ui, sans-serif').attr('font-size', '12px').text(x_label);
    g.append('text').attr('transform', 'rotate(-90)').attr('x', -innerH / 2).attr('y', -46).attr('text-anchor', 'middle')
      .attr('fill', colorTextSecondary).attr('font-family', 'Inter, system-ui, sans-serif').attr('font-size', '12px').text(y_label);

    // Bars
    g.selectAll('.bar').data(bars).join('rect')
      .attr('x', d => xScale(String(d.year))!)
      .attr('y', d => yScale(d.count))
      .attr('width', xScale.bandwidth())
      .attr('height', d => innerH - yScale(d.count))
      .attr('fill', colorAccent)
      .attr('fill-opacity', 0.7)
      .attr('rx', 2)
      .attr('cursor', 'pointer')
      .on('mouseenter', function (event: MouseEvent, d: BarData) {
        d3.select(this).attr('fill-opacity', 1);
        const tooltipEl = d3.select(tooltip);
        tooltipEl.style('opacity', '1').style('pointer-events', 'auto')
          .html(`<div style="font-family:Inter,system-ui,sans-serif;font-size:12px;line-height:1.6;">` +
            `<div style="color:${colorTextSecondary};">Year: <span style="font-family:JetBrains Mono,monospace;color:${colorText};">${d.year}</span></div>` +
            `<div style="color:${colorTextSecondary};">Zip codes: <span style="font-family:JetBrains Mono,monospace;color:${colorText};">${d.count}</span></div></div>`);
        const containerRect = containerRef.current!.getBoundingClientRect();
        const px = event.clientX - containerRect.left;
        const py = event.clientY - containerRect.top;
        tooltipEl.style('left', `${px + 16}px`).style('top', `${py - 20}px`);
      })
      .on('mouseleave', function () {
        d3.select(this).attr('fill-opacity', 0.7);
        d3.select(tooltip).style('opacity', '0').style('pointer-events', 'none');
      });
  }, [dimensions, bars, y_label, x_label, getCSSVar, theme]);

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

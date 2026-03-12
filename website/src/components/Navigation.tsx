'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import ThemeToggle from './ThemeToggle';

const NAV_LINKS = [
  { label: 'Research Question', href: '#research-question' },
  { label: 'Data & Sample', href: '#data-sample' },
  { label: 'Sources', href: '#data-sources' },
  { label: 'Methodology', href: '#methodology' },
  { label: 'Results', href: '#results' },
  { label: 'Robustness', href: '#robustness' },
  { label: 'Limitations', href: '#limitations' },
  { label: 'Data', href: '#data-download' },
  { label: 'About', href: '#about' },
];

export default function Navigation() {
  const [activeSection, setActiveSection] = useState<string>('');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sectionIds = NAV_LINKS.map((link) => link.href.slice(1));
    const elements = sectionIds
      .map((id) => document.getElementById(id))
      .filter(Boolean) as HTMLElement[];

    if (elements.length === 0) return;

    const visibleSet = new Set<string>();

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            visibleSet.add(entry.target.id);
          } else {
            visibleSet.delete(entry.target.id);
          }
        });

        const topmost = sectionIds.find((id) => visibleSet.has(id));
        if (topmost) {
          setActiveSection(topmost);
        }
      },
      {
        rootMargin: '-48px 0px -40% 0px',
        threshold: 0,
      }
    );

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  // Close menu on click outside
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
      e.preventDefault();
      const id = href.slice(1);
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
      setMenuOpen(false);
    },
    []
  );

  const scrollToTop = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    setMenuOpen(false);
  }, []);

  return (
    <div ref={menuRef} className="fixed top-0 left-0 right-0 z-50">
      <nav
        className="h-12 flex items-center px-4 md:px-6"
        style={{
          backgroundColor: 'color-mix(in srgb, var(--color-bg) 80%, transparent)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          borderBottom: menuOpen ? 'none' : '1px solid var(--color-border)',
        }}
      >
        {/* Left: Logo */}
        <a
          href="#"
          onClick={scrollToTop}
          className="font-mono font-bold text-sm tracking-wider mr-6 shrink-0 transition-colors duration-200"
          style={{ color: 'var(--color-text)' }}
        >
          FEAR
        </a>

        {/* Center: Section links — desktop */}
        <div className="hidden sm:flex items-center gap-1 overflow-x-auto hide-scrollbar flex-1">
          {NAV_LINKS.map((link) => {
            const isActive = activeSection === link.href.slice(1);
            return (
              <a
                key={link.href}
                href={link.href}
                onClick={(e) => handleClick(e, link.href)}
                className="whitespace-nowrap px-2 py-1 text-xs rounded transition-colors duration-200"
                style={{
                  color: isActive
                    ? 'var(--color-accent)'
                    : 'var(--color-text-secondary)',
                  backgroundColor: isActive
                    ? 'color-mix(in srgb, var(--color-accent) 10%, transparent)'
                    : 'transparent',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.color = 'var(--color-text)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.color = 'var(--color-text-secondary)';
                  }
                }}
              >
                {link.label}
              </a>
            );
          })}
        </div>

        {/* Mobile: spacer + theme toggle + hamburger */}
        <div className="flex-1 sm:hidden" />

        {/* Right: Theme toggle */}
        <div className="shrink-0 sm:ml-4">
          <ThemeToggle />
        </div>

        <button
          className="sm:hidden ml-2 w-8 h-8 flex items-center justify-center rounded transition-colors"
          style={{ color: 'var(--color-text)' }}
          onClick={() => setMenuOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {menuOpen ? (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M4 4l10 10M14 4L4 14" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M2 5h14M2 9h14M2 13h14" />
            </svg>
          )}
        </button>
      </nav>

      {/* Mobile dropdown menu */}
      <div
        ref={contentRef}
        className="sm:hidden overflow-hidden transition-all duration-300 ease-in-out"
        style={{
          maxHeight: menuOpen ? `${NAV_LINKS.length * 44 + 16}px` : '0px',
          opacity: menuOpen ? 1 : 0,
          backgroundColor: 'color-mix(in srgb, var(--color-bg) 95%, transparent)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          borderBottom: menuOpen ? '1px solid var(--color-border)' : 'none',
        }}
      >
        <div className="flex flex-col py-2 px-4">
          {NAV_LINKS.map((link) => {
            const isActive = activeSection === link.href.slice(1);
            return (
              <a
                key={link.href}
                href={link.href}
                onClick={(e) => handleClick(e, link.href)}
                className="py-2.5 px-3 text-sm rounded transition-colors duration-200"
                style={{
                  color: isActive
                    ? 'var(--color-accent)'
                    : 'var(--color-text-secondary)',
                  backgroundColor: isActive
                    ? 'color-mix(in srgb, var(--color-accent) 10%, transparent)'
                    : 'transparent',
                }}
              >
                {link.label}
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
}

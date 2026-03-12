'use client';

/**
 * DownloadCard - renders a single dataset card for the data download section.
 *
 * Each card displays the dataset name, a short description, the file format
 * (as a small badge), approximate file size, and a styled download button.
 *
 * Styling uses CSS variables from globals.css so it adapts to light/dark theme.
 */

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  name: string;
  description: string;
  format: string;
  size: string;
  href: string;
  external?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DownloadCard({ name, description, format, size, href, external }: Props) {
  return (
    <div
      className="flex flex-col justify-between rounded-lg border p-5"
      style={{
        background: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      {/* Top section: name + description */}
      <div className="mb-4">
        <h3
          className="font-sans text-base font-semibold leading-snug"
          style={{ color: 'var(--color-text)' }}
        >
          {name}
        </h3>
        <p
          className="mt-1 line-clamp-2 font-sans text-sm leading-relaxed"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {description}
        </p>
      </div>

      {/* Bottom row: format badge, size, download button */}
      <div className="flex items-center gap-3">
        {/* Format badge */}
        <span
          className="inline-block rounded px-2 py-0.5 font-mono text-xs font-medium uppercase tracking-wide"
          style={{
            color: 'var(--color-accent)',
            background: 'color-mix(in srgb, var(--color-accent) 12%, transparent)',
            border: '1px solid color-mix(in srgb, var(--color-accent) 30%, transparent)',
          }}
        >
          {format}
        </span>

        {/* File size */}
        <span
          className="font-mono text-xs"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {size}
        </span>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Download button */}
        <a
          href={href}
          {...(external ? { target: "_blank", rel: "noopener noreferrer" } : { download: true })}
          className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 font-sans text-sm font-medium transition-colors duration-150"
          style={{
            color: 'var(--color-accent)',
            borderColor: 'var(--color-accent)',
            background: 'transparent',
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget;
            el.style.background = 'var(--color-accent)';
            el.style.color = '#ffffff';
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget;
            el.style.background = 'transparent';
            el.style.color = 'var(--color-accent)';
          }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            {external ? (
              <>
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </>
            ) : (
              <>
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </>
            )}
          </svg>
          {external ? "GitHub" : "Download"}
        </a>
      </div>
    </div>
  );
}

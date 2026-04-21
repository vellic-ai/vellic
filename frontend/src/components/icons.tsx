import * as React from "react";

interface IconProps {
  size?: number;
  className?: string;
}

function Icon({
  d,
  size = 16,
  stroke = 1.6,
  fill = "none",
  className,
}: {
  d: React.ReactNode;
  size?: number;
  stroke?: number;
  fill?: string;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill}
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {d}
    </svg>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export const Icons = {
  dashboard: ({ size = 16 }: IconProps) => (
    <Icon size={size} d={<path d="M3 12l9-8 9 8M5 10v10h4v-6h6v6h4V10" />} />
  ),
  deliveries: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M3 7l9-4 9 4-9 4-9-4z" />
          <path d="M3 12l9 4 9-4" />
          <path d="M3 17l9 4 9-4" />
        </>
      }
    />
  ),
  jobs: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        </>
      }
    />
  ),
  llm: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M12 2a4 4 0 00-4 4v2a4 4 0 008 0V6a4 4 0 00-4-4z" />
          <path d="M5 11v1a7 7 0 0014 0v-1" />
          <path d="M12 19v3" />
        </>
      }
    />
  ),
  repos: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M4 5a2 2 0 012-2h10l4 4v12a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" />
          <path d="M8 13h8M8 17h5" />
        </>
      }
    />
  ),
  webhook: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <circle cx="6" cy="18" r="3" />
          <circle cx="18" cy="18" r="3" />
          <circle cx="12" cy="6" r="3" />
          <path d="M12 9v4M10.5 14l-3 2M13.5 14l3 2" />
        </>
      }
    />
  ),
  logout: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M15 4h4a1 1 0 011 1v14a1 1 0 01-1 1h-4" />
          <path d="M10 8l-4 4 4 4M6 12h10" />
        </>
      }
    />
  ),
  copy: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <rect x="9" y="9" width="11" height="11" rx="2" />
          <path d="M5 15V5a2 2 0 012-2h10" />
        </>
      }
    />
  ),
  eye: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
          <circle cx="12" cy="12" r="3" />
        </>
      }
    />
  ),
  eyeOff: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M3 3l18 18" />
          <path d="M10.6 6.2A9.9 9.9 0 0112 6c6.5 0 10 6 10 6a15 15 0 01-3 3.6M6.4 6.4A15 15 0 002 12s3.5 6 10 6a9.9 9.9 0 003.4-.6" />
          <path d="M9.9 9.9a3 3 0 104.2 4.2" />
        </>
      }
    />
  ),
  refresh: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M21 12a9 9 0 11-3-6.7" />
          <path d="M21 4v5h-5" />
        </>
      }
    />
  ),
  chevronDown: ({ size = 16 }: IconProps) => (
    <Icon size={size} d={<path d="M6 9l6 6 6-6" />} />
  ),
  chevronRight: ({ size = 16 }: IconProps) => (
    <Icon size={size} d={<path d="M9 6l6 6-6 6" />} />
  ),
  chevronLeft: ({ size = 16 }: IconProps) => (
    <Icon size={size} d={<path d="M15 6l-6 6 6 6" />} />
  ),
  x: ({ size = 16 }: IconProps) => (
    <Icon size={size} d={<path d="M6 6l12 12M18 6L6 18" />} />
  ),
  check: ({ size = 16 }: IconProps) => (
    <Icon size={size} d={<path d="M5 12l5 5L20 7" />} />
  ),
  plus: ({ size = 16 }: IconProps) => (
    <Icon size={size} d={<path d="M12 5v14M5 12h14" />} />
  ),
  trash: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M4 7h16" />
          <path d="M9 7V4h6v3" />
          <path d="M6 7l1 13a2 2 0 002 2h6a2 2 0 002-2l1-13" />
        </>
      }
    />
  ),
  warn: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M12 3l10 18H2L12 3z" />
          <path d="M12 10v5M12 18v.1" />
        </>
      }
    />
  ),
  info: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 11v5M12 8v.1" />
        </>
      }
    />
  ),
  search: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <circle cx="11" cy="11" r="7" />
          <path d="M21 21l-4.3-4.3" />
        </>
      }
    />
  ),
  external: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M14 4h6v6" />
          <path d="M20 4l-9 9" />
          <path d="M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5" />
        </>
      }
    />
  ),
  menu: ({ size = 16 }: IconProps) => (
    <Icon size={size} d={<path d="M4 7h16M4 12h16M4 17h16" />} />
  ),
  flags: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M4 4v16" />
          <path d="M4 4h12l-3 4 3 4H4" />
        </>
      }
    />
  ),
  plugin: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M12 2l9 4.5v9L12 20l-9-4.5v-9L12 2z" />
          <path d="M12 8v8M8 10l4-2 4 2" />
        </>
      }
    />
  ),
  mcpServer: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <rect x="3" y="4" width="18" height="7" rx="2" />
          <rect x="3" y="13" width="18" height="7" rx="2" />
          <circle cx="7" cy="7.5" r="1" fill="currentColor" stroke="none" />
          <circle cx="7" cy="16.5" r="1" fill="currentColor" stroke="none" />
        </>
      }
    />
  ),
  extensions: ({ size = 16 }: IconProps) => (
    <Icon
      size={size}
      d={
        <>
          <path d="M12 2l3 3h4v4l3 3-3 3v4h-4l-3 3-3-3H5v-4l-3-3 3-3V5h4z" />
          <circle cx="12" cy="12" r="2" />
        </>
      }
    />
  ),
  github: ({ size = 16, className }: IconProps) => (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 2a10 10 0 00-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.54 2.36 1.09 2.94.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02a9.5 9.5 0 015 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0012 2z" />
    </svg>
  ),
  gitlab: ({ size = 16, className }: IconProps) => (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 21l-3.5-11H15.5L12 21zM4 10L2 16l10 5L4 10zM20 10l2 6-10 5 8-11zM8.5 10H4l2-6 2.5 6zM15.5 10H20l-2-6-2.5 6z" />
    </svg>
  ),
};

export function Spinner({ size = 14, className }: { size?: number; className?: string }) {
  return (
    <span
      className={className}
      style={{
        display: "inline-block",
        width: size,
        height: size,
        border: "2px solid rgba(255,255,255,.15)",
        borderTopColor: "currentColor",
        borderRadius: "50%",
        animation: "spin .7s linear infinite",
        verticalAlign: "middle",
        flexShrink: 0,
      }}
      aria-hidden="true"
    />
  );
}

export function Wordmark({ size = 20 }: { size?: number }) {
  return (
    <div className="flex items-center gap-2">
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <defs>
          <linearGradient id="vellicG" x1="0" y1="24" x2="24" y2="0">
            <stop offset="0%" stopColor="#4b7cff" />
            <stop offset="100%" stopColor="#8c7cff" />
          </linearGradient>
        </defs>
        <path
          d="M4 21L12 3L20 21"
          stroke="url(#vellicG)"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="font-mono text-sm font-semibold tracking-[.01em]">
        vellic <span className="text-text-muted font-normal">admin</span>
      </span>
    </div>
  );
}

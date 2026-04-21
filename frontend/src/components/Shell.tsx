import * as React from "react";
import { NavLink, useNavigate } from "react-router";
import { Icons, Wordmark } from "@/components/icons";
import { useLogout } from "@/api";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
}

interface NavSection {
  section: string;
  items: NavItem[];
}

const NAV: Array<NavItem | NavSection> = [
  { label: "Dashboard", to: "/dashboard", icon: <Icons.dashboard /> },
  {
    section: "Observe",
    items: [
      { label: "Deliveries", to: "/deliveries", icon: <Icons.deliveries /> },
      { label: "Jobs", to: "/jobs", icon: <Icons.jobs /> },
    ],
  },
  {
    section: "Settings",
    items: [
      { label: "Providers", to: "/settings", icon: <Icons.llm /> },
      { label: "Repositories", to: "/repos", icon: <Icons.repos /> },
    ],
  },
];

function SidebarNavItem({ to, icon, label }: NavItem) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2.5 h-8 mx-2 px-2.5 rounded-[6px] text-sm transition-colors duration-[120ms]",
          "border-l-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
          isActive
            ? "bg-surface-2 text-text border-l-accent font-medium"
            : "text-text-muted border-l-transparent hover:bg-surface-2/50 hover:text-text",
        )
      }
    >
      {({ isActive }) => (
        <>
          <span
            className={cn(
              "inline-flex w-4 shrink-0",
              isActive ? "text-accent" : "text-current",
            )}
          >
            {icon}
          </span>
          <span>{label}</span>
        </>
      )}
    </NavLink>
  );
}

function Sidebar({ onClose }: { onClose?: () => void }) {
  const navigate = useNavigate();
  const logout = useLogout();

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSuccess: () => navigate("/login"),
    });
  };

  return (
    <aside className="w-[220px] shrink-0 bg-surface border-r border-border h-screen flex flex-col sticky top-0">
      <div className="px-4 pt-[18px] pb-3.5 flex items-center justify-between">
        <NavLink to="/dashboard" aria-label="Dashboard">
          <Wordmark />
        </NavLink>
        {onClose && (
          <button
            onClick={onClose}
            className="inline-flex items-center justify-center w-6 h-6 rounded text-text-muted hover:text-text hover:bg-surface-2"
            aria-label="Close menu"
          >
            <Icons.x />
          </button>
        )}
      </div>

      <nav className="flex-1 pt-1 overflow-y-auto" aria-label="Main navigation">
        {NAV.map((entry, i) => {
          if ("section" in entry) {
            return (
              <div key={i} className="mt-4">
                <div className="text-[10.5px] uppercase tracking-[.08em] text-text-muted px-[18px] pb-1.5 font-medium">
                  {entry.section}
                </div>
                {entry.items.map((item) => (
                  <SidebarNavItem key={item.to} {...item} />
                ))}
              </div>
            );
          }
          return <SidebarNavItem key={entry.to} {...entry} />;
        })}
      </nav>

      <div className="border-t border-border px-4 py-3 flex items-center justify-between gap-2">
        <button
          onClick={handleLogout}
          disabled={logout.isPending}
          className="inline-flex items-center gap-1.5 text-text-muted text-sm hover:text-text transition-colors"
          aria-label="Log out"
        >
          <span className="inline-flex w-3.5">
            <Icons.logout />
          </span>
          Logout
        </button>
        <span className="font-mono text-[10.5px] text-text-muted px-1.5 py-0.5 bg-surface-2 rounded">
          v0.4.2
        </span>
      </div>
    </aside>
  );
}

interface ShellProps {
  children: React.ReactNode;
}

export function Shell({ children }: ShellProps) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const isMobile = useIsMobile();

  return (
    <div className="flex min-h-screen bg-bg">
      {!isMobile && <Sidebar />}

      {isMobile && mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 animate-fade-in"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div className="fixed top-0 left-0 h-screen z-50">
            <Sidebar onClose={() => setMobileOpen(false)} />
          </div>
        </>
      )}

      <main className="flex-1 min-w-0">
        {isMobile && (
          <div className="flex items-center gap-2.5 px-4 py-3 border-b border-border bg-surface sticky top-0 z-10">
            <button
              onClick={() => setMobileOpen(true)}
              className="inline-flex items-center justify-center w-8 h-8 rounded text-text-muted hover:text-text hover:bg-surface-2"
              aria-label="Open menu"
            >
              <Icons.menu />
            </button>
            <Wordmark size={18} />
          </div>
        )}

        <div className={cn("max-w-[1100px] mx-auto", isMobile ? "px-4 py-5" : "px-8 py-8")}>
          {children}
        </div>
      </main>
    </div>
  );
}

function useIsMobile() {
  const [mobile, setMobile] = React.useState(
    () => typeof window !== "undefined" && window.innerWidth <= 600,
  );
  React.useEffect(() => {
    const onResize = () => setMobile(window.innerWidth <= 600);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return mobile;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  extra?: React.ReactNode;
}

export function PageHeader({ title, subtitle, action, extra }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div className="min-w-0">
        <div className="flex items-center gap-2.5 flex-wrap">
          <h1 className="text-[22px] font-semibold tracking-[-0.01em] m-0">{title}</h1>
          {extra}
        </div>
        {subtitle && (
          <div className="text-text-muted text-sm mt-1">{subtitle}</div>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="bg-surface border border-border rounded p-14 text-center">
      <div className="inline-flex w-11 h-11 rounded-[10px] bg-surface-2 text-text-muted items-center justify-center mb-3.5">
        {icon}
      </div>
      <div className="text-[15px] font-medium mb-1.5">{title}</div>
      <div className="text-text-muted text-sm mb-5">{body}</div>
      {action}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-block rounded bg-surface-2 animate-shimmer",
        "bg-[linear-gradient(90deg,var(--surface-2)_25%,#2a2f44_50%,var(--surface-2)_75%)]",
        "bg-[length:400px_100%]",
        className,
      )}
    />
  );
}

interface StatusDotProps {
  status: "processed" | "failed" | "queued" | "running";
}

export function StatusDot({ status }: StatusDotProps) {
  const colors: Record<string, string> = {
    processed: "bg-success",
    failed: "bg-error",
    running: "bg-accent animate-pulse",
    queued: "bg-text-muted",
  };
  return (
    <span
      className={cn("inline-block w-1.5 h-1.5 rounded-full", colors[status] ?? "bg-text-muted")}
    />
  );
}

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastRoot } from "@/lib/toast";
import DashboardPage from "../index";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ToastRoot>{children}</ToastRoot>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("DashboardPage", () => {
  it("renders stat tile labels", () => {
    render(<DashboardPage />, { wrapper });
    expect(screen.getByText(/PRs reviewed/i)).toBeInTheDocument();
    expect(screen.getByText(/p50 latency/i)).toBeInTheDocument();
    expect(screen.getByText(/p95 latency/i)).toBeInTheDocument();
    expect(screen.getByText(/Failure rate/i)).toBeInTheDocument();
  });

  it("renders Dashboard heading", () => {
    render(<DashboardPage />, { wrapper });
    expect(screen.getByRole("heading", { name: /Dashboard/i })).toBeInTheDocument();
  });
});

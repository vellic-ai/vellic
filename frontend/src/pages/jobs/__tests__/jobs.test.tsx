import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastRoot } from "@/lib/toast";
import JobsPage from "../index";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ToastRoot>{children}</ToastRoot>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("JobsPage", () => {
  it("renders page heading", () => {
    render(<JobsPage />, { wrapper });
    expect(screen.getByRole("heading", { name: /Jobs/i })).toBeInTheDocument();
  });

  it("renders status filter", () => {
    render(<JobsPage />, { wrapper });
    expect(screen.getByLabelText(/Filter by status/i)).toBeInTheDocument();
  });

  it("renders subtitle", () => {
    render(<JobsPage />, { wrapper });
    expect(screen.getByText(/Analysis pipeline runs per PR\/MR/i)).toBeInTheDocument();
  });
});

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastRoot } from "@/lib/toast";
import DeliveriesPage from "../index";

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

describe("DeliveriesPage", () => {
  it("renders page heading", () => {
    render(<DeliveriesPage />, { wrapper });
    expect(screen.getByRole("heading", { name: /Deliveries/i })).toBeInTheDocument();
  });

  it("renders filter controls", () => {
    render(<DeliveriesPage />, { wrapper });
    expect(screen.getByLabelText(/Filter by status/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Filter by event type/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Refresh/i })).toBeInTheDocument();
  });
});

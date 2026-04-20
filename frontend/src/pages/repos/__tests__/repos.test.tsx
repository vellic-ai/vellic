import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastRoot } from "@/lib/toast";
import ReposPage from "../index";

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

describe("ReposPage", () => {
  it("renders page heading", () => {
    render(<ReposPage />, { wrapper });
    expect(screen.getByRole("heading", { name: /Repositories/i })).toBeInTheDocument();
  });

  it("renders Add repository button", () => {
    render(<ReposPage />, { wrapper });
    expect(screen.getByRole("button", { name: /Add repository/i })).toBeInTheDocument();
  });
});

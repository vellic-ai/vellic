import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastRoot } from "@/lib/toast";
import SettingsPage from "../index";

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

describe("SettingsPage", () => {
  it("renders Providers heading", () => {
    render(<SettingsPage />, { wrapper });
    expect(screen.getByRole("heading", { name: /Providers/i })).toBeInTheDocument();
  });

  it("renders manage repositories button", () => {
    render(<SettingsPage />, { wrapper });
    expect(screen.getByRole("button", { name: /Manage repositories/i })).toBeInTheDocument();
  });
});

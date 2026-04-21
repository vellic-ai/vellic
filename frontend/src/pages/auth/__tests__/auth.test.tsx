import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastRoot } from "@/lib/toast";
import AuthPage from "../index";

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

describe("AuthPage", () => {
  it("renders password field and sign in button", () => {
    render(<AuthPage />, { wrapper });
    expect(screen.getByLabelText(/Admin password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign in/i })).toBeInTheDocument();
  });

  it("sign in button is disabled when password is empty", () => {
    render(<AuthPage />, { wrapper });
    expect(screen.getByRole("button", { name: /Sign in/i })).toBeDisabled();
  });
});

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  it("renders Settings heading", () => {
    render(<SettingsPage />, { wrapper });
    expect(screen.getByRole("heading", { name: /Settings/i })).toBeInTheDocument();
  });

  it("renders manage repositories button", () => {
    render(<SettingsPage />, { wrapper });
    expect(screen.getByRole("button", { name: /Manage repositories/i })).toBeInTheDocument();
  });

  it("shows LLM Providers tab by default", () => {
    render(<SettingsPage />, { wrapper });
    expect(screen.getByRole("button", { name: /LLM Providers/i })).toBeInTheDocument();
  });

  it("shows VCS Adapters tab", () => {
    render(<SettingsPage />, { wrapper });
    expect(screen.getByTestId("vcs-tab")).toBeInTheDocument();
  });

  it("switches to VCS Adapters tab on click", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />, { wrapper });
    await user.click(screen.getByTestId("vcs-tab"));
    expect(await screen.findByTestId("github-app-id")).toBeInTheDocument();
  });
});

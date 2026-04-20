import { beforeEach, describe, expect, it, vi } from "vitest";
import { createApiClient, ApiError, API_ERROR_EVENT, API_LOGOUT_EVENT } from "@/api/client";

// Pass mockFetch directly to bypass globalThis.fetch isolation in Vitest jsdom.
// openapi-fetch captures the fetch reference at createClient() time (baseFetch),
// so injecting it via the factory guarantees our mock is the one used.
const mockFetch = vi.fn<typeof fetch>();
const api = createApiClient("http://localhost:5173", mockFetch);

function mockJsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockTextResponse(body: string, status: number): Response {
  return new Response(body, { status, headers: { "Content-Type": "text/plain" } });
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("api client — credentials", () => {
  it("sends credentials: include on every request", async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        prs_reviewed_24h: 0, prs_reviewed_7d: 0, latency_p50_ms: 0,
        latency_p95_ms: 0, failure_rate_pct: 0,
        llm_provider: null, llm_model: null, recent_deliveries: [],
      }),
    );

    await api.GET("/admin/stats");

    const [request] = mockFetch.mock.calls[0] as [Request, RequestInit];
    expect(request.credentials).toBe("include");
  });
});

describe("api client — error handling", () => {
  it("throws ApiError(401) and fires both API_ERROR_EVENT and API_LOGOUT_EVENT", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse({ detail: "Unauthorized" }, 401));

    const logoutFired = vi.fn();
    const errorFired = vi.fn();
    window.addEventListener(API_LOGOUT_EVENT, logoutFired);
    window.addEventListener(API_ERROR_EVENT, errorFired);

    await expect(api.GET("/admin/stats")).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      message: "Unauthorized",
    });

    expect(errorFired).toHaveBeenCalledTimes(1);
    expect(logoutFired).toHaveBeenCalledTimes(1);

    window.removeEventListener(API_LOGOUT_EVENT, logoutFired);
    window.removeEventListener(API_ERROR_EVENT, errorFired);
  });

  it("throws ApiError(403) and fires API_ERROR_EVENT but NOT API_LOGOUT_EVENT", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse({ detail: "Forbidden" }, 403));

    const logoutFired = vi.fn();
    const errorFired = vi.fn();
    window.addEventListener(API_LOGOUT_EVENT, logoutFired);
    window.addEventListener(API_ERROR_EVENT, errorFired);

    await expect(api.GET("/admin/stats")).rejects.toMatchObject({
      name: "ApiError",
      status: 403,
      message: "Forbidden",
    });

    expect(errorFired).toHaveBeenCalledTimes(1);
    expect(logoutFired).not.toHaveBeenCalled();

    window.removeEventListener(API_LOGOUT_EVENT, logoutFired);
    window.removeEventListener(API_ERROR_EVENT, errorFired);
  });

  it("throws ApiError(500) and fires API_ERROR_EVENT", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse({ detail: "Internal Server Error" }, 500));

    const errorFired = vi.fn();
    window.addEventListener(API_ERROR_EVENT, errorFired);

    await expect(api.GET("/admin/stats")).rejects.toMatchObject({
      name: "ApiError",
      status: 500,
    });

    expect(errorFired).toHaveBeenCalledTimes(1);
    window.removeEventListener(API_ERROR_EVENT, errorFired);
  });

  it("throws ApiError but does NOT fire events for 404", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse({ detail: "Not found" }, 404));

    const errorFired = vi.fn();
    window.addEventListener(API_ERROR_EVENT, errorFired);

    await expect(api.GET("/admin/settings/llm")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
    });

    expect(errorFired).not.toHaveBeenCalled();
    window.removeEventListener(API_ERROR_EVENT, errorFired);
  });

  it("extracts detail from JSON error body as message", async () => {
    mockFetch.mockResolvedValueOnce(mockJsonResponse({ detail: "Invalid credentials" }, 401));

    let caughtError: unknown;
    try {
      await api.POST("/admin/auth/login", { body: { password: "wrong" } });
    } catch (e) {
      caughtError = e;
    }

    expect(caughtError).toBeInstanceOf(ApiError);
    expect((caughtError as ApiError).message).toBe("Invalid credentials");
  });

  it("falls back to status text for non-JSON bodies", async () => {
    mockFetch.mockResolvedValueOnce(mockTextResponse("Bad Gateway", 502));

    let caughtError: unknown;
    try {
      await api.GET("/admin/stats");
    } catch (e) {
      caughtError = e;
    }

    expect(caughtError).toBeInstanceOf(ApiError);
    expect((caughtError as ApiError).status).toBe(502);
  });
});

describe("api client — successful responses", () => {
  it("returns typed data for GET /admin/auth/status", async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({ setup_required: false, authenticated: true }),
    );

    const { data, error } = await api.GET("/admin/auth/status");
    expect(error).toBeUndefined();
    expect(data?.authenticated).toBe(true);
    expect(data?.setup_required).toBe(false);
  });

  it("returns typed data for GET /admin/stats", async () => {
    mockFetch.mockResolvedValueOnce(
      mockJsonResponse({
        prs_reviewed_24h: 5, prs_reviewed_7d: 30, latency_p50_ms: 1000,
        latency_p95_ms: 5000, failure_rate_pct: 0,
        llm_provider: "ollama", llm_model: "qwen2.5-coder:14b", recent_deliveries: [],
      }),
    );

    const { data, error } = await api.GET("/admin/stats");
    expect(error).toBeUndefined();
    expect(data?.prs_reviewed_24h).toBe(5);
    expect(data?.llm_provider).toBe("ollama");
  });
});

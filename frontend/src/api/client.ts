import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type ApiErrorEvent = CustomEvent<{ status: number; message: string }>;

export const API_ERROR_EVENT = "vellic:api-error" as const;
export const API_LOGOUT_EVENT = "vellic:api-logout" as const;

function fireApiError(status: number, message: string) {
  window.dispatchEvent(
    new CustomEvent(API_ERROR_EVENT, { detail: { status, message } }),
  );
  if (status === 401) {
    window.dispatchEvent(new CustomEvent(API_LOGOUT_EVENT));
  }
}

const errorMiddleware: Middleware = {
  async onResponse({ response }) {
    if (response.ok) return response;

    let message = `HTTP ${response.status}`;
    try {
      const clone = response.clone();
      const json = await clone.json();
      message = (json as Record<string, string>).detail ?? message;
    } catch {
      // non-JSON error body — keep default message
    }

    if (response.status === 401 || response.status === 403 || response.status >= 500) {
      fireApiError(response.status, message);
    }

    throw new ApiError(response.status, message);
  },
};

export function createApiClient(
  baseUrl: string,
  fetchFn?: typeof globalThis.fetch,
) {
  const client = createClient<paths>({
    baseUrl,
    credentials: "include",
    ...(fetchFn ? { fetch: fetchFn } : {}),
  });
  client.use(errorMiddleware);
  return client;
}

export const api = createApiClient(
  typeof window !== "undefined" && window.location.origin !== "null"
    ? window.location.origin
    : "http://localhost:5173",
);

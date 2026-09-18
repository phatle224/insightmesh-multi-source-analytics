import { describe, expect, it, vi } from "vitest";

import { ApiClientError, apiRequest } from "@/lib/api-client";

describe("apiRequest", () => {
  it("returns typed JSON for a successful response", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(apiRequest<{ status: string }>("/api/v1/health", {}, fetcher)).resolves.toEqual({
      status: "ok",
    });
  });

  it("maps the canonical backend error envelope", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "validation_error", message: "Request validation failed", retryable: false },
          request_id: "request-123",
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );

    const error = await apiRequest("/api/v1/datasources", {}, fetcher).catch(
      (reason: unknown) => reason,
    );
    expect(error).toBeInstanceOf(ApiClientError);
    expect(error).toMatchObject({
      code: "validation_error",
      message: "Request validation failed",
      requestId: "request-123",
      retryable: false,
      status: 422,
    });
  });

  it("does not expose an unstructured server response", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response("raw driver secret", { status: 500 }));

    const error = await apiRequest("/api/v1/datasources", {}, fetcher).catch(
      (reason: unknown) => reason,
    );
    expect(error).toMatchObject({
      code: "invalid_error_response",
      message: "The service returned an unreadable error response.",
      retryable: true,
    });
    expect(String(error)).not.toContain("raw driver secret");
  });
});

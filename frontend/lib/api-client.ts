export interface ApiErrorBody {
  code: string;
  message: string;
  retryable: boolean;
  details?: Record<string, unknown>;
}

export interface ApiErrorEnvelope {
  error: ApiErrorBody;
  request_id: string;
}

export class ApiClientError extends Error {
  readonly code: string;
  readonly retryable: boolean;
  readonly requestId: string;
  readonly status: number;
  readonly details?: Record<string, unknown>;

  constructor(envelope: ApiErrorEnvelope, status: number) {
    super(envelope.error.message);
    this.name = "ApiClientError";
    this.code = envelope.error.code;
    this.retryable = envelope.error.retryable;
    this.requestId = envelope.request_id;
    this.status = status;
    this.details = envelope.error.details;
  }
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<ApiErrorEnvelope>;
  return (
    typeof candidate.request_id === "string" &&
    typeof candidate.error === "object" &&
    candidate.error !== null &&
    typeof candidate.error.code === "string" &&
    typeof candidate.error.message === "string" &&
    typeof candidate.error.retryable === "boolean"
  );
}

export async function apiRequest<T>(
  path: `/api/v1/${string}`,
  init: RequestInit = {},
  fetcher: typeof fetch = fetch,
): Promise<T> {
  const response = await fetcher(path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    if (isApiErrorEnvelope(payload)) throw new ApiClientError(payload, response.status);
    throw new ApiClientError(
      {
        error: {
          code: "invalid_error_response",
          message: "The service returned an unreadable error response.",
          retryable: response.status >= 500,
        },
        request_id: response.headers.get("X-Request-ID") ?? "unknown",
      },
      response.status,
    );
  }
  return payload as T;
}

"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApiClientError } from "@/lib/api-client";
import { listDatasources, type DatasourceSummary } from "@/lib/datasources";

interface DatasourceContextValue {
  sources: DatasourceSummary[];
  activeSource: DatasourceSummary | null;
  loading: boolean;
  error: ApiClientError | null;
  refresh: () => Promise<void>;
}

const DatasourceContext = createContext<DatasourceContextValue | null>(null);

function normalizeError(error: unknown) {
  if (error instanceof ApiClientError) return error;
  return new ApiClientError(
    {
      error: {
        code: "network_error",
        message: "InsightMesh could not reach the datasource service.",
        retryable: true,
      },
      request_id: "unavailable",
    },
    0,
  );
}

export function DatasourceProvider({ children }: { children: ReactNode }) {
  const [sources, setSources] = useState<DatasourceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiClientError | null>(null);
  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSources(await listDatasources());
    } catch (reason) {
      setError(normalizeError(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    listDatasources()
      .then((items) => {
        if (active) setSources(items);
      })
      .catch((reason: unknown) => {
        if (active) setError(normalizeError(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  const value = useMemo(
    () => ({
      sources,
      activeSource: sources.find((source) => source.is_active) ?? null,
      loading,
      error,
      refresh,
    }),
    [sources, loading, error, refresh],
  );
  return <DatasourceContext.Provider value={value}>{children}</DatasourceContext.Provider>;
}

export function useDatasources() {
  const value = useContext(DatasourceContext);
  if (!value) throw new Error("useDatasources must be used inside DatasourceProvider");
  return value;
}

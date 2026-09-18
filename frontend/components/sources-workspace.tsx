"use client";

import { ArrowClockwiseIcon, DatabaseIcon, PlusIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { useDatasources } from "@/components/datasource-provider";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { SourceStatus } from "@/components/source-status";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { activateDatasource, refreshDatasource } from "@/lib/datasources";

function formatDate(value: string | null) {
  return value
    ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(value),
      )
    : "Not refreshed yet";
}

export function SourcesWorkspace() {
  const { sources, loading, error, refresh } = useDatasources();
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<Error | null>(null);

  async function runAction(id: string, action: "activate" | "refresh") {
    setPendingId(id);
    setActionError(null);
    try {
      await (action === "activate" ? activateDatasource(id) : refreshDatasource(id));
      await refresh();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason : new Error("Datasource action failed."));
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Data workspace"
        title="Sources"
        description="Connect and manage databases through a read-only, schema-bounded access path."
        action={
          <Button asChild>
            <Link href="/sources/new">
              <PlusIcon size={18} aria-hidden /> Add source
            </Link>
          </Button>
        }
      />
      {actionError ? (
        <ApiErrorNotice title="Datasource action failed" message={actionError.message} />
      ) : null}
      {error ? (
        <ApiErrorNotice
          title="Sources could not be loaded"
          message={error.message}
          requestId={error.requestId}
          action={<Button onClick={() => void refresh()}>Try again</Button>}
        />
      ) : null}
      {loading && sources.length === 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Loading sources">
          {[0, 1, 2].map((item) => (
            <Card key={item} className="h-56 animate-pulse bg-muted" />
          ))}
        </div>
      ) : null}
      {!loading && !error && sources.length === 0 ? (
        <EmptyState
          icon={<DatabaseIcon size={24} weight="duotone" />}
          title="No data sources yet"
          description="Add the Docker demo PostgreSQL database or another read-only PostgreSQL connection."
          action={
            <Button asChild>
              <Link href="/sources/new">Add PostgreSQL source</Link>
            </Button>
          }
        />
      ) : null}
      {sources.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {sources.map((source) => (
            <Card key={source.id} className="flex min-h-56 flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wider text-primary">
                    PostgreSQL
                  </p>
                  <h2 className="mt-1 truncate text-lg font-semibold text-text">{source.name}</h2>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                  {source.is_active ? (
                    <span className="rounded-full bg-primary px-2.5 py-1 text-xs font-semibold text-on-primary">
                      Active
                    </span>
                  ) : null}
                  <SourceStatus status={source.status} />
                </div>
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-muted-foreground">Database</dt>
                  <dd className="truncate font-medium text-text">{source.database_name}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Schema objects</dt>
                  <dd className="font-medium text-text">{source.entity_count}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-muted-foreground">Last refresh</dt>
                  <dd className="font-medium text-text">{formatDate(source.last_refreshed_at)}</dd>
                </div>
              </dl>
              <div className="mt-auto flex flex-wrap gap-2 pt-5">
                <Button asChild variant="secondary" size="small">
                  <Link href={`/sources/${source.id}`}>View</Link>
                </Button>
                {!source.is_active && source.status === "ready" ? (
                  <Button
                    size="small"
                    onClick={() => void runAction(source.id, "activate")}
                    disabled={pendingId !== null}
                  >
                    Activate
                  </Button>
                ) : null}
                <Button
                  variant="ghost"
                  size="small"
                  onClick={() => void runAction(source.id, "refresh")}
                  disabled={pendingId !== null}
                >
                  <ArrowClockwiseIcon
                    className={pendingId === source.id ? "animate-spin" : undefined}
                    size={16}
                    aria-hidden
                  />
                  Refresh
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );
}

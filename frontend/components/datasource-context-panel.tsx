"use client";

import { ArrowClockwiseIcon, CircleNotchIcon, DatabaseIcon, GraphIcon, TableIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { RelationshipExplorer } from "@/components/relationship-explorer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiClientError } from "@/lib/api-client";
import {
  getDatasource,
  getDatasourcePreview,
  type DatasourceDetail,
  type DatasourcePreview,
  type DatasourceSummary,
} from "@/lib/datasources";

type ContextView = "preview" | "erd";

function normalizeError(reason: unknown) {
  return reason instanceof ApiClientError
    ? reason
    : new ApiClientError(
        {
          error: {
            code: "network_error",
            message: "Datasource context could not be loaded.",
            retryable: true,
          },
          request_id: "unavailable",
        },
        0,
      );
}

function displayCell(value: unknown) {
  if (value === null || value === undefined) return "NULL";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return "[structured value]";
    }
  }
  return String(value);
}

function PreviewTable({ preview }: { preview: DatasourcePreview }) {
  if (preview.rows.length === 0) {
    return (
      <div className="rounded-md border border-border bg-muted/35 p-5 text-sm text-muted-foreground">
        This entity does not contain any rows to preview.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border border-border" tabIndex={0} aria-label="Datasource row preview">
      <table className="min-w-[44rem] w-full border-collapse text-left text-sm">
        <caption className="sr-only">
          First {preview.rows.length} rows from {preview.schema_name}.{preview.entity_name}.
        </caption>
        <thead className="bg-muted/70 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="sticky left-0 bg-muted/70 px-3 py-3">#</th>
            {preview.columns.map((column) => <th key={column} className="whitespace-nowrap px-3 py-3">{column}</th>)}
          </tr>
        </thead>
        <tbody>
          {preview.rows.map((row, rowIndex) => (
            <tr key={`${preview.entity_id}-${rowIndex}`} className="border-t border-border align-top hover:bg-muted/30">
              <td className="sticky left-0 bg-card px-3 py-3 font-mono text-xs text-muted-foreground">{rowIndex + 1}</td>
              {preview.columns.map((column, columnIndex) => (
                <td key={`${column}-${columnIndex}`} className="max-w-[20rem] whitespace-normal break-words px-3 py-3 text-text">
                  {displayCell(row[columnIndex])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DatasourceContextPanel({ source }: { source: DatasourceSummary }) {
  const [view, setView] = useState<ContextView>("preview");
  const [detail, setDetail] = useState<DatasourceDetail | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState("");
  const [preview, setPreview] = useState<DatasourcePreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [previewError, setPreviewError] = useState<ApiClientError | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let active = true;
    getDatasource(source.id)
      .then((nextDetail) => {
        if (!active) return;
        setError(null);
        setDetail(nextDetail);
        setSelectedEntityId(nextDetail.entities[0]?.id ?? "");
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
  }, [source.id]);

  useEffect(() => {
    if (view !== "preview" || !selectedEntityId) return;
    let active = true;
    getDatasourcePreview(source.id, selectedEntityId)
      .then((nextPreview) => {
        if (!active) return;
        setPreviewError(null);
        setPreview(nextPreview);
      })
      .catch((reason: unknown) => {
        if (active) setPreviewError(normalizeError(reason));
      });
    return () => {
      active = false;
    };
  }, [refreshToken, selectedEntityId, source.id, view]);

  const selectedEntity = useMemo(
    () => detail?.entities.find((entity) => entity.id === selectedEntityId) ?? null,
    [detail, selectedEntityId],
  );
  const previewLoading = Boolean(
    selectedEntityId && (!preview || preview.entity_id !== selectedEntityId),
  );

  return (
    <Card className="overflow-hidden" aria-labelledby="datasource-context-heading">
      <div className="flex flex-col gap-4 border-b border-border px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-primary" aria-hidden>
            <DatabaseIcon size={21} />
          </span>
          <div className="min-w-0">
            <h2 id="datasource-context-heading" className="font-semibold text-text">Explore source</h2>
            <p className="mt-1 text-sm text-muted-foreground">Inspect a small read-only sample or understand how entities connect before asking a question.</p>
          </div>
        </div>
        <Button asChild variant="ghost" size="small">
          <Link href={`/sources/${source.id}`}>Full source details</Link>
        </Button>
      </div>

      <div className="grid gap-2 border-b border-border bg-muted/25 p-3 sm:grid-cols-2" role="tablist" aria-label="Datasource context view">
        <Button
          size="default"
          variant={view === "preview" ? "primary" : "secondary"}
          role="tab"
          aria-selected={view === "preview"}
          onClick={() => setView("preview")}
        >
          <TableIcon size={18} aria-hidden /> Preview rows
        </Button>
        <Button
          size="default"
          variant={view === "erd" ? "primary" : "secondary"}
          role="tab"
          aria-selected={view === "erd"}
          onClick={() => setView("erd")}
        >
          <GraphIcon size={18} aria-hidden /> ERD / relationships
        </Button>
      </div>

      {view === "erd" ? (
        loading ? (
          <div className="h-80 animate-pulse bg-muted" aria-label="Loading datasource relationships" />
        ) : error ? (
          <div className="p-5"><ApiErrorNotice title="Relationships could not be loaded" message={error.message} requestId={error.requestId} /></div>
        ) : detail ? (
          <RelationshipExplorer entities={detail.entities} relationships={detail.relationships} />
        ) : null
      ) : (
        <div className="space-y-4 p-5">
          {loading ? (
            <div className="h-28 animate-pulse rounded-md bg-muted" aria-label="Loading datasource preview" />
          ) : error ? (
            <ApiErrorNotice title="Datasource preview could not be loaded" message={error.message} requestId={error.requestId} />
          ) : detail && detail.entities.length > 0 ? (
            <>
              <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
                <label className="text-sm font-medium text-text">
                  Entity to preview
                  <select
                    className="mt-2 min-h-11 w-full rounded-md border border-border bg-card px-3 text-sm text-text focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    value={selectedEntityId}
                    onChange={(event) => {
                      setPreview(null);
                      setPreviewError(null);
                      setSelectedEntityId(event.target.value);
                    }}
                  >
                    {detail.entities.map((entity) => (
                      <option key={entity.id} value={entity.id}>{entity.schema_name}.{entity.name}</option>
                    ))}
                  </select>
                </label>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setPreview(null);
                    setPreviewError(null);
                    setRefreshToken((value) => value + 1);
                  }}
                  disabled={previewLoading || !selectedEntityId}
                >
                  {previewLoading ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : <ArrowClockwiseIcon size={18} aria-hidden />} Refresh sample
                </Button>
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground" aria-label="Selected entity metadata">
                <span><strong className="text-text">{selectedEntity?.fields.length ?? 0}</strong> fields</span>
                <span>Read-only sample, maximum 10 rows</span>
              </div>
              {previewError ? <ApiErrorNotice title="Rows could not be loaded" message={previewError.message} requestId={previewError.requestId} /> : null}
              {previewLoading && !preview ? <div className="h-44 animate-pulse rounded-md bg-muted" aria-label="Loading preview rows" /> : null}
              {preview && !previewLoading ? (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <p className="font-semibold text-text">First {preview.rows.length} rows from {preview.schema_name}.{preview.entity_name}</p>
                    {preview.truncated ? <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">More rows available</span> : null}
                  </div>
                  <PreviewTable preview={preview} />
                </>
              ) : null}
            </>
          ) : (
            <div className="rounded-md border border-border bg-muted/35 p-5 text-sm text-muted-foreground">
              No entities are available yet. Refresh metadata from the source details page first.
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

"use client";

import { ArrowClockwiseIcon, CircleNotchIcon, DatabaseIcon, GraphIcon, TableIcon, XIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent, useEffect, useMemo, useRef, useState } from "react";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { RelationshipExplorer } from "@/components/relationship-explorer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { ApiClientError } from "@/lib/api-client";
import {
  getDatasource,
  getDatasourcePreview,
  type DatasourceDetail,
  type DatasourcePreview,
  type DatasourceSummary,
} from "@/lib/datasources";

type ContextView = "preview" | "erd";
const DEFAULT_DRAWER_WIDTH = 640;
const MAX_DRAWER_WIDTH = 1080;

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

export function DatasourceContextPanel({
  source,
  canRun,
}: {
  source: DatasourceSummary;
  canRun?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<ContextView>("preview");
  const [detail, setDetail] = useState<DatasourceDetail | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState("");
  const [preview, setPreview] = useState<DatasourcePreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [previewError, setPreviewError] = useState<ApiClientError | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const [drawerWidth, setDrawerWidth] = useState(DEFAULT_DRAWER_WIDTH);
  const [resizing, setResizing] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const resizeStartRef = useRef({ startX: 0, startWidth: DEFAULT_DRAWER_WIDTH });

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

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    const previousPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) document.body.style.paddingRight = `${scrollbarWidth}px`;
    const focusFrame = window.requestAnimationFrame(() => closeButtonRef.current?.focus());
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = drawerRef.current?.querySelectorAll<HTMLElement>(
        'button, a[href], select, input, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.cancelAnimationFrame(focusFrame);
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      document.body.style.paddingRight = previousPaddingRight;
    };
  }, [open]);

  function startResize(event: ReactPointerEvent<HTMLDivElement>) {
    if (window.innerWidth < 768) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    resizeStartRef.current = { startX: event.clientX, startWidth: drawerWidth };
    setResizing(true);
  }

  function resizeDrawer(event: ReactPointerEvent<HTMLDivElement>) {
    if (!resizing) return;
    const maxWidth = Math.min(MAX_DRAWER_WIDTH, window.innerWidth - 16);
    const nextWidth = resizeStartRef.current.startWidth + resizeStartRef.current.startX - event.clientX;
    setDrawerWidth(Math.min(maxWidth, Math.max(DEFAULT_DRAWER_WIDTH, nextWidth)));
  }

  function stopResize(event: ReactPointerEvent<HTMLDivElement>) {
    if (!resizing) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setResizing(false);
  }

  function adjustDrawerWidth(event: ReactKeyboardEvent<HTMLDivElement>) {
    const maxWidth = Math.min(MAX_DRAWER_WIDTH, window.innerWidth - 16);
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setDrawerWidth((width) => Math.min(maxWidth, width + 32));
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      setDrawerWidth((width) => Math.max(DEFAULT_DRAWER_WIDTH, width - 32));
    } else if (event.key === "Home") {
      event.preventDefault();
      setDrawerWidth(DEFAULT_DRAWER_WIDTH);
    } else if (event.key === "End") {
      event.preventDefault();
      setDrawerWidth(maxWidth);
    }
  }

  function closeDrawer() {
    setOpen(false);
    window.requestAnimationFrame(() => triggerRef.current?.focus());
  }

  return (
    <>
      <Card className="flex flex-wrap items-center justify-between gap-3 p-3 sm:p-4" aria-label="Active datasource status">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-primary" aria-hidden>
            <DatabaseIcon size={21} />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Active source</p>
            <p className="truncate font-semibold text-text">{source.name}</p>
            <p className="truncate text-xs text-muted-foreground">
              {source.source_type === "mysql" ? "MySQL" : "PostgreSQL"} · {source.database_name} · {source.entity_count} entities · {source.relationship_count} relationships · semantic index {source.semantic_status}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            ref={triggerRef}
            variant="secondary"
            onClick={() => setOpen(true)}
            aria-expanded={open}
            aria-controls="datasource-context-drawer"
          >
            <TableIcon size={18} aria-hidden /> Inspect source
          </Button>
        </div>
      </Card>

      {open ? (
        <>
          <button type="button" className="fixed inset-0 z-40 bg-text/35 backdrop-blur-[1px]" aria-label="Close source context" onClick={closeDrawer} />
          <aside
            ref={drawerRef}
            id="datasource-context-drawer"
            className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-[calc(100vw-1rem)] flex-col border-l border-border bg-card shadow-float ${resizing ? "select-none" : "transition-[width] duration-200 ease-out"}`}
            style={{ width: `${drawerWidth}px` }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="datasource-context-heading"
          >
            <div
              className="absolute inset-y-0 left-0 z-10 hidden w-3 -translate-x-1/2 cursor-col-resize items-center justify-center md:flex"
              role="separator"
              aria-label="Resize source context drawer"
              aria-orientation="vertical"
              aria-valuemin={DEFAULT_DRAWER_WIDTH}
              aria-valuemax={MAX_DRAWER_WIDTH}
              aria-valuenow={drawerWidth}
              aria-valuetext={`${drawerWidth}px wide; use left and right arrow keys to resize`}
              tabIndex={0}
              onPointerDown={startResize}
              onPointerMove={resizeDrawer}
              onPointerUp={stopResize}
              onPointerCancel={stopResize}
              onKeyDown={adjustDrawerWidth}
            >
              <span className="h-16 w-1 rounded-full bg-border-strong transition-colors hover:bg-primary" />
            </div>
            <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wider text-primary">Source context</p>
                <h2 id="datasource-context-heading" className="mt-1 truncate text-lg font-semibold text-text">{source.name}</h2>
                <p className="mt-1 truncate text-sm text-muted-foreground">{source.source_type === "mysql" ? "MySQL" : "PostgreSQL"} · {source.database_name}</p>
              </div>
              <Button ref={closeButtonRef} size="icon" variant="ghost" aria-label="Close source context" onClick={closeDrawer}>
                <XIcon size={20} aria-hidden />
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

            <div className="min-h-0 flex-1 overflow-y-auto">
              {view === "erd" ? (
                loading ? (
                  <div className="h-80 animate-pulse bg-muted" aria-label="Loading datasource relationships" />
                ) : error ? (
                  <div className="p-5"><ApiErrorNotice title="Relationships could not be loaded" message={error.message} requestId={error.requestId} /></div>
                ) : detail ? (
                  <RelationshipExplorer datasourceId={source.id} entities={detail.entities} relationships={detail.relationships} />
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
            </div>
            <div className="border-t border-border px-5 py-3">
              <Link href={`/sources/${source.id}`} className="text-sm font-semibold text-primary hover:text-primary-hover">Open full source details</Link>
            </div>
          </aside>
        </>
      ) : null}
    </>
  );
}

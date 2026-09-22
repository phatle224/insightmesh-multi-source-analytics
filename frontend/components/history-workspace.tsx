"use client";

import {
  ArrowClockwiseIcon,
  BookmarkSimpleIcon,
  CaretLeftIcon,
  CaretRightIcon,
  ClockCounterClockwiseIcon,
  EyeIcon,
  MagnifyingGlassIcon,
  PlayIcon,
  TrashIcon,
} from "@phosphor-icons/react";
import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { useDatasources } from "@/components/datasource-provider";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { QueryRunDetails } from "@/components/query-run-details";
import { ResultVisualization } from "@/components/result-visualization";
import { SaveWidgetDialog } from "@/components/save-widget-dialog";
import { SaveAnalysisDialog } from "@/components/save-analysis-dialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { ApiClientError } from "@/lib/api-client";
import {
  createQueryRun,
  clearQueryRuns,
  getQueryRun,
  getQueryTrace,
  listQueryRuns,
  type QueryRun,
  type QueryRunPage,
  type QueryRunStatus,
  type QueryTrace,
} from "@/lib/query-runs";
import { isChartType } from "@/lib/visualization";
import {
  deleteSavedAnalysis,
  listSavedAnalyses,
  type SavedAnalysis,
} from "@/lib/saved-analyses";

const FILTER_STATUSES: Array<{ value: QueryRunStatus | ""; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "completed", label: "Completed" },
  { value: "clarification_required", label: "Clarification required" },
  { value: "out_of_scope", label: "Out of scope" },
  { value: "blocked", label: "Blocked" },
  { value: "failed", label: "Failed" },
];

interface AppliedFilters {
  search: string;
  status: QueryRunStatus | "";
  datasourceId: string;
  createdBefore: string;
}

const EMPTY_FILTERS: AppliedFilters = {
  search: "",
  status: "",
  datasourceId: "",
  createdBefore: "",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDuration(value: number | null) {
  if (value === null) return "—";
  return value < 1000 ? `${value} ms` : `${(value / 1000).toFixed(1)} s`;
}

function asError(reason: unknown) {
  return reason instanceof Error ? reason : new Error("Query history could not be loaded.");
}

export function HistoryWorkspace() {
  const { sources } = useDatasources();
  const [draft, setDraft] = useState<AppliedFilters>(EMPTY_FILTERS);
  const [filters, setFilters] = useState<AppliedFilters>(EMPTY_FILTERS);
  const [cursor, setCursor] = useState<string | undefined>();
  const [previousCursors, setPreviousCursors] = useState<Array<string | undefined>>([]);
  const [data, setData] = useState<QueryRunPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [rerunningId, setRerunningId] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [detail, setDetail] = useState<QueryRun | null>(null);
  const [detailTrace, setDetailTrace] = useState<QueryTrace | null>(null);
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailErrorRunId, setDetailErrorRunId] = useState<string | null>(null);
  const [view, setView] = useState<"recent" | "saved">("recent");
  const [saved, setSaved] = useState<SavedAnalysis[]>([]);
  const [savedLoaded, setSavedLoaded] = useState(false);
  const [savedLoading, setSavedLoading] = useState(false);
  const [savedError, setSavedError] = useState<Error | null>(null);
  const [deletingSavedId, setDeletingSavedId] = useState<string | null>(null);
  const recentRequestKey = useRef<string | null>(null);
  const recentRequestGeneration = useRef(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(
        await listQueryRuns({
          limit: 20,
          cursor,
          search: filters.search,
          status: filters.status,
          datasourceId: filters.datasourceId,
          createdBefore: filters.createdBefore
            ? new Date(filters.createdBefore).toISOString()
            : undefined,
        }),
      );
    } catch (reason) {
      setError(asError(reason));
    } finally {
      setLoading(false);
    }
  }, [cursor, filters]);

  const loadSaved = useCallback(async () => {
    setSavedLoading(true);
    setSavedError(null);
    try {
      setSaved(await listSavedAnalyses());
      setSavedLoaded(true);
    } catch (reason) {
      setSavedError(asError(reason));
    } finally {
      setSavedLoading(false);
    }
  }, []);

  useEffect(() => {
    if (view !== "saved" || savedLoaded) return;
    let active = true;
    listSavedAnalyses()
      .then((nextSaved) => {
        if (active) {
          setSaved(nextSaved);
          setSavedLoaded(true);
        }
      })
      .catch((reason: unknown) => {
        if (active) setSavedError(asError(reason));
      })
      .finally(() => {
        if (active) setSavedLoading(false);
      });
    return () => {
      active = false;
    };
  }, [savedLoaded, view]);

  useEffect(() => {
    if (view !== "recent") return;
    const requestKey = JSON.stringify({ cursor, filters });
    if (recentRequestKey.current === requestKey) return;
    recentRequestKey.current = requestKey;
    const requestGeneration = recentRequestGeneration.current;
    let active = true;
    listQueryRuns({
      limit: 20,
      cursor,
      search: filters.search,
      status: filters.status,
      datasourceId: filters.datasourceId,
      createdBefore: filters.createdBefore
        ? new Date(filters.createdBefore).toISOString()
        : undefined,
    })
      .then((nextData) => {
        if (active && requestGeneration === recentRequestGeneration.current) setData(nextData);
      })
      .catch((reason: unknown) => {
        if (active && requestGeneration === recentRequestGeneration.current) {
          recentRequestKey.current = null;
          setError(asError(reason));
        }
      })
      .finally(() => {
        if (active && requestGeneration === recentRequestGeneration.current) setLoading(false);
      });
    return () => {
      active = false;
      recentRequestKey.current = null;
    };
  }, [cursor, filters, view]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setCursor(undefined);
    setPreviousCursors([]);
    setFilters({ ...draft, search: draft.search.trim() });
  }

  function clearFilters() {
    setLoading(true);
    setError(null);
    setDraft(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setCursor(undefined);
    setPreviousCursors([]);
  }

  function showNextPage() {
    if (!data?.next_cursor) return;
    setLoading(true);
    setError(null);
    setPreviousCursors((current) => [...current, cursor]);
    setCursor(data.next_cursor);
  }

  function showPreviousPage() {
    const nextPrevious = previousCursors.slice(0, -1);
    setLoading(true);
    setError(null);
    setCursor(previousCursors.at(-1));
    setPreviousCursors(nextPrevious);
  }

  async function rerun(runId: string, datasourceId: string, question: string) {
    setRerunningId(runId);
    setAnnouncement("");
    try {
      const nextRun = await createQueryRun(datasourceId, question);
      if (!cursor) await load();
      else {
        setLoading(true);
        setCursor(undefined);
        setPreviousCursors([]);
      }
      setAnnouncement(`Created independent run ${nextRun.run_id}.`);
    } catch (reason) {
      const rerunError = reason instanceof ApiClientError ? reason.message : asError(reason).message;
      setAnnouncement(`Rerun failed. ${rerunError}`);
    } finally {
      setRerunningId(null);
    }
  }

  async function toggleDetails(runId: string) {
    if (detail?.run_id === runId) {
      setDetail(null);
      setDetailTrace(null);
      setDetailError(null);
      setDetailErrorRunId(null);
      return;
    }
    setDetailLoadingId(runId);
    setDetailError(null);
    setDetailErrorRunId(null);
    try {
      const [nextDetail, nextTrace] = await Promise.all([
        getQueryRun(runId),
        getQueryTrace(runId),
      ]);
      setDetail(nextDetail);
      setDetailTrace(nextTrace);
    } catch (reason) {
      setDetail(null);
      setDetailTrace(null);
      setDetailError(asError(reason).message);
      setDetailErrorRunId(runId);
    } finally {
      setDetailLoadingId(null);
    }
  }

  async function removeSaved(analysis: SavedAnalysis) {
    setDeletingSavedId(analysis.id);
    try {
      await deleteSavedAnalysis(analysis.id);
      setSaved((current) => current.filter((item) => item.id !== analysis.id));
      setAnnouncement(`Removed saved analysis ${analysis.name}.`);
    } catch (reason) {
      setAnnouncement(`Could not remove saved analysis. ${asError(reason).message}`);
    } finally {
      setDeletingSavedId(null);
    }
  }

  async function clearRecentActivity() {
    if (!window.confirm("Clear all recent activity? Saved analyses and dashboards will not be removed.")) return;
    recentRequestGeneration.current += 1;
    recentRequestKey.current = null;
    setLoading(true);
    setError(null);
    try {
      const result = await clearQueryRuns();
      recentRequestGeneration.current += 1;
      recentRequestKey.current = null;
      setData({ items: [], limit: 20, total: 0, next_cursor: null, has_more: false });
      setDetail(null);
      setDetailTrace(null);
      setAnnouncement(`Cleared ${result.deleted_count} recent run${result.deleted_count === 1 ? "" : "s"}.`);
    } catch (reason) {
      recentRequestGeneration.current += 1;
      recentRequestKey.current = null;
      setError(asError(reason));
    } finally {
      setLoading(false);
    }
  }

  const filtered = Boolean(
    filters.search || filters.status || filters.datasourceId || filters.createdBefore,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reproducible runs"
        title="Query history"
        description="Keep the analyses you care about, while recent execution activity expires automatically."
      />

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Query history views">
        <Button
          variant={view === "recent" ? "primary" : "secondary"}
          role="tab"
          aria-selected={view === "recent"}
          onClick={() => setView("recent")}
        >
          <ClockCounterClockwiseIcon size={18} aria-hidden /> Recent activity
        </Button>
        <Button
          variant={view === "saved" ? "primary" : "secondary"}
          role="tab"
          aria-selected={view === "saved"}
          onClick={() => {
            if (!savedLoaded) setSavedLoading(true);
            setSavedError(null);
            setView("saved");
          }}
        >
          <BookmarkSimpleIcon size={18} aria-hidden /> Saved analyses
        </Button>
      </div>

      {view === "recent" ? <Card className="p-4 sm:p-5">
        <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(14rem,1fr)_13rem_13rem_13rem_auto] xl:items-end" onSubmit={applyFilters}>
          <div>
            <label htmlFor="history-search" className="text-sm font-semibold text-text">Search questions</label>
            <div className="relative mt-1.5">
              <MagnifyingGlassIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} aria-hidden />
              <input
                id="history-search"
                type="search"
                value={draft.search}
                onChange={(event) => setDraft((current) => ({ ...current, search: event.target.value }))}
                className="min-h-11 w-full rounded-md border border-border bg-card py-2 pl-10 pr-3 text-base text-text transition-colors duration-200 focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/20"
                placeholder="Revenue, customers, orders…"
                maxLength={200}
              />
            </div>
          </div>
          <div>
            <label htmlFor="history-status" className="text-sm font-semibold text-text">Status</label>
            <select
              id="history-status"
              value={draft.status}
              onChange={(event) => setDraft((current) => ({ ...current, status: event.target.value as QueryRunStatus | "" }))}
              className="mt-1.5 min-h-11 w-full rounded-md border border-border bg-card px-3 text-base text-text transition-colors duration-200 focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/20"
            >
              {FILTER_STATUSES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="history-source" className="text-sm font-semibold text-text">Datasource</label>
            <select
              id="history-source"
              value={draft.datasourceId}
              onChange={(event) => setDraft((current) => ({ ...current, datasourceId: event.target.value }))}
              className="mt-1.5 min-h-11 w-full rounded-md border border-border bg-card px-3 text-base text-text transition-colors duration-200 focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/20"
            >
              <option value="">All datasources</option>
              {sources.map((source) => <option key={source.id} value={source.id}>{source.name}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="history-created-before" className="text-sm font-semibold text-text">Created before</label>
            <input
              id="history-created-before"
              type="datetime-local"
              value={draft.createdBefore}
              onChange={(event) => setDraft((current) => ({ ...current, createdBefore: event.target.value }))}
              className="mt-1.5 min-h-11 w-full rounded-md border border-border bg-card px-3 text-base text-text transition-colors duration-200 focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/20"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit">Apply filters</Button>
            {filtered ? <Button type="button" variant="ghost" onClick={clearFilters}>Clear</Button> : null}
            <Button type="button" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => void clearRecentActivity()}>Clear recent</Button>
          </div>
        </form>
      </Card> : null}

      <p className="sr-only" aria-live="polite" aria-atomic="true">{announcement}</p>

      <div className="min-h-[30rem]">

      {view === "recent" && error ? (
        <ApiErrorNotice title="Query history could not be loaded" message={error.message} action={<Button onClick={() => void load()}><ArrowClockwiseIcon size={18} aria-hidden /> Retry</Button>} />
      ) : null}

      {view === "recent" && loading && !data ? (
        <div className="space-y-3" aria-label="Loading query history">
          {[0, 1, 2].map((item) => <Card key={item} className="h-32 animate-pulse bg-muted" />)}
        </div>
      ) : null}

      {view === "recent" && !loading && !error && data?.items.length === 0 ? (
        <EmptyState
          icon={<ClockCounterClockwiseIcon size={24} weight="duotone" />}
          title={filtered ? "No runs match these filters" : "No query runs yet"}
          description={filtered ? "Clear or adjust the filters to find another run." : "Submit a complete analytical question from Ask to create the first run."}
          action={filtered ? <Button variant="secondary" onClick={clearFilters}>Clear filters</Button> : undefined}
        />
      ) : null}

      {view === "recent" && data && data.items.length > 0 ? (
        <section aria-label="Query runs" aria-busy={loading} className="space-y-3">
          <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <p><span className="font-mono font-semibold text-text">{data.total}</span> runs</p>
            {loading ? <span role="status">Refreshing…</span> : null}
          </div>
          {data.items.map((run) => (
            <Card key={run.run_id} className="p-4 sm:p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusPill className="capitalize">{run.status.replaceAll("_", " ")}</StatusPill>
                    <span className="text-xs text-muted-foreground">{formatDate(run.created_at)}</span>
                  </div>
                  <h2 className="mt-2 [overflow-wrap:anywhere] text-base font-semibold leading-6 text-text">{run.question}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{run.datasource_name}</p>
                  <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
                    <div className="flex gap-1"><dt>Rows</dt><dd className="font-mono text-text">{run.row_count ?? "—"}</dd></div>
                    <div className="flex gap-1"><dt>Duration</dt><dd className="font-mono text-text">{formatDuration(run.duration_ms)}</dd></div>
                    <div className="flex gap-1"><dt>Repairs</dt><dd className="font-mono text-text">{run.repair_count}</dd></div>
                    <div className="flex min-w-0 gap-1"><dt>Run</dt><dd className="max-w-52 truncate font-mono text-text" title={run.run_id}>{run.run_id}</dd></div>
                  </dl>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="ghost"
                    onClick={() => void toggleDetails(run.run_id)}
                    disabled={detailLoadingId !== null}
                    aria-expanded={detail?.run_id === run.run_id}
                  >
                    {detailLoadingId === run.run_id ? <ArrowClockwiseIcon className="animate-spin" size={18} aria-hidden /> : <EyeIcon size={18} aria-hidden />}
                    {detail?.run_id === run.run_id ? "Hide details" : "View details"}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => void rerun(run.run_id, run.datasource_id, run.question)}
                    disabled={rerunningId !== null}
                  >
                    {rerunningId === run.run_id ? <ArrowClockwiseIcon className="animate-spin" size={18} aria-hidden /> : <PlayIcon size={18} aria-hidden />}
                    {rerunningId === run.run_id ? "Running…" : "Rerun as new"}
                  </Button>
                </div>
              </div>
              {detailError && detailErrorRunId === run.run_id ? (
                <p className="mt-4 border-t border-border pt-4 text-sm text-destructive" role="alert">{detailError}</p>
              ) : null}
              {detail?.run_id === run.run_id ? (
                <div className="mt-5 space-y-4 border-t border-border pt-5">
                  <QueryRunDetails run={detail} trace={detailTrace} />
                  {detail.status === "completed" ? (
                    <>
                      <div className="flex flex-wrap justify-end gap-2">
                        <SaveAnalysisDialog
                          runId={detail.run_id}
                          defaultName={detail.question}
                          onSaved={(analysis) => setSaved((current) => [analysis, ...current.filter((item) => item.id !== analysis.id)])}
                        />
                        {detail.result ? (
                          <SaveWidgetDialog
                            runId={detail.run_id}
                            defaultTitle={detail.question}
                            chartType={isChartType(detail.visualization_type) ? detail.visualization_type : "table"}
                          />
                        ) : null}
                      </div>
                      {detail.result ? <ResultVisualization result={detail.result} initialType={detail.visualization_type} /> : <p className="text-sm text-muted-foreground">The result snapshot expired, but the validated query can still be saved and rerun.</p>}
                    </>
                  ) : null}
                </div>
              ) : null}
            </Card>
          ))}

          <nav className="flex items-center justify-between gap-3 pt-2" aria-label="Query history pages">
            <Button variant="secondary" onClick={showPreviousPage} disabled={previousCursors.length === 0 || loading}>
              <CaretLeftIcon size={18} aria-hidden /> Previous
            </Button>
            <p className="text-sm text-muted-foreground">Page <span className="font-mono font-semibold text-text">{previousCursors.length + 1}</span></p>
            <Button variant="secondary" onClick={showNextPage} disabled={!data.has_more || !data.next_cursor || loading}>
              Next <CaretRightIcon size={18} aria-hidden />
            </Button>
          </nav>
        </section>
      ) : null}

      {view === "saved" ? (
        <section aria-label="Saved analyses" aria-busy={savedLoading} className="space-y-3">
          {savedError ? <ApiErrorNotice title="Saved analyses could not be loaded" message={savedError.message} action={<Button onClick={() => void loadSaved()}><ArrowClockwiseIcon size={18} aria-hidden /> Retry</Button>} /> : null}
          {savedLoading && !saved.length ? (
            <div className="space-y-3" aria-label="Loading saved analyses">
              {[0, 1, 2].map((item) => <Card key={item} className="h-32 animate-pulse bg-muted" />)}
            </div>
          ) : null}
          {!savedLoading && !savedError && saved.length === 0 ? (
            <EmptyState
              icon={<BookmarkSimpleIcon size={24} weight="duotone" />}
              title="No saved analyses yet"
              description="Save a completed result from Recent activity or Ask to keep its validated query for later."
            />
          ) : null}
          {saved.map((analysis) => (
            <Card key={analysis.id} className="p-4 sm:p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <BookmarkSimpleIcon size={18} className="text-primary" weight="duotone" aria-hidden />
                    <h2 className="[overflow-wrap:anywhere] text-base font-semibold leading-6 text-text">{analysis.name}</h2>
                  </div>
                  <p className="mt-1 [overflow-wrap:anywhere] text-sm text-muted-foreground">{analysis.question}</p>
                  <p className="mt-2 text-xs text-muted-foreground">{analysis.datasource_name} · Saved {formatDate(analysis.updated_at)}</p>
                  {analysis.description ? <p className="mt-2 text-sm text-muted-foreground">{analysis.description}</p> : null}
                  {analysis.tags.length ? <div className="mt-3 flex flex-wrap gap-2">{analysis.tags.map((tag) => <StatusPill key={tag}>{tag}</StatusPill>)}</div> : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => void rerun(analysis.id, analysis.datasource_id, analysis.question)} disabled={rerunningId !== null}>
                    {rerunningId === analysis.id ? <ArrowClockwiseIcon className="animate-spin" size={18} aria-hidden /> : <PlayIcon size={18} aria-hidden />}
                    {rerunningId === analysis.id ? "Running…" : "Run again"}
                  </Button>
                  <Button variant="ghost" onClick={() => void removeSaved(analysis)} disabled={deletingSavedId !== null}>
                    {deletingSavedId === analysis.id ? <ArrowClockwiseIcon className="animate-spin" size={18} aria-hidden /> : <TrashIcon size={18} aria-hidden />}
                    {deletingSavedId === analysis.id ? "Removing…" : "Remove"}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </section>
      ) : null}
      </div>
    </div>
  );
}

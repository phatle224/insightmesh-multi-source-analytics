"use client";

import { ArrowClockwiseIcon, ArrowDownIcon, ArrowUpIcon, ChartBarIcon, CircleNotchIcon, PencilSimpleIcon, TrashIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { ResultVisualization } from "@/components/result-visualization";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { ApiClientError } from "@/lib/api-client";
import {
  deleteDashboardWidget,
  getDashboard,
  refreshDashboardWidget,
  updateDashboardWidget,
  type DashboardDetail,
  type DashboardWidget,
} from "@/lib/dashboards";
import type { ChartType } from "@/lib/visualization";

export function DashboardDetailWorkspace({ id }: { id: string }) {
  const [dashboard, setDashboard] = useState<DashboardDetail | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      setDashboard(await getDashboard(id));
    } catch (reason) {
      setError(reason instanceof ApiClientError ? reason : null);
    }
  }
  useEffect(() => {
    let active = true;
    void getDashboard(id)
      .then((value) => {
        if (active) setDashboard(value);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof ApiClientError ? reason : null);
      });
    return () => {
      active = false;
    };
  }, [id]);

  function replaceWidget(widget: DashboardWidget) {
    setDashboard((current) => current ? { ...current, widgets: current.widgets.map((item) => item.id === widget.id ? widget : item).sort((a, b) => a.position - b.position) } : current);
  }

  async function change(widget: DashboardWidget, payload: { title?: string; chart_type?: ChartType; position?: number }) {
    setBusyId(widget.id);
    setError(null);
    try {
      replaceWidget(await updateDashboardWidget(widget.id, payload));
      if (payload.position !== undefined) await load();
    } catch (reason) {
      setError(reason instanceof ApiClientError ? reason : null);
    } finally {
      setBusyId(null);
    }
  }

  async function refresh(widget: DashboardWidget) {
    setBusyId(widget.id);
    setError(null);
    try {
      replaceWidget(await refreshDashboardWidget(widget.id));
    } catch (reason) {
      setError(reason instanceof ApiClientError ? reason : null);
    } finally {
      setBusyId(null);
    }
  }

  async function remove(widget: DashboardWidget) {
    if (!window.confirm(`Remove “${widget.title}” from this dashboard?`)) return;
    setBusyId(widget.id);
    try {
      await deleteDashboardWidget(widget.id);
      await load();
    } catch (reason) {
      setError(reason instanceof ApiClientError ? reason : null);
    } finally {
      setBusyId(null);
    }
  }

  if (error && !dashboard) return <ApiErrorNotice title="Dashboard could not be loaded" message={error.message} requestId={error.requestId} action={<Button onClick={() => void load()}>Try again</Button>} />;
  if (!dashboard) return <Card className="h-48 animate-pulse bg-muted" aria-label="Loading dashboard" />;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Saved analysis" title={dashboard.name} description={dashboard.description || "Verified results and provider-free refreshes."} action={<Button asChild variant="secondary"><Link href="/ask">Add from Ask</Link></Button>} />
      {error ? <ApiErrorNotice title="Widget action failed" message={error.message} requestId={error.requestId} /> : null}
      {dashboard.widgets.length === 0 ? (
        <EmptyState icon={<ChartBarIcon size={24} weight="duotone" />} title="This dashboard is empty" description="Run a complete analytical question, then save its verified result here." action={<Button asChild><Link href="/ask">Open Ask workspace</Link></Button>} />
      ) : (
        <div className="grid gap-6">
          {dashboard.widgets.map((widget, index) => (
            <Card key={widget.id} className="min-w-0 p-4 sm:p-5">
              <div className="flex flex-col items-stretch gap-3 border-b border-border pb-4">
                <div className="w-full min-w-0 flex-1">
                  <form onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); void change(widget, { title: String(data.get("title") || widget.title) }); }} className="flex w-full max-w-2xl gap-2">
                    <label className="sr-only" htmlFor={`title-${widget.id}`}>Widget title</label>
                    <input id={`title-${widget.id}`} name="title" defaultValue={widget.title} maxLength={160} className="min-h-10 min-w-0 flex-1 rounded-md border border-transparent bg-transparent px-2 text-lg font-semibold text-text hover:border-border focus:border-primary" />
                    <Button type="submit" size="icon" variant="ghost" aria-label={`Rename ${widget.title}`} disabled={busyId === widget.id}><PencilSimpleIcon size={18} aria-hidden /></Button>
                  </form>
                  <p className="mt-1 text-sm text-muted-foreground">{widget.question}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <StatusPill>{widget.status}</StatusPill>
                    <span>{widget.row_count ?? 0} rows</span>
                    <span>{widget.duration_ms ?? 0} ms</span>
                    {widget.last_refreshed_at ? <span>Refreshed {new Date(widget.last_refreshed_at).toLocaleString()}</span> : null}
                  </div>
                </div>
                <div className="flex w-full flex-wrap justify-end gap-1">
                  <Button size="icon" variant="ghost" aria-label="Move widget up" disabled={index === 0 || busyId === widget.id} onClick={() => void change(widget, { position: index - 1 })}><ArrowUpIcon size={18} aria-hidden /></Button>
                  <Button size="icon" variant="ghost" aria-label="Move widget down" disabled={index === dashboard.widgets.length - 1 || busyId === widget.id} onClick={() => void change(widget, { position: index + 1 })}><ArrowDownIcon size={18} aria-hidden /></Button>
                  <Button variant="secondary" size="small" disabled={busyId === widget.id} onClick={() => void refresh(widget)}>
                    {busyId === widget.id ? <CircleNotchIcon className="animate-spin" size={17} aria-hidden /> : <ArrowClockwiseIcon size={17} aria-hidden />} Refresh
                  </Button>
                  <Button size="icon" variant="ghost" aria-label={`Remove ${widget.title}`} disabled={busyId === widget.id} onClick={() => void remove(widget)}><TrashIcon className="text-destructive" size={18} aria-hidden /></Button>
                </div>
              </div>
              {widget.error ? <p className="my-4 rounded-md border border-accent/40 bg-accent/5 p-3 text-sm text-muted-foreground" role="status">Refresh failed: {widget.error.message}. The last successful result remains visible.</p> : null}
              <div className="mt-4">
                {widget.result ? <ResultVisualization result={widget.result} selectedType={widget.chart_type} onTypeChange={(chart_type) => void change(widget, { chart_type })} /> : <p className="py-8 text-center text-sm text-muted-foreground">No successful result is available.</p>}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

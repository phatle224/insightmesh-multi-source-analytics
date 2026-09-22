"use client";

import { FloppyDiskIcon, XIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiClientError } from "@/lib/api-client";
import { addDashboardWidget, createDashboard, listDashboards, type DashboardSummary } from "@/lib/dashboards";
import type { ChartType, DashboardRecommendation } from "@/lib/visualization";

export function SaveWidgetDialog({
  runId,
  savedAnalysisId,
  defaultTitle,
  chartType,
  recommendation,
}: {
  runId?: string;
  savedAnalysisId?: string;
  defaultTitle: string;
  chartType: ChartType;
  recommendation?: DashboardRecommendation;
}) {
  const [open, setOpen] = useState(false);
  const [dashboards, setDashboards] = useState<DashboardSummary[]>([]);
  const [dashboardId, setDashboardId] = useState("");
  const [title, setTitle] = useState(defaultTitle.slice(0, 160));
  const [pending, setPending] = useState(false);
  const [creatingDashboard, setCreatingDashboard] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", close);
    void listDashboards()
      .then((items) => {
        setDashboards(items);
        setDashboardId((current) => current || items[0]?.id || "");
      })
      .catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Dashboards could not be loaded."));
    window.setTimeout(() => titleRef.current?.focus(), 0);
    return () => window.removeEventListener("keydown", close);
  }, [open]);

  async function save() {
    if (!dashboardId || !title.trim()) return;
    setPending(true);
    setMessage(null);
    try {
      await addDashboardWidget(dashboardId, {
        ...(runId ? { query_run_id: runId } : { saved_analysis_id: savedAnalysisId }),
        title: title.trim(),
        chart_type: chartType,
      });
      setMessage("Saved to dashboard.");
    } catch (error) {
      setMessage(error instanceof ApiClientError ? error.message : "The result could not be saved.");
    } finally {
      setPending(false);
    }
  }

  async function createRecommendedDashboard() {
    if (!recommendation || recommendation.fit !== "recommended") return;
    setCreatingDashboard(true);
    setMessage(null);
    try {
      const dashboard = await createDashboard(
        recommendation.dashboardName,
        recommendation.dashboardDescription,
      );
      await addDashboardWidget(dashboard.id, {
        ...(runId ? { query_run_id: runId } : { saved_analysis_id: savedAnalysisId }),
        title: defaultTitle.slice(0, 160),
        chart_type: chartType,
      });
      setDashboards((current) => [dashboard, ...current]);
      setDashboardId(dashboard.id);
      setMessage(`Created ${dashboard.name} and saved this result as a ${chartType} widget.`);
    } catch (error) {
      setMessage(error instanceof ApiClientError ? error.message : "The recommended dashboard could not be created.");
    } finally {
      setCreatingDashboard(false);
    }
  }

  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <FloppyDiskIcon size={18} aria-hidden /> Save to dashboard
      </Button>
      {open ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-text/45 p-4" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}>
          <div className="w-full max-w-lg rounded-lg border border-border bg-card p-5 shadow-float" role="dialog" aria-modal="true" aria-labelledby="save-widget-title">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="save-widget-title" className="text-lg font-semibold text-text">Save verified result</h2>
                <p className="mt-1 text-sm text-muted-foreground">The stored query can refresh later without an LLM call.</p>
              </div>
              <Button size="icon" variant="ghost" aria-label="Close save dialog" onClick={() => setOpen(false)}>
                <XIcon size={18} aria-hidden />
              </Button>
            </div>
            {dashboards.length ? (
              <div className="mt-5 space-y-4">
                {recommendation ? (
                  <div className={recommendation.fit === "recommended" ? "rounded-md border border-primary/30 bg-primary/5 p-3 text-sm" : "rounded-md border border-accent/35 bg-accent/5 p-3 text-sm"} role="status">
                    <p className="font-semibold text-text">{recommendation.fit === "recommended" ? "Recommended dashboard" : "Dashboard fit"}</p>
                    <p className="mt-1 text-muted-foreground">{recommendation.message}</p>
                  </div>
                ) : null}
                <label className="block text-sm font-semibold text-text">
                  Dashboard
                  <select value={dashboardId} onChange={(event) => setDashboardId(event.target.value)} className="mt-1 min-h-11 w-full rounded-md border border-border bg-card px-3 font-normal">
                    {dashboards.map((dashboard) => <option key={dashboard.id} value={dashboard.id}>{dashboard.name}</option>)}
                  </select>
                </label>
                <label className="block text-sm font-semibold text-text">
                  Widget title
                  <input ref={titleRef} value={title} onChange={(event) => setTitle(event.target.value)} maxLength={160} className="mt-1 min-h-11 w-full rounded-md border border-border bg-card px-3 font-normal" />
                </label>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-muted-foreground" role="status">{message}</p>
                  <div className="flex flex-wrap justify-end gap-2">
                    {recommendation?.fit === "recommended" ? <Button variant="secondary" onClick={() => void createRecommendedDashboard()} disabled={pending || creatingDashboard}>{creatingDashboard ? "Creating…" : "Create recommended dashboard"}</Button> : null}
                    <Button onClick={() => void save()} disabled={pending || creatingDashboard || !dashboardId || !title.trim()}>
                      {pending ? "Saving…" : "Save widget"}
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-5 rounded-md bg-muted p-4">
                {recommendation ? <p className="text-sm text-muted-foreground">{recommendation.message}</p> : <p className="text-sm text-muted-foreground">Create a dashboard before saving this result.</p>}
                {recommendation?.fit === "recommended" ? (
                  <Button className="mt-3" onClick={() => void createRecommendedDashboard()} disabled={creatingDashboard}>{creatingDashboard ? "Creating…" : "Create dashboard and save result"}</Button>
                ) : (
                  <Button asChild variant="secondary" className="mt-3"><Link href="/dashboards">Create dashboard</Link></Button>
                )}
                {message ? <p className="mt-3 text-sm text-destructive" role="alert">{message}</p> : null}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}

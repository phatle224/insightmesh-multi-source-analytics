"use client";

import { ChartBarIcon, CircleNotchIcon, PlusIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiClientError } from "@/lib/api-client";
import { createDashboard, listDashboards, type DashboardSummary } from "@/lib/dashboards";

export function DashboardsWorkspace() {
  const [dashboards, setDashboards] = useState<DashboardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<ApiClientError | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setDashboards(await listDashboards());
    } catch (reason) {
      setError(reason instanceof ApiClientError ? reason : null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    void listDashboards()
      .then((items) => {
        if (active) setDashboards(items);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof ApiClientError ? reason : null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const dashboard = await createDashboard(name.trim(), description.trim());
      setDashboards((current) => [dashboard, ...current]);
      setName("");
      setDescription("");
    } catch (reason) {
      setError(reason instanceof ApiClientError ? reason : null);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Saved analysis"
        title="Dashboards"
        description="Keep verified results together and refresh stored read-only queries without another LLM call."
      />
      <Card className="p-4 sm:p-5">
        <form onSubmit={submit} className="grid gap-4 lg:grid-cols-[minmax(12rem,1fr)_minmax(16rem,2fr)_auto] lg:items-end">
          <label className="text-sm font-semibold text-text">Dashboard name
            <input value={name} onChange={(event) => setName(event.target.value)} maxLength={160} required className="mt-1 min-h-11 w-full rounded-md border border-border bg-card px-3 font-normal" placeholder="Executive overview" />
          </label>
          <label className="text-sm font-semibold text-text">Description <span className="font-normal text-muted-foreground">(optional)</span>
            <input value={description} onChange={(event) => setDescription(event.target.value)} maxLength={1000} className="mt-1 min-h-11 w-full rounded-md border border-border bg-card px-3 font-normal" placeholder="Key metrics for weekly review" />
          </label>
          <Button type="submit" disabled={creating || !name.trim()}>
            {creating ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : <PlusIcon size={18} aria-hidden />}
            {creating ? "Creating…" : "Create dashboard"}
          </Button>
        </form>
      </Card>
      {error ? <ApiErrorNotice title="Dashboard request failed" message={error.message} requestId={error.requestId} action={<Button onClick={() => void load()}>Try again</Button>} /> : null}
      {loading ? <Card className="h-40 animate-pulse bg-muted" aria-label="Loading dashboards" /> : dashboards.length === 0 ? (
        <EmptyState icon={<ChartBarIcon size={24} weight="duotone" />} title="No dashboards yet" description="Create one here, then save any completed result from the Ask workspace." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {dashboards.map((dashboard) => (
            <Link key={dashboard.id} href={`/dashboards/${dashboard.id}`} className="rounded-lg focus:outline-none focus-visible:ring-3 focus-visible:ring-primary/30">
              <Card className="h-full p-5 transition-colors hover:border-border-strong">
                <div className="flex items-start justify-between gap-3">
                  <ChartBarIcon className="text-primary" size={24} weight="duotone" aria-hidden />
                  <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground">{dashboard.widget_count} widgets</span>
                </div>
                <h2 className="mt-4 text-lg font-semibold text-text">{dashboard.name}</h2>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{dashboard.description || "Saved verified analysis"}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

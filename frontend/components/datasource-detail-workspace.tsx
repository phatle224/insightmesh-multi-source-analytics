"use client";

import {
  ArrowClockwiseIcon,
  ArrowLeftIcon,
  CheckIcon,
  CircleNotchIcon,
  KeyIcon,
} from "@phosphor-icons/react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { useDatasources } from "@/components/datasource-provider";
import { PageHeader } from "@/components/page-header";
import { SourceStatus } from "@/components/source-status";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiClientError } from "@/lib/api-client";
import {
  activateDatasource,
  getDatasource,
  refreshDatasource,
  type DatasourceDetail,
} from "@/lib/datasources";

function displayError(reason: unknown) {
  return reason instanceof ApiClientError
    ? reason
    : new ApiClientError(
        { error: { code: "network_error", message: "Datasource details could not be loaded.", retryable: true }, request_id: "unavailable" },
        0,
      );
}

export function DatasourceDetailWorkspace({ id }: { id: string }) {
  const { refresh: refreshList } = useDatasources();
  const [source, setSource] = useState<DatasourceDetail | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<"activate" | "refresh" | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setSource(await getDatasource(id)); }
    catch (reason) { setError(displayError(reason)); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => {
    let active = true;
    getDatasource(id)
      .then((detail) => {
        if (active) setSource(detail);
      })
      .catch((reason: unknown) => {
        if (active) setError(displayError(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  async function runAction(nextAction: "activate" | "refresh") {
    setAction(nextAction); setError(null);
    try {
      const updated = await (nextAction === "activate" ? activateDatasource(id) : refreshDatasource(id));
      setSource(updated);
      await refreshList();
    } catch (reason) { setError(displayError(reason)); }
    finally { setAction(null); }
  }

  if (loading && !source) return <Card className="h-80 animate-pulse bg-muted" aria-label="Loading datasource details" />;
  if (error && !source) return <ApiErrorNotice title="Datasource unavailable" message={error.message} requestId={error.requestId} action={<Button onClick={() => void load()}>Try again</Button>} />;
  if (!source) return null;

  return (
    <div className="space-y-6">
      <Link href="/sources" className="inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-semibold text-primary hover:text-primary-hover"><ArrowLeftIcon size={18} aria-hidden /> Back to sources</Link>
      <PageHeader eyebrow="PostgreSQL datasource" title={source.name} description={`${source.safe_host}:${source.port} / ${source.database_name}`} action={<div className="flex flex-wrap gap-2"><SourceStatus status={source.status} />{source.is_active ? <span className="rounded-full bg-primary px-2.5 py-1 text-xs font-semibold text-on-primary">Active</span> : null}</div>} />
      {error ? <ApiErrorNotice title="Datasource action failed" message={error.message} requestId={error.requestId} /> : null}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <h2 className="font-semibold text-text">Safe connection summary</h2>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
            <div><dt className="text-muted-foreground">Database</dt><dd className="mt-1 font-medium">{source.database_name}</dd></div>
            <div><dt className="text-muted-foreground">SSL mode</dt><dd className="mt-1 font-medium">{source.ssl_mode}</dd></div>
            <div><dt className="text-muted-foreground">Allowed schemas</dt><dd className="mt-1 font-mono text-xs">{source.allowed_schemas.join(", ")}</dd></div>
            <div><dt className="text-muted-foreground">Last metadata refresh</dt><dd className="mt-1 font-medium">{source.last_refreshed_at ? new Date(source.last_refreshed_at).toLocaleString() : "Not completed"}</dd></div>
          </dl>
        </Card>
        <Card className="p-5">
          <h2 className="font-semibold text-text">Actions</h2>
          <p className="mt-2 text-sm text-muted-foreground">Refresh re-discovers schema metadata using the stored encrypted credential.</p>
          <div className="mt-5 flex flex-col gap-2">
            {!source.is_active && source.status === "ready" ? <Button onClick={() => void runAction("activate")} disabled={action !== null}>{action === "activate" ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : <CheckIcon size={18} aria-hidden />} Activate source</Button> : null}
            <Button variant="secondary" onClick={() => void runAction("refresh")} disabled={action !== null}>{action === "refresh" ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : <ArrowClockwiseIcon size={18} aria-hidden />} Refresh metadata</Button>
          </div>
        </Card>
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
        <Card className="overflow-hidden">
          <div className="border-b border-border px-5 py-4"><h2 className="font-semibold text-text">Discovered entities</h2><p className="mt-1 text-sm text-muted-foreground">{source.entity_count} entities found through read-only introspection.</p></div>
          <div className="divide-y divide-border">
            {source.entities.map((entity) => <details key={entity.id} className="group px-5 py-3"><summary className="flex min-h-11 items-center justify-between gap-3 font-semibold text-text"><span>{entity.schema_name}.{entity.name}</span><span className="text-xs font-normal text-muted-foreground">{entity.fields.length} fields</span></summary><div className="overflow-x-auto pb-3"><table className="w-full min-w-lg text-left text-sm"><thead className="text-xs uppercase tracking-wide text-muted-foreground"><tr><th className="py-2 pr-4">Field</th><th className="py-2 pr-4">Type</th><th className="py-2">Constraints</th></tr></thead><tbody>{entity.fields.map((field) => <tr key={field.id} className="border-t border-border"><td className="py-2 pr-4 font-mono text-xs">{field.name}</td><td className="py-2 pr-4">{field.native_type}</td><td className="py-2">{field.primary_key ? <span className="inline-flex items-center gap-1"><KeyIcon size={14} aria-hidden />Primary key</span> : field.unique ? "Unique" : field.nullable ? "Nullable" : "Required"}</td></tr>)}</tbody></table></div></details>)}
          </div>
        </Card>
        <Card className="p-5">
          <h2 className="font-semibold text-text">Relationships</h2>
          <p className="mt-1 text-sm text-muted-foreground">{source.relationship_count} foreign-key relationships.</p>
          {source.relationships.length ? <ul className="mt-4 space-y-3">{source.relationships.map((relationship) => <li key={relationship.id} className="rounded-md border border-border bg-background p-3 text-sm"><p className="font-mono text-xs text-primary">{relationship.source}</p><p className="my-1 text-muted-foreground">references</p><p className="font-mono text-xs text-text">{relationship.target}</p></li>)}</ul> : <p className="mt-4 text-sm text-muted-foreground">No foreign keys were discovered.</p>}
        </Card>
      </div>
    </div>
  );
}

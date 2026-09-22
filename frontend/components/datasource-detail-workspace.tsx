"use client";

import {
  ArrowClockwiseIcon,
  ArrowLeftIcon,
  CheckIcon,
  CircleNotchIcon,
  DatabaseIcon,
  KeyIcon,
  PencilSimpleIcon,
  ShieldCheckIcon,
  SparkleIcon,
  TrashIcon,
  XIcon,
} from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { useDatasources } from "@/components/datasource-provider";
import { PageHeader } from "@/components/page-header";
import { RelationshipExplorer } from "@/components/relationship-explorer";
import { SemanticManifestPanel } from "@/components/semantic-manifest-panel";
import { SourceStatus } from "@/components/source-status";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiClientError } from "@/lib/api-client";
import {
  activateDatasource,
  deleteDatasource,
  getDatasource,
  renameDatasource,
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

function profileSummary(profile: Record<string, unknown> | null) {
  if (!profile) return "Not profiled";
  if (profile.excluded) return "Excluded by privacy policy";
  const parts: string[] = [];
  if (typeof profile.distinct_count === "number") parts.push(`${profile.distinct_count} distinct`);
  if (typeof profile.null_ratio === "number") parts.push(`${Math.round(profile.null_ratio * 100)}% null`);
  if (profile.minimum !== undefined && profile.minimum !== null) parts.push(`min ${String(profile.minimum)}`);
  if (profile.maximum !== undefined && profile.maximum !== null) parts.push(`max ${String(profile.maximum)}`);
  if (Array.isArray(profile.candidate_values)) parts.push(`values: ${profile.candidate_values.map(String).join(", ")}`);
  return parts.join(" · ") || "Profile available";
}

const semanticStatusCopy: Record<DatasourceDetail["semantic_status"], string> = {
  not_configured: "Not configured",
  configuration_required: "API key required",
  indexing: "Indexing",
  ready: "Searchable",
  stale: "Stale index retained",
  failed: "Index unavailable",
};

export function DatasourceDetailWorkspace({ id }: { id: string }) {
  const router = useRouter();
  const { refresh: refreshList } = useDatasources();
  const [source, setSource] = useState<DatasourceDetail | null>(null);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<"activate" | "refresh" | "rename" | "delete" | null>(null);
  const [editing, setEditing] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");

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

  function startEditing() {
    setDraftName(source?.name ?? "");
    setConfirmDelete(false);
    setDeleteConfirmation("");
    setEditing(true);
    setError(null);
  }

  function cancelEditing() {
    setEditing(false);
    setConfirmDelete(false);
    setDeleteConfirmation("");
  }

  async function saveName() {
    const name = draftName.trim();
    if (!source || !name || name === source.name) return;
    setAction("rename"); setError(null);
    try {
      const updated = await renameDatasource(id, name);
      setSource(updated);
      await refreshList();
      setEditing(false);
    } catch (reason) { setError(displayError(reason)); }
    finally { setAction(null); }
  }

  async function removeSource() {
    if (!source || deleteConfirmation.trim() !== source.name) return;
    setAction("delete"); setError(null);
    try {
      await deleteDatasource(id);
      await refreshList();
      router.push("/sources");
    } catch (reason) { setError(displayError(reason)); }
    finally { setAction(null); }
  }

  if (loading && !source) return <Card className="h-80 animate-pulse bg-muted" aria-label="Loading datasource details" />;
  if (error && !source) return <ApiErrorNotice title="Datasource unavailable" message={error.message} requestId={error.requestId} action={<Button onClick={() => void load()}>Try again</Button>} />;
  if (!source) return null;

  return (
    <div className="space-y-6">
      <Link href="/sources" className="inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-semibold text-primary hover:text-primary-hover"><ArrowLeftIcon size={18} aria-hidden /> Back to sources</Link>
      <PageHeader eyebrow={`${source.source_type === "mysql" ? "MySQL" : "PostgreSQL"} datasource`} title={source.name} description={`${source.safe_host}:${source.port} / ${source.database_name}`} action={<div className="flex flex-wrap gap-2"><SourceStatus status={source.status} />{source.is_active ? <span className="rounded-full bg-primary px-2.5 py-1 text-xs font-semibold text-on-primary">Active</span> : null}</div>} />
      {error ? <ApiErrorNotice title="Datasource action failed" message={error.message} requestId={error.requestId} /> : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-5"><DatabaseIcon size={20} className="text-primary" aria-hidden /><p className="mt-3 text-2xl font-semibold text-text">{source.profile_count}</p><p className="text-sm text-muted-foreground">Fields profiled locally</p></Card>
        <Card className="p-5"><ShieldCheckIcon size={20} className="text-primary" aria-hidden /><p className="mt-3 text-2xl font-semibold text-text">{source.pii_excluded_count}</p><p className="text-sm text-muted-foreground">Fields excluded as possible PII</p></Card>
        <Card className="p-5"><SparkleIcon size={20} className="text-primary" aria-hidden /><p className="mt-3 text-base font-semibold text-text">{semanticStatusCopy[source.semantic_status]}</p><p className="text-sm text-muted-foreground">Semantic index · {source.embedding_count} embeddings</p></Card>
        <Card className="p-5"><p className="text-2xl font-semibold text-text">{source.semantic_term_count + source.metric_count}</p><p className="mt-1 text-sm text-muted-foreground">Inferred terms and metric candidates</p></Card>
      </div>
      {source.semantic_status === "configuration_required" ? <Card className="border-accent/40 bg-accent/5 p-4 text-sm"><p className="font-semibold text-text">Semantic indexing is waiting for configuration</p><p className="mt-1 text-muted-foreground">Local metadata and profiling completed. Add an OpenRouter API key, then refresh this datasource to build the searchable index.</p></Card> : null}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <h2 className="font-semibold text-text">Safe connection summary</h2>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
            <div><dt className="text-muted-foreground">Database</dt><dd className="mt-1 font-medium">{source.database_name}</dd></div>
            <div><dt className="text-muted-foreground">SSL mode</dt><dd className="mt-1 font-medium">{source.ssl_mode}</dd></div>
            <div><dt className="text-muted-foreground">{source.source_type === "mysql" ? "Allowed databases" : "Allowed schemas"}</dt><dd className="mt-1 font-mono text-xs">{source.allowed_schemas.join(", ")}</dd></div>
            <div><dt className="text-muted-foreground">Last metadata refresh</dt><dd className="mt-1 font-medium">{source.last_refreshed_at ? new Date(source.last_refreshed_at).toLocaleString() : "Not completed"}</dd></div>
          </dl>
        </Card>
        <Card className="p-5">
          <h2 className="font-semibold text-text">Actions</h2>
          <p className="mt-2 text-sm text-muted-foreground">Refresh re-discovers schema metadata using the stored encrypted credential.</p>
          <div className="mt-5 flex flex-col gap-2">
            {!source.is_active && source.status === "ready" ? <Button onClick={() => void runAction("activate")} disabled={action !== null}>{action === "activate" ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : <CheckIcon size={18} aria-hidden />} Activate source</Button> : null}
            <Button variant="secondary" onClick={() => void runAction("refresh")} disabled={action !== null}>{action === "refresh" ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : <ArrowClockwiseIcon size={18} aria-hidden />} Refresh metadata</Button>
            <Button variant="ghost" onClick={startEditing} disabled={action !== null}><PencilSimpleIcon size={18} aria-hidden /> Edit source</Button>
          </div>
        </Card>
      </div>
      {editing ? (
        <Card className="border-primary/30 p-5" role="region" aria-labelledby="edit-source-heading">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 id="edit-source-heading" className="font-semibold text-text">Edit source</h2>
              <p className="mt-1 text-sm text-muted-foreground">Update the display name or remove this connection.</p>
            </div>
            <Button size="icon" variant="ghost" aria-label="Close edit source panel" onClick={cancelEditing} disabled={action !== null}><XIcon size={18} aria-hidden /></Button>
          </div>
          <form className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={(event) => { event.preventDefault(); void saveName(); }}>
            <div className="min-w-0 flex-1">
              <label htmlFor="datasource-name" className="text-sm font-medium text-text">Source name</label>
              <input id="datasource-name" name="name" value={draftName} onChange={(event) => setDraftName(event.target.value)} maxLength={120} required autoFocus className="mt-2 min-h-11 w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-text shadow-sm placeholder:text-muted-foreground" />
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="ghost" onClick={cancelEditing} disabled={action !== null}>Cancel</Button>
              <Button type="submit" disabled={action !== null || !draftName.trim() || draftName.trim() === source.name}>{action === "rename" ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : <CheckIcon size={18} aria-hidden />} Save name</Button>
            </div>
          </form>
          <div className="mt-6 border-t border-border pt-5">
            <h3 className="font-semibold text-destructive">Delete source</h3>
            <p className="mt-1 text-sm text-muted-foreground">This removes the stored connection and discovered metadata. Dashboard widgets using it must be removed first.</p>
            {!confirmDelete ? (
              <Button variant="ghost" className="mt-3 text-destructive hover:bg-destructive/5 hover:text-destructive" onClick={() => setConfirmDelete(true)} disabled={action !== null}><TrashIcon size={18} aria-hidden /> Delete source</Button>
            ) : (
              <div className="mt-4 rounded-md border border-destructive/30 bg-destructive/5 p-4" role="alert">
                <p className="text-sm text-destructive">To confirm, type <strong>{source.name}</strong> exactly.</p>
                <label htmlFor="delete-source-confirmation" className="sr-only">Type the source name to confirm deletion</label>
                <input id="delete-source-confirmation" value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} className="mt-3 min-h-11 w-full rounded-md border border-border bg-card px-3 py-2 text-sm text-text shadow-sm" autoComplete="off" />
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button type="button" variant="ghost" onClick={() => { setConfirmDelete(false); setDeleteConfirmation(""); }} disabled={action !== null}>Keep source</Button>
                  <Button type="button" variant="primary" className="bg-destructive text-on-destructive hover:bg-destructive/90" onClick={() => void removeSource()} disabled={action !== null || deleteConfirmation.trim() !== source.name}>{action === "delete" ? <CircleNotchIcon className="animate-spin" size={18} aria-hidden /> : <TrashIcon size={18} aria-hidden />} Delete permanently</Button>
                </div>
              </div>
            )}
          </div>
        </Card>
      ) : null}
      <div>
        <Card className="overflow-hidden">
          <div className="border-b border-border px-5 py-4"><h2 className="font-semibold text-text">Discovered entities</h2><p className="mt-1 text-sm text-muted-foreground">{source.entity_count} entities found through read-only introspection.</p></div>
          <div className="max-h-[65vh] overflow-y-auto overscroll-contain divide-y divide-border focus-visible:outline-primary" tabIndex={0} aria-label="Discovered entities list">
            {source.entities.map((entity) => <details key={entity.id} className="group px-5 py-3"><summary className="flex min-h-11 items-center justify-between gap-3 font-semibold text-text"><span>{entity.schema_name}.{entity.name}</span><span className="text-xs font-normal text-muted-foreground">{entity.fields.length} fields</span></summary>{entity.description ? <p className="mb-2 text-sm text-muted-foreground">{entity.description}</p> : null}{entity.business_terms.length || entity.metrics.length ? <div className="mb-3 flex flex-wrap gap-2">{entity.business_terms.map((term) => <span key={term} className="rounded-full bg-muted px-2 py-1 text-xs text-muted-foreground">{term}</span>)}{entity.metrics.map((metric) => <span key={metric} className="rounded-full border border-border px-2 py-1 text-xs text-text">Metric: {metric}</span>)}</div> : null}<div className="overflow-x-auto pb-3"><table className="w-full min-w-[48rem] text-left text-sm"><thead className="text-xs uppercase tracking-wide text-muted-foreground"><tr><th className="py-2 pr-4">Field</th><th className="py-2 pr-4">Type</th><th className="py-2 pr-4">Constraints</th><th className="py-2">Safe profile</th></tr></thead><tbody>{entity.fields.map((field) => <tr key={field.id} className="border-t border-border align-top"><td className="py-2 pr-4"><p className="font-mono text-xs">{field.name}</p>{field.description ? <p className="mt-1 max-w-xs text-xs text-muted-foreground">{field.description}</p> : null}</td><td className="py-2 pr-4">{field.native_type}</td><td className="py-2 pr-4">{field.primary_key ? <span className="inline-flex items-center gap-1"><KeyIcon size={14} aria-hidden />Primary key</span> : field.unique ? "Unique" : field.nullable ? "Nullable" : "Required"}</td><td className="max-w-sm py-2 text-xs text-muted-foreground"><span className={field.profile_excluded ? "font-medium text-accent" : ""}>{profileSummary(field.profile)}</span>{field.profile_sample_size !== null && !field.profile_excluded ? <span className="mt-1 block">Sample: up to {field.profile_sample_size} rows</span> : null}</td></tr>)}</tbody></table></div></details>)}
          </div>
        </Card>
      </div>
      <RelationshipExplorer datasourceId={source.id} entities={source.entities} relationships={source.relationships} />
      <SemanticManifestPanel key={source.updated_at} datasourceId={source.id} />
    </div>
  );
}

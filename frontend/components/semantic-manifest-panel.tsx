"use client";

import {
  CircleNotchIcon,
  DownloadSimpleIcon,
  FileCodeIcon,
  ShieldCheckIcon,
} from "@phosphor-icons/react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiClientError } from "@/lib/api-client";
import { getSemanticManifest, type SemanticManifest } from "@/lib/datasources";

function shortHash(value: string) {
  return `${value.slice(0, 10)}…${value.slice(-6)}`;
}

function safeFilename(name: string) {
  const normalized = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return normalized || "datasource";
}

function downloadManifest(manifest: SemanticManifest) {
  const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `insightmesh-${safeFilename(manifest.datasource_name)}-semantic-manifest-v${manifest.version}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function SemanticManifestPanel({ datasourceId }: { datasourceId: string }) {
  const [manifest, setManifest] = useState<SemanticManifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getSemanticManifest(datasourceId)
      .then((result) => {
        if (active) setManifest(result);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(
          reason instanceof ApiClientError
            ? reason.message
            : "The semantic manifest could not be loaded.",
        );
      });
    return () => {
      active = false;
    };
  }, [datasourceId]);

  if (error) {
    return (
      <Card className="p-5">
        <h2 className="font-semibold text-text">Semantic manifest</h2>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
      </Card>
    );
  }

  if (!manifest) {
    return (
      <Card className="flex min-h-28 items-center gap-3 p-5" aria-label="Loading semantic manifest">
        <CircleNotchIcon className="animate-spin text-primary" size={20} aria-hidden />
        <span className="text-sm text-muted-foreground">Loading privacy-safe manifest…</span>
      </Card>
    );
  }

  const fieldCount = manifest.entities.reduce((total, entity) => total + entity.fields.length, 0);
  const termCount = manifest.entities.reduce(
    (total, entity) =>
      total +
      entity.semantic_terms.length +
      entity.fields.reduce((fieldTotal, field) => fieldTotal + field.semantic_terms.length, 0),
    0,
  );
  const metricCount = manifest.entities.reduce(
    (total, entity) => total + entity.metrics.length,
    0,
  );

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-4 border-b border-border px-5 py-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <FileCodeIcon size={20} className="text-primary" aria-hidden />
            <h2 className="font-semibold text-text">Semantic manifest</h2>
            <span className="rounded-full bg-primary/10 px-2 py-1 text-xs font-semibold text-primary">
              v{manifest.version}
            </span>
          </div>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Immutable, reproducible semantic context. Export includes safe profiles and artifact IDs,
            never credentials, raw rows, embedding vectors, or raw PII.
          </p>
        </div>
        <Button variant="secondary" onClick={() => downloadManifest(manifest)}>
          <DownloadSimpleIcon size={18} aria-hidden /> Export JSON
        </Button>
      </div>
      <div className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Entities", manifest.entities.length],
          ["Fields", fieldCount],
          ["Terms and metrics", termCount + metricCount],
          ["Relationships", manifest.relationships.length],
        ].map(([label, value]) => (
          <div key={label} className="bg-card px-5 py-4">
            <p className="text-xl font-semibold text-text">{value}</p>
            <p className="text-xs text-muted-foreground">{label}</p>
          </div>
        ))}
      </div>
      <details className="group px-5 py-3">
        <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 font-semibold text-text">
          <span>Version and configuration</span>
          <span className="font-mono text-xs font-normal text-muted-foreground">
            {shortHash(manifest.manifest_hash)}
          </span>
        </summary>
        <div className="grid gap-4 pb-3 text-sm sm:grid-cols-2 xl:grid-cols-3">
          <div><p className="text-muted-foreground">Generated</p><p className="mt-1">{new Date(manifest.created_at).toLocaleString()}</p></div>
          <div><p className="text-muted-foreground">Generation model</p><p className="mt-1 font-mono text-xs">{manifest.configuration.generation_provider} / {manifest.configuration.generation_model}</p></div>
          <div><p className="text-muted-foreground">Fallback model</p><p className="mt-1 font-mono text-xs">{manifest.configuration.fallback_provider} / {manifest.configuration.fallback_model}</p></div>
          <div><p className="text-muted-foreground">Embedding model</p><p className="mt-1 font-mono text-xs">{manifest.configuration.embedding_model} ({manifest.configuration.embedding_dimensions}d)</p></div>
          <div><p className="text-muted-foreground">Metadata hash</p><p className="mt-1 font-mono text-xs" title={manifest.metadata_hash}>{shortHash(manifest.metadata_hash)}</p></div>
          <div><p className="text-muted-foreground">Profile hash</p><p className="mt-1 font-mono text-xs" title={manifest.profile_hash}>{shortHash(manifest.profile_hash)}</p></div>
        </div>
        <div className="mb-3 flex items-start gap-2 rounded-md border border-border bg-background p-3 text-xs text-muted-foreground">
          <ShieldCheckIcon size={18} className="shrink-0 text-primary" aria-hidden />
          <span>Privacy policy {manifest.configuration.privacy_policy_version}; inferred joins require {Math.round(manifest.configuration.relationship_inferred_min_confidence * 100)}% confidence.</span>
        </div>
      </details>
    </Card>
  );
}

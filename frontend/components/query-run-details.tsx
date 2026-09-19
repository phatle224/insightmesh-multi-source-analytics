"use client";

import {
  CheckCircleIcon,
  ClipboardIcon,
  CodeIcon,
  GitBranchIcon,
} from "@phosphor-icons/react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import type { GeneratedQuery, QueryRun, QueryTrace } from "@/lib/query-runs";

const SQL_KEYWORD = /^(select|from|where|join|inner|left|right|full|on|as|group|by|order|limit|with|and|or|not|in|is|null|asc|desc|having|count|sum|avg|min|max|date_trunc|extract)$/i;
const SQL_TOKENIZER = /(\s+|[,().*+\-/]|'(?:''|[^'])*'|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][A-Za-z0-9_$]*\b)/g;

function SqlCode({ query }: { query: GeneratedQuery }) {
  const tokens = query.sql.split(SQL_TOKENIZER).filter(Boolean);
  return (
    <code>
      {tokens.map((token, index) => {
        const className = SQL_KEYWORD.test(token)
          ? "font-semibold text-secondary"
          : token.startsWith("'")
            ? "text-accent-hover"
            : /^\d/.test(token)
              ? "text-primary"
              : undefined;
        return (
          <span className={className} key={`${index}-${token}`}>
            {token}
          </span>
        );
      })}
    </code>
  );
}

function readable(value: string) {
  return value.replaceAll("_", " ");
}

export function QueryRunDetails({ run, trace }: { run: QueryRun; trace: QueryTrace | null }) {
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");

  async function copyQuery() {
    if (!run.generated_query) return;
    try {
      await navigator.clipboard.writeText(run.generated_query.sql);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }
  }

  return (
    <div className="grid min-w-0 gap-4 xl:grid-cols-2">
      <Card className="min-w-0 overflow-hidden">
        <details>
          <summary className="flex min-h-12 items-center gap-2 px-4 py-3 font-semibold text-text transition-colors hover:bg-muted/55">
            <CodeIcon size={19} aria-hidden /> Generated PostgreSQL
          </summary>
          <div className="border-t border-border p-4">
            {run.generated_query ? (
              <>
                <div className="flex flex-wrap items-center gap-2 pb-3">
                  <StatusPill>{run.validation.explain_valid ? "Validated" : "Not validated"}</StatusPill>
                  <StatusPill>{run.repair_count} repair{run.repair_count === 1 ? "" : "s"}</StatusPill>
                  {run.result ? <StatusPill>{run.result.duration_ms} ms</StatusPill> : null}
                  <Button className="ml-auto" size="small" variant="ghost" onClick={() => void copyQuery()}>
                    {copyStatus === "copied" ? (
                      <CheckCircleIcon size={17} aria-hidden />
                    ) : (
                      <ClipboardIcon size={17} aria-hidden />
                    )}
                    {copyStatus === "copied" ? "Copied" : "Copy query"}
                  </Button>
                </div>
                <pre className="max-h-96 overflow-auto rounded-md bg-sidebar p-4 font-mono text-[0.8125rem] leading-6 text-on-primary">
                  <SqlCode query={run.generated_query} />
                </pre>
                <p className="sr-only" aria-live="polite">
                  {copyStatus === "copied"
                    ? "Query copied to clipboard"
                    : copyStatus === "failed"
                      ? "Query could not be copied"
                      : ""}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">No query was generated for this run.</p>
            )}
          </div>
        </details>
      </Card>

      <Card className="min-w-0 overflow-hidden">
        <details>
          <summary className="flex min-h-12 items-center gap-2 px-4 py-3 font-semibold text-text transition-colors hover:bg-muted/55">
            <GitBranchIcon size={19} aria-hidden /> Execution trace
          </summary>
          <div className="border-t border-border p-4">
            {trace && trace.trace.length > 0 ? (
              <ol className="space-y-3">
                {trace.trace.map((event) => (
                  <li key={event.sequence} className="grid grid-cols-[1.75rem_minmax(0,1fr)] gap-2 text-sm">
                    <span className="grid size-7 place-items-center rounded-full bg-muted font-mono text-xs font-semibold text-primary">
                      {event.sequence}
                    </span>
                    <div className="min-w-0 border-b border-border pb-3 last:border-0">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-semibold capitalize text-text">{readable(event.event)}</p>
                        {event.duration_ms !== undefined ? (
                          <span className="font-mono text-xs text-muted-foreground">
                            {event.duration_ms} ms
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-xs capitalize text-muted-foreground">
                        {readable(event.state)} → {readable(event.outcome)}
                      </p>
                      {event.error_code ? (
                        <p className="mt-1 font-mono text-xs text-destructive">
                          {event.error_code}
                        </p>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-muted-foreground">Trace details are unavailable.</p>
            )}
          </div>
        </details>
      </Card>
    </div>
  );
}

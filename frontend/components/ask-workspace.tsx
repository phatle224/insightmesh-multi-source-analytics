"use client";

import {
  ArrowClockwiseIcon,
  CheckCircleIcon,
  CircleNotchIcon,
  DatabaseIcon,
  MagnifyingGlassIcon,
  QuestionIcon,
  ShieldWarningIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react";
import Link from "next/link";
import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { DatasourceContextPanel } from "@/components/datasource-context-panel";
import { useDatasources } from "@/components/datasource-provider";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { QueryRunDetails } from "@/components/query-run-details";
import { ResultVisualization } from "@/components/result-visualization";
import { SaveWidgetDialog } from "@/components/save-widget-dialog";
import { QuestionSuggestions } from "@/components/question-suggestions";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { ApiClientError } from "@/lib/api-client";
import {
  createQueryRun,
  getQueryTrace,
  type QueryRun,
  type QueryRunStatus,
  type QueryTrace,
} from "@/lib/query-runs";
import { cn } from "@/lib/utils";
import { isChartType, type ChartType } from "@/lib/visualization";

interface StatusPresentation {
  label: string;
  description: string;
  tone: "neutral" | "success" | "warning" | "danger";
}

export const RUN_STATUS_PRESENTATION: Record<QueryRunStatus, StatusPresentation> = {
  received: {
    label: "Request received",
    description: "The complete question is ready for deterministic processing.",
    tone: "neutral",
  },
  retrieve_context: {
    label: "Finding relevant context",
    description: "Selecting schema, business terms, and relationship paths.",
    tone: "neutral",
  },
  generate_query: {
    label: "Generating a read-only query",
    description: "Creating dialect-specific SQL from the retrieved context.",
    tone: "neutral",
  },
  validate_query: {
    label: "Checking query safety",
    description: "Applying AST policy and database-native EXPLAIN validation.",
    tone: "neutral",
  },
  execute_query: {
    label: "Running query",
    description: "Executing with read-only permissions, timeout, and row limits.",
    tone: "neutral",
  },
  repair_query: {
    label: "Repairing query",
    description: "Applying a bounded repair from safe validation feedback.",
    tone: "warning",
  },
  verify_result: {
    label: "Checking result shape",
    description: "Verifying columns, bounds, serialization, nulls, and truncation.",
    tone: "neutral",
  },
  select_visualization: {
    label: "Preparing result view",
    description: "Selecting a compatible deterministic presentation.",
    tone: "neutral",
  },
  completed: {
    label: "Query completed",
    description: "The result passed deterministic validation and verification.",
    tone: "success",
  },
  clarification_required: {
    label: "Clarification required",
    description: "Choose a complete question with an explicit business metric.",
    tone: "warning",
  },
  out_of_scope: {
    label: "Question outside datasource scope",
    description: "Ask an analytical question about the active datasource's known schema and metrics.",
    tone: "warning",
  },
  blocked: {
    label: "Request blocked",
    description: "The request was stopped by the read-only safety policy.",
    tone: "danger",
  },
  failed: {
    label: "Query could not be completed",
    description: "Review the safe error below, edit the question, or start a new run.",
    tone: "danger",
  },
};

const toneClasses: Record<StatusPresentation["tone"], string> = {
  neutral: "border-border-strong bg-muted/45",
  success: "border-primary/35 bg-primary/5",
  warning: "border-accent/45 bg-accent/5",
  danger: "border-destructive/45 bg-destructive/5",
};

function requestError(reason: unknown) {
  if (reason instanceof ApiClientError) return reason;
  return new ApiClientError(
    {
      error: {
        code: "network_error",
        message: "InsightMesh could not reach the query service. Check the Docker services and retry.",
        retryable: true,
      },
      request_id: "unavailable",
    },
    0,
  );
}

function RunStatus({ run }: { run: QueryRun }) {
  const presentation = RUN_STATUS_PRESENTATION[run.status];
  const Icon =
    run.status === "completed"
      ? CheckCircleIcon
      : run.status === "blocked"
          ? ShieldWarningIcon
          : run.status === "clarification_required"
            ? QuestionIcon
            : run.status === "out_of_scope"
              ? WarningCircleIcon
            : run.status === "failed"
            ? WarningCircleIcon
            : CircleNotchIcon;
  return (
    <Card className={cn("min-h-32 border p-4", toneClasses[presentation.tone])}>
      <div className="flex items-start gap-3">
        <Icon
          className={cn(
            "mt-0.5 shrink-0",
            presentation.tone === "danger" ? "text-destructive" : "text-primary",
            !["completed", "blocked", "clarification_required", "out_of_scope", "failed"].includes(run.status)
              ? "animate-spin"
              : undefined,
          )}
          size={22}
          weight="duotone"
          aria-hidden
        />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-semibold text-text">{presentation.label}</h2>
            <StatusPill className="capitalize">{run.status.replaceAll("_", " ")}</StatusPill>
          </div>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {run.error?.message ?? presentation.description}
          </p>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            Run {run.run_id}
          </p>
        </div>
      </div>
    </Card>
  );
}

function LoadingWorkspace() {
  return (
    <div className="space-y-4" aria-label="Loading Ask workspace">
      <Card className="h-20 animate-pulse bg-muted" />
      <Card className="h-44 animate-pulse bg-muted" />
      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="h-44 animate-pulse bg-muted" />
        <Card className="h-44 animate-pulse bg-muted" />
      </div>
    </div>
  );
}

export function AskWorkspace() {
  const { activeSource, loading, error, refresh } = useDatasources();
  const [question, setQuestion] = useState("");
  const [run, setRun] = useState<QueryRun | null>(null);
  const [trace, setTrace] = useState<QueryTrace | null>(null);
  const [pending, setPending] = useState(false);
  const [submitError, setSubmitError] = useState<ApiClientError | null>(null);
  const [traceError, setTraceError] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<ChartType | undefined>();
  const statusRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (run || submitError) statusRef.current?.focus();
  }, [run, submitError]);

  const semanticReady =
    activeSource?.semantic_status === "ready" || activeSource?.semantic_status === "stale";
  const canRun = Boolean(activeSource && activeSource.status === "ready" && semanticReady);

  async function submitQuestion(completeQuestion: string) {
    const normalized = completeQuestion.trim();
    if (normalized.length < 3) {
      setFieldError("Enter a complete analytical question with at least 3 characters.");
      return;
    }
    if (!activeSource || !canRun) return;
    setQuestion(normalized);
    setFieldError(null);
    setSubmitError(null);
    setTraceError(false);
    setRun(null);
    setTrace(null);
    setChartType(undefined);
    setPending(true);
    try {
      const nextRun = await createQueryRun(activeSource.id, normalized);
      setRun(nextRun);
      try {
        setTrace(await getQueryTrace(nextRun.run_id));
      } catch {
        setTraceError(true);
      }
    } catch (reason) {
      setSubmitError(requestError(reason));
    } finally {
      setPending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion(question);
  }

  function handleQuestionKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void submitQuestion(question);
    }
  }

  if (loading && !activeSource) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Independent question"
          title="Ask your data"
          description="Each run starts from one complete analytical question against the active datasource."
        />
        <LoadingWorkspace />
      </div>
    );
  }

  if (error && !activeSource) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Independent question"
          title="Ask your data"
          description="Each run starts from one complete analytical question against the active datasource."
        />
        <ApiErrorNotice
          title="Active datasource could not be loaded"
          message={error.message}
          requestId={error.requestId}
          action={<Button onClick={() => void refresh()}>Try again</Button>}
        />
      </div>
    );
  }

  if (!activeSource) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Independent question"
          title="Ask your data"
          description="Each run starts from one complete analytical question against the active datasource."
        />
        <Card className="flex items-center gap-3 p-4" aria-label="Active datasource status">
          <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-primary" aria-hidden>
            <DatabaseIcon size={21} />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Active source</p>
            <p className="font-semibold text-text">No datasource selected</p>
          </div>
        </Card>
        <EmptyState
          icon={<MagnifyingGlassIcon size={24} weight="duotone" />}
          title="Choose a ready datasource first"
          description="Question submission stays disabled until a datasource has completed onboarding and is active."
          action={
            <Button asChild variant="secondary">
              <Link href="/sources">Go to Sources</Link>
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Independent question"
        title="Ask your data"
        description="Each submission is a new run. Include the metric, grouping, filters, and time range needed to answer it."
      />

      <Card className="flex flex-wrap items-center gap-3 p-4" aria-label="Active datasource status">
        <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-primary" aria-hidden>
          <DatabaseIcon size={21} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Active source</p>
          <p className="truncate font-semibold text-text">{activeSource.name}</p>
          <p className="truncate text-xs text-muted-foreground">
            {activeSource.source_type === "mysql" ? "MySQL" : "PostgreSQL"} · {activeSource.database_name} · semantic index {activeSource.semantic_status}
          </p>
        </div>
        <StatusPill>{canRun ? "Ready to query" : "Query unavailable"}</StatusPill>
      </Card>

      <DatasourceContextPanel source={activeSource} />

      {!canRun ? (
        <ApiErrorNotice
          title="This datasource is not query-ready"
          message="Refresh metadata and wait for a searchable semantic index before submitting a question."
          action={
            <Button asChild variant="secondary">
              <Link href={`/sources/${activeSource.id}`}>View datasource</Link>
            </Button>
          }
        />
      ) : null}

      <Card className="p-4 sm:p-5">
        <form onSubmit={handleSubmit} noValidate>
          <label htmlFor="analytical-question" className="font-semibold text-text">
            Complete analytical question
          </label>
          <p id="question-help" className="mt-1 text-sm leading-6 text-muted-foreground">
            Example: Revenue by product category for completed orders. This is not a multi-turn chat.
          </p>
          <textarea
            id="analytical-question"
            value={question}
            onChange={(event) => {
              setQuestion(event.target.value);
              if (fieldError) setFieldError(null);
            }}
            onBlur={() => {
              if (question.trim().length > 0 && question.trim().length < 3) {
                setFieldError("Enter at least 3 characters.");
              }
            }}
            onKeyDown={handleQuestionKeyDown}
            aria-describedby={fieldError ? "question-help question-error" : "question-help"}
            aria-invalid={Boolean(fieldError)}
            className="mt-3 min-h-28 w-full resize-y rounded-md border border-border bg-card px-4 py-3 text-base text-text transition-colors duration-200 placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/20 disabled:cursor-not-allowed disabled:bg-muted"
            placeholder="Ask one complete question about the active datasource"
            minLength={3}
            maxLength={1000}
            disabled={!canRun || pending}
          />
          {canRun ? (
            <QuestionSuggestions
              datasourceId={activeSource.id}
              onSelect={(suggestion) => {
                setQuestion(suggestion);
                setFieldError(null);
              }}
            />
          ) : null}
          <div className="mt-2 flex min-h-6 flex-wrap items-start justify-between gap-2">
            <p id="question-error" className="text-sm font-medium text-destructive" role={fieldError ? "alert" : undefined}>
              {fieldError}
            </p>
            <p className="ml-auto text-xs text-muted-foreground">Ctrl/⌘ + Enter to run</p>
          </div>
          <div className="mt-3 flex justify-end">
            <Button type="submit" disabled={!canRun || pending || question.trim().length < 3}>
              {pending ? (
                <CircleNotchIcon className="animate-spin" size={18} aria-hidden />
              ) : (
                <MagnifyingGlassIcon size={18} aria-hidden />
              )}
              {pending ? "Running query…" : "Run question"}
            </Button>
          </div>
        </form>
      </Card>

      <section
        ref={statusRef}
        tabIndex={-1}
        aria-live="polite"
        aria-atomic="true"
        aria-label="Query run status"
        className="min-h-32 scroll-mt-20 rounded-lg focus:outline-none focus-visible:ring-3 focus-visible:ring-primary/30"
      >
        {pending ? (
          <Card className="flex min-h-32 items-start gap-3 border-border-strong bg-muted/45 p-4">
            <CircleNotchIcon className="mt-0.5 shrink-0 animate-spin text-primary" size={22} aria-hidden />
            <div>
              <h2 className="font-semibold text-text">Running the deterministic query path</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Waiting for the backend to return a confirmed terminal state. Duplicate submission is disabled.
              </p>
            </div>
          </Card>
        ) : submitError ? (
          <ApiErrorNotice
            title="Query request failed"
            message={submitError.message}
            requestId={submitError.requestId}
            action={
              submitError.retryable ? (
                <Button onClick={() => void submitQuestion(question)}>
                  <ArrowClockwiseIcon size={18} aria-hidden /> Retry as new run
                </Button>
              ) : undefined
            }
          />
        ) : run ? (
          <RunStatus run={run} />
        ) : (
          <Card className="flex min-h-32 items-center p-4">
            <div>
              <h2 className="font-semibold text-text">Ready for a question</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Generated SQL, safe execution trace, warnings, and verified rows will appear below.
              </p>
            </div>
          </Card>
        )}
      </section>

      {run?.status === "clarification_required" ? (
        <Card className="border-accent/45 p-4 sm:p-5">
          <h2 className="font-semibold text-text">Choose a complete question</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Each choice starts a new independent run; no prior conversational context is attached.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {run.clarification_suggestions.map((suggestion) => (
              <Button
                key={suggestion}
                variant="secondary"
                onClick={() => void submitQuestion(suggestion)}
                disabled={pending}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </Card>
      ) : null}

      {run?.status === "failed" ? (
        <div className="flex justify-end">
          <Button variant="secondary" onClick={() => void submitQuestion(question)} disabled={pending}>
            <ArrowClockwiseIcon size={18} aria-hidden /> Retry as new run
          </Button>
        </div>
      ) : null}

      {run?.warnings.length ? (
        <Card className="border-accent/45 p-4" role="status">
          <h2 className="font-semibold text-text">Result warnings</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {run.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </Card>
      ) : null}

      {pending ? (
        <div className="grid gap-4 xl:grid-cols-2" aria-hidden="true">
          <Card className="h-40 animate-pulse bg-muted" />
          <Card className="h-40 animate-pulse bg-muted" />
        </div>
      ) : run ? (
        <>
          <QueryRunDetails run={run} trace={trace} />
          {traceError ? (
            <p className="text-sm text-muted-foreground" role="status">
              The run completed, but its trace could not be loaded. The result remains available.
            </p>
          ) : null}
        </>
      ) : null}

      {run?.status === "completed" && run.result ? (
        <div className="space-y-4">
          <div className="flex justify-end">
            <SaveWidgetDialog
              runId={run.run_id}
              defaultTitle={run.question}
              chartType={chartType ?? (isChartType(run.visualization_type) ? run.visualization_type : "table")}
            />
          </div>
          <ResultVisualization
            result={run.result}
            initialType={run.visualization_type}
            selectedType={chartType}
            onTypeChange={setChartType}
          />
        </div>
      ) : null}
    </div>
  );
}

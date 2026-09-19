import { TableIcon, WarningCircleIcon } from "@phosphor-icons/react";

import { Card } from "@/components/ui/card";
import type { QueryResult, QueryResultColumn } from "@/lib/query-runs";

function formatValue(value: unknown, column: QueryResultColumn) {
  if (value === null || value === undefined) {
    return (
      <span className="font-sans text-xs font-semibold uppercase text-muted-foreground" aria-label="Null value">
        Null
      </span>
    );
  }
  if (column.type === "number" && typeof value === "number") {
    return new Intl.NumberFormat().format(value);
  }
  if (column.type === "boolean" && typeof value === "boolean") {
    return value ? "True" : "False";
  }
  if (column.type === "structured") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function QueryResultTable({ result }: { result: QueryResult }) {
  const notices = [
    ...(result.truncated
      ? ["Only the configured row limit is shown. Refine the question for a smaller result."]
      : []),
    ...result.warnings,
  ];

  if (result.rows.length === 0) {
    return (
      <div className="space-y-3">
        <ResultNotices notices={notices} />
        <Card className="flex min-h-44 flex-col items-center justify-center p-6 text-center">
          <TableIcon className="text-primary" size={28} weight="duotone" aria-hidden />
          <h2 className="mt-3 text-lg font-semibold text-text">No matching rows</h2>
          <p className="mt-1 max-w-md text-sm text-muted-foreground">
            The query completed successfully, but the current filters returned an empty result.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <Card className="min-w-0 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div>
          <h2 className="font-semibold text-text">Verified result</h2>
          <p className="text-xs text-muted-foreground">
            {result.row_count.toLocaleString()} returned row{result.row_count === 1 ? "" : "s"}
          </p>
        </div>
        <span className="font-mono text-xs text-muted-foreground">
          {result.duration_ms.toLocaleString()} ms
        </span>
      </div>
      <ResultNotices notices={notices} embedded />
      <div className="max-w-full overflow-x-auto" tabIndex={0} aria-label="Scrollable query result">
        <table className="w-full min-w-max border-collapse text-left text-sm">
          <caption className="sr-only">
            Query result with {result.row_count} rows and {result.columns.length} columns
          </caption>
          <thead className="bg-muted/70">
            <tr>
              {result.columns.map((column) => (
                <th
                  key={column.name}
                  scope="col"
                  className="border-b border-border px-4 py-3 font-semibold text-text"
                >
                  <span>{column.name}</span>
                  <span className="ml-2 font-mono text-[0.6875rem] font-normal uppercase text-muted-foreground">
                    {column.type}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-b border-border last:border-b-0 hover:bg-muted/45">
                {result.columns.map((column, columnIndex) => (
                  <td
                    key={`${rowIndex}-${column.name}`}
                    className="max-w-96 px-4 py-3 font-mono text-[0.8125rem] tabular-nums text-text"
                  >
                    <span className="block [overflow-wrap:anywhere]">
                      {formatValue(row[columnIndex], column)}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function ResultNotices({ notices, embedded = false }: { notices: string[]; embedded?: boolean }) {
  if (notices.length === 0) return null;
  return (
    <div
      className={embedded ? "border-b border-accent/35 bg-accent/5 px-4 py-3" : "rounded-lg border border-accent/35 bg-accent/5 p-4"}
      role="status"
    >
      <div className="flex items-start gap-2">
        <WarningCircleIcon className="mt-0.5 shrink-0 text-accent-hover" size={18} aria-hidden />
        <div>
          <p className="text-sm font-semibold text-text">Result notice</p>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-muted-foreground">
            {notices.map((notice) => (
              <li key={notice}>{notice}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

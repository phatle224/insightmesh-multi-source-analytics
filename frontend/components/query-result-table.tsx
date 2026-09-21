"use client";

import { CaretLeftIcon, CaretRightIcon, TableIcon, WarningCircleIcon } from "@phosphor-icons/react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { QueryResult, QueryResultColumn } from "@/lib/query-runs";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;
const DEFAULT_PAGE_SIZE = 10;

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
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [previousResult, setPreviousResult] = useState(result);

  if (previousResult !== result) {
    setPreviousResult(result);
    setCurrentPage(1);
  }

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

  const totalRows = result.rows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  const safePage = Math.min(Math.max(1, currentPage), totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalRows);
  const displayedRows = result.rows.slice(startIndex, endIndex);

  return (
    <Card className="min-w-0 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div>
          <h2 className="font-semibold text-text">Verified result</h2>
          <p className="text-xs text-muted-foreground">
            {result.row_count.toLocaleString()} returned row{result.row_count === 1 ? "" : "s"}
            {totalPages > 1 ? (
              <span className="ml-1.5 font-medium text-text">
                • Page {safePage} of {totalPages}
              </span>
            ) : null}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {totalPages > 1 ? (
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="small"
                className="h-8 px-2 text-xs"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={safePage <= 1}
                aria-label="Previous page (header)"
              >
                <CaretLeftIcon size={14} aria-hidden />
                <span className="hidden sm:inline">Prev</span>
              </Button>
              <span className="font-mono text-xs text-muted-foreground">
                {safePage}/{totalPages}
              </span>
              <Button
                variant="ghost"
                size="small"
                className="h-8 px-2 text-xs"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={safePage >= totalPages}
                aria-label="Next page (header)"
              >
                <span className="hidden sm:inline">Next</span>
                <CaretRightIcon size={14} aria-hidden />
              </Button>
            </div>
          ) : null}
          <span className="font-mono text-xs text-muted-foreground">
            {result.duration_ms.toLocaleString()} ms
          </span>
        </div>
      </div>
      <ResultNotices notices={notices} embedded />
      <div className="max-w-full overflow-x-auto" tabIndex={0} aria-label="Scrollable query result">
        <table className="w-full min-w-max border-collapse text-left text-sm">
          <caption className="sr-only">
            Query result with {result.row_count} rows and {result.columns.length} columns. Displaying page {safePage} of {totalPages}.
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
            {displayedRows.map((row, rowIndex) => {
              const globalRowIndex = startIndex + rowIndex;
              return (
                <tr key={globalRowIndex} className="border-b border-border last:border-b-0 hover:bg-muted/45">
                  {result.columns.map((column, columnIndex) => (
                    <td
                      key={`${globalRowIndex}-${column.name}`}
                      className="max-w-96 px-4 py-3 font-mono text-[0.8125rem] tabular-nums text-text"
                    >
                      <span className="block [overflow-wrap:anywhere]">
                        {formatValue(row[columnIndex], column)}
                      </span>
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">
          {totalRows === 1
            ? "Showing 1 of 1 returned row"
            : `Showing ${(startIndex + 1).toLocaleString()}–${endIndex.toLocaleString()} of ${totalRows.toLocaleString()} returned rows`}
        </p>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="result-rows-per-page" className="whitespace-nowrap text-xs text-muted-foreground">
              Rows per page:
            </label>
            <select
              id="result-rows-per-page"
              value={pageSize}
              onChange={(event) => {
                setPageSize(Number(event.target.value));
                setCurrentPage(1);
              }}
              className="h-8 rounded-md border border-border bg-card px-2 text-xs text-text transition-colors duration-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              {PAGE_SIZE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          <nav aria-label="Query result table pagination" className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="small"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              aria-label="Previous page"
            >
              <CaretLeftIcon size={16} aria-hidden />
              <span>Previous</span>
            </Button>

            <span className="whitespace-nowrap text-xs text-muted-foreground">
              Page <span className="font-mono font-semibold text-text">{safePage}</span> of{" "}
              <span className="font-mono font-semibold text-text">{totalPages}</span>
            </span>

            <Button
              variant="secondary"
              size="small"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              aria-label="Next page"
            >
              <span>Next</span>
              <CaretRightIcon size={16} aria-hidden />
            </Button>
          </nav>
        </div>
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

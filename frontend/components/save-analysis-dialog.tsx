"use client";

import { FloppyDiskIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiClientError } from "@/lib/api-client";
import { createSavedAnalysis, type SavedAnalysis } from "@/lib/saved-analyses";

export function SaveAnalysisDialog({
  runId,
  defaultName,
  onSaved,
}: {
  runId: string;
  defaultName: string;
  onSaved?: (analysis: SavedAnalysis) => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(defaultName.slice(0, 160));
  const [description, setDescription] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", close);
    window.setTimeout(() => nameRef.current?.focus(), 0);
    return () => window.removeEventListener("keydown", close);
  }, [open]);

  function show() {
    setName(defaultName.slice(0, 160));
    setDescription("");
    setMessage(null);
    setSaved(false);
    setOpen(true);
  }

  async function save() {
    if (!name.trim()) return;
    setPending(true);
    setMessage(null);
    try {
      const analysis = await createSavedAnalysis({
        query_run_id: runId,
        name: name.trim(),
        description: description.trim() || undefined,
      });
      onSaved?.(analysis);
      setSaved(true);
      setMessage("Saved analysis. You can close this dialog.");
    } catch (error) {
      setMessage(error instanceof ApiClientError ? error.message : "The analysis could not be saved.");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <Button variant="secondary" onClick={show}>
        <FloppyDiskIcon size={18} aria-hidden /> Save analysis
      </Button>
      {open ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-text/45 p-4"
          role="presentation"
          onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}
        >
          <div
            className="w-full max-w-lg rounded-lg border border-border bg-card p-5 shadow-float"
            role="dialog"
            aria-modal="true"
            aria-labelledby="save-analysis-title"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="save-analysis-title" className="text-lg font-semibold text-text">Save analysis</h2>
                <p className="mt-1 text-sm text-muted-foreground">The validated query will stay available after recent activity expires.</p>
              </div>
              <Button size="icon" variant="ghost" aria-label="Close save analysis dialog" onClick={() => setOpen(false)}>
                <XIcon size={18} aria-hidden />
              </Button>
            </div>
            <div className="mt-5 space-y-4">
              <label className="block text-sm font-semibold text-text">
                Name
                <input ref={nameRef} value={name} onChange={(event) => setName(event.target.value)} maxLength={160} className="mt-1 min-h-11 w-full rounded-md border border-border bg-card px-3 font-normal focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/20" />
              </label>
              <label className="block text-sm font-semibold text-text">
                Description <span className="font-normal text-muted-foreground">(optional)</span>
                <textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={1_000} rows={3} className="mt-1 w-full rounded-md border border-border bg-card px-3 py-2 font-normal focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/20" />
              </label>
              {message ? <p className={saved ? "text-sm text-primary" : "text-sm text-destructive"} role={saved ? "status" : "alert"}>{message}</p> : null}
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={() => setOpen(false)} disabled={pending}>{saved ? "Close" : "Cancel"}</Button>
                <Button onClick={() => void save()} disabled={pending || saved || !name.trim()}>{pending ? "Saving…" : saved ? "Saved" : "Save analysis"}</Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

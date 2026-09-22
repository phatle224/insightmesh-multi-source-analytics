"use client";

import { PencilSimpleIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiClientError } from "@/lib/api-client";
import { updateSavedAnalysis, type SavedAnalysis } from "@/lib/saved-analyses";

export function EditSavedAnalysisDialog({
  analysis,
  onUpdated,
}: {
  analysis: SavedAnalysis;
  onUpdated: (analysis: SavedAnalysis) => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(analysis.name);
  const [description, setDescription] = useState(analysis.description ?? "");
  const [tags, setTags] = useState(analysis.tags.join(", "));
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", close);
    window.setTimeout(() => nameRef.current?.focus(), 0);
    return () => window.removeEventListener("keydown", close);
  }, [open]);

  function show() {
    setName(analysis.name);
    setDescription(analysis.description ?? "");
    setTags(analysis.tags.join(", "));
    setMessage(null);
    setOpen(true);
  }

  async function save() {
    if (!name.trim()) return;
    setPending(true);
    setMessage(null);
    try {
      const updated = await updateSavedAnalysis(analysis.id, {
        name: name.trim(),
        description: description.trim() || null,
        tags: tags
          .split(",")
          .map((tag) => tag.trim().toLowerCase())
          .filter(Boolean),
      });
      onUpdated(updated);
      setOpen(false);
    } catch (error) {
      setMessage(error instanceof ApiClientError ? error.message : "The saved analysis could not be updated.");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <Button variant="ghost" onClick={show} aria-label={`Edit ${analysis.name}`}>
        <PencilSimpleIcon size={18} aria-hidden /> Edit
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
            aria-labelledby="edit-saved-analysis-title"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="edit-saved-analysis-title" className="text-lg font-semibold text-text">Edit saved analysis</h2>
                <p className="mt-1 text-sm text-muted-foreground">Update the label and organization details. The validated query stays unchanged.</p>
              </div>
              <Button size="icon" variant="ghost" aria-label="Close edit saved analysis dialog" onClick={() => setOpen(false)}>
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
              <label className="block text-sm font-semibold text-text">
                Tags <span className="font-normal text-muted-foreground">(comma separated)</span>
                <input value={tags} onChange={(event) => setTags(event.target.value)} maxLength={500} placeholder="sales, weekly, finance" className="mt-1 min-h-11 w-full rounded-md border border-border bg-card px-3 font-normal focus:border-primary focus:outline-none focus:ring-3 focus:ring-primary/20" />
              </label>
              {message ? <p className="text-sm text-destructive" role="alert">{message}</p> : null}
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={() => setOpen(false)} disabled={pending}>Cancel</Button>
                <Button onClick={() => void save()} disabled={pending || !name.trim()}>{pending ? "Saving…" : "Save changes"}</Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

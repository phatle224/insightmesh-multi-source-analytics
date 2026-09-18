import type { InputHTMLAttributes, SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const controlClass =
  "mt-1.5 min-h-11 w-full rounded-md border border-border-strong bg-card px-3 text-sm text-text shadow-sm placeholder:text-muted-foreground hover:border-primary focus:border-primary focus:outline-none";

export function FormField({
  label,
  hint,
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <label className="block text-sm font-semibold text-text">
      {label}
      <input className={cn(controlClass, className)} {...props} />
      {hint ? <span className="mt-1.5 block text-xs font-normal text-muted-foreground">{hint}</span> : null}
    </label>
  );
}

export function SelectField({
  label,
  hint,
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label: string; hint?: string }) {
  return (
    <label className="block text-sm font-semibold text-text">
      {label}
      <select className={cn(controlClass, className)} {...props}>{children}</select>
      {hint ? <span className="mt-1.5 block text-xs font-normal text-muted-foreground">{hint}</span> : null}
    </label>
  );
}

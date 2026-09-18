import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function StatusPill({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex min-h-6 items-center rounded-full border border-border-strong bg-muted px-2.5 py-0.5 text-xs font-semibold text-foreground",
        className,
      )}
      {...props}
    />
  );
}

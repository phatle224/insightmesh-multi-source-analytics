import { CheckCircleIcon, CircleNotchIcon, WarningCircleIcon } from "@phosphor-icons/react";

import { StatusPill } from "@/components/ui/status-pill";
import { cn } from "@/lib/utils";

export function SourceStatus({ status }: { status: string }) {
  const failed = status === "failed";
  const ready = status === "ready";
  const Icon = failed ? WarningCircleIcon : ready ? CheckCircleIcon : CircleNotchIcon;
  return (
    <StatusPill
      className={cn(
        "gap-1.5 capitalize",
        failed && "border-destructive/40 bg-destructive/5 text-destructive",
        ready && "border-green-700/30 bg-green-50 text-green-800",
      )}
    >
      <Icon size={14} className={!failed && !ready ? "animate-spin" : undefined} aria-hidden />
      {status.replaceAll("_", " ")}
    </StatusPill>
  );
}

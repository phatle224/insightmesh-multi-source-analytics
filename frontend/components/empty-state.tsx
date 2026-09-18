import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Card className="flex min-h-72 flex-col items-center justify-center px-5 py-10 text-center">
      <div
        className="mb-4 grid size-12 place-items-center rounded-lg border border-border-strong bg-muted text-primary"
        aria-hidden="true"
      >
        {icon}
      </div>
      <h2 className="text-lg font-semibold text-text">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </Card>
  );
}

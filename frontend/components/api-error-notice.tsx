import { WarningCircleIcon } from "@phosphor-icons/react/dist/ssr";

import { Card } from "@/components/ui/card";

export function ApiErrorNotice({
  title,
  message,
  requestId,
  action,
}: {
  title: string;
  message: string;
  requestId?: string;
  action?: React.ReactNode;
}) {
  return (
    <Card className="border-destructive/40 p-4" role="alert">
      <div className="flex items-start gap-3">
        <WarningCircleIcon className="mt-0.5 shrink-0 text-destructive" size={20} aria-hidden />
        <div className="min-w-0">
          <h2 className="font-semibold text-text">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{message}</p>
          {requestId ? (
            <p className="mt-2 font-mono text-xs text-muted-foreground">Request ID: {requestId}</p>
          ) : null}
          {action ? <div className="mt-4">{action}</div> : null}
        </div>
      </div>
    </Card>
  );
}

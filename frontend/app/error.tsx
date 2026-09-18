"use client";

import { ApiErrorNotice } from "@/components/api-error-notice";
import { Button } from "@/components/ui/button";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <ApiErrorNotice
      title="This page could not be loaded"
      message="Try the request again. If it keeps failing, use the request identifier from the service response when available."
      action={<Button onClick={reset}>Try again</Button>}
    />
  );
}

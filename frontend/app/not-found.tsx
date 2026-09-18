import { CompassIcon } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <EmptyState
      icon={<CompassIcon size={24} weight="duotone" />}
      title="Page not found"
      description="The requested InsightMesh route does not exist."
      action={
        <Button asChild variant="secondary">
          <Link href="/sources">Return to Sources</Link>
        </Button>
      }
    />
  );
}

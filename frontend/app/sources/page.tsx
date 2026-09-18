import { DatabaseIcon } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatusPill } from "@/components/ui/status-pill";

export const metadata: Metadata = { title: "Sources" };

export default function SourcesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Data workspace"
        title="Sources"
        description="Connect and manage the databases that InsightMesh can analyze safely."
        action={<StatusPill>Connector APIs · Phase 4</StatusPill>}
      />
      <EmptyState
        icon={<DatabaseIcon size={24} weight="duotone" />}
        title="No data sources yet"
        description="Datasource onboarding starts in Phase 4. This state intentionally contains no sample connections or fake readiness status."
      />
    </div>
  );
}

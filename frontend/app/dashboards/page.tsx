import { ChartBarIcon, MagnifyingGlassIcon } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Dashboards" };

export default function DashboardsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Saved analysis"
        title="Dashboards"
        description="Keep verified results together and refresh their stored read-only queries without another LLM call."
      />
      <EmptyState
        icon={<ChartBarIcon size={24} weight="duotone" />}
        title="No dashboards yet"
        description="Completed query results can be saved here after the Ask workflow is available."
        action={
          <Button asChild variant="secondary">
            <Link href="/ask">
              <MagnifyingGlassIcon size={18} aria-hidden />
              Open Ask workspace
            </Link>
          </Button>
        }
      />
    </div>
  );
}

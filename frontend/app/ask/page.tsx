import { DatabaseIcon, MagnifyingGlassIcon } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "Ask" };

export default function AskPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Independent question"
        title="Ask your data"
        description="Each run starts from one complete analytical question against the active datasource."
      />
      <Card className="flex items-center gap-3 p-4" aria-label="Active datasource status">
        <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-primary" aria-hidden>
          <DatabaseIcon size={21} />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Active source</p>
          <p className="font-semibold text-text">No datasource selected</p>
        </div>
      </Card>
      <section aria-live="polite" aria-atomic="true">
        <EmptyState
          icon={<MagnifyingGlassIcon size={24} weight="duotone" />}
          title="Choose a ready datasource first"
          description="Question submission stays disabled until a datasource has completed onboarding and is active."
          action={
            <Button asChild variant="secondary">
              <Link href="/sources">Go to Sources</Link>
            </Button>
          }
        />
      </section>
    </div>
  );
}

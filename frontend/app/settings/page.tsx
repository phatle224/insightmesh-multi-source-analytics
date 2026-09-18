import { GearSixIcon, SlidersHorizontalIcon } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";

import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Settings"
        description="Only non-secret, user-actionable preferences supported by the backend appear here."
      />
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-primary" aria-hidden>
              <SlidersHorizontalIcon size={21} />
            </span>
            <div>
              <h2 className="font-semibold text-text">Display preferences</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Preference controls will appear when their persistence contract is available.
              </p>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-md bg-muted text-primary" aria-hidden>
              <GearSixIcon size={21} />
            </span>
            <div>
              <h2 className="font-semibold text-text">Server-managed controls</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Credentials, provider keys, and safety limits are intentionally not exposed in this UI.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

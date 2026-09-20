import type { Metadata } from "next";

import { DashboardsWorkspace } from "@/components/dashboards-workspace";

export const metadata: Metadata = { title: "Dashboards" };

export default function DashboardsPage() {
  return <DashboardsWorkspace />;
}

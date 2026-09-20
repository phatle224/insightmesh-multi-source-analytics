import type { Metadata } from "next";

import { DashboardDetailWorkspace } from "@/components/dashboard-detail-workspace";

export const metadata: Metadata = { title: "Dashboard details" };

export default async function DashboardDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DashboardDetailWorkspace id={id} />;
}

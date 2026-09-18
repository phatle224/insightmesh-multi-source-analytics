import type { Metadata } from "next";

import { DatasourceDetailWorkspace } from "@/components/datasource-detail-workspace";

export const metadata: Metadata = { title: "Datasource details" };

export default async function DatasourceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DatasourceDetailWorkspace id={id} />;
}

import type { Metadata } from "next";

import { HistoryWorkspace } from "@/components/history-workspace";

export const metadata: Metadata = { title: "Query history" };

export default function HistoryPage() {
  return <HistoryWorkspace />;
}

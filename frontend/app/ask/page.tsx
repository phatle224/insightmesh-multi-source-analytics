import type { Metadata } from "next";

import { AskWorkspace } from "@/components/ask-workspace";

export const metadata: Metadata = { title: "Ask" };

export default function AskPage() {
  return <AskWorkspace />;
}

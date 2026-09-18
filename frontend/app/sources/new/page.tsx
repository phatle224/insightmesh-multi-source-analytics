import type { Metadata } from "next";

import { DatasourceForm } from "@/components/datasource-form";

export const metadata: Metadata = { title: "Add PostgreSQL source" };

export default function NewSourcePage() {
  return <DatasourceForm />;
}

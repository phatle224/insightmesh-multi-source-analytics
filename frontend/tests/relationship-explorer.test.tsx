import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RelationshipExplorer } from "@/components/relationship-explorer";
import type { DatasourceEntity, DatasourceRelationship } from "@/lib/datasources";

const entities = ["customers", "orders", "order_items", "products"].map(
  (name, index): DatasourceEntity => ({
    id: `entity-${index}`,
    schema_name: "public",
    name,
    entity_type: "table",
    description: null,
    business_terms: [],
    metrics: [],
    fields: [],
  }),
);

const relationships: DatasourceRelationship[] = [
  {
    id: "r1",
    name: "foreign_key",
    source: "public.orders",
    target: "public.customers",
    source_field: "customer_id",
    target_field: "id",
    relationship_type: "foreign_key",
    provenance: "declared",
    confidence: 1,
    evidence: ["database foreign key"],
    generation_eligible: true,
  },
  {
    id: "r2",
    name: "foreign_key",
    source: "public.order_items",
    target: "public.orders",
    source_field: "order_id",
    target_field: "id",
    relationship_type: "foreign_key",
    provenance: "declared",
    confidence: 1,
    evidence: ["database foreign key"],
    generation_eligible: true,
  },
  {
    id: "r3",
    name: "name_match",
    source: "public.order_items",
    target: "public.products",
    source_field: "product_id",
    target_field: "id",
    relationship_type: "candidate_join",
    provenance: "inferred",
    confidence: 0.62,
    evidence: ["privacy-safe relationship signal"],
    generation_eligible: false,
  },
];

describe("RelationshipExplorer", () => {
  it("highlights direct neighbors when an entity is selected", () => {
    render(<RelationshipExplorer entities={entities} relationships={relationships} />);

    fireEvent.click(screen.getByRole("button", { name: "public.orders" }));

    expect(screen.getByRole("status")).toHaveTextContent("Selected entity: public.orders");
    expect(screen.getByRole("button", { name: "public.customers, directly related" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByRole("button", { name: "public.products" })).toHaveAttribute(
      "aria-label",
      "public.products",
    );
  });

  it("exposes an explicit arrange mode for drag and keyboard positioning", () => {
    render(<RelationshipExplorer entities={entities} relationships={relationships} />);

    fireEvent.click(screen.getByRole("button", { name: "Arrange / drag" }));

    expect(screen.getByRole("button", { name: "Arrange / drag" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Inspect" })).toHaveAttribute("aria-pressed", "false");
  });

  it("keeps the ERD focused without path controls or a secondary list", () => {
    render(<RelationshipExplorer entities={entities} relationships={relationships} />);

    expect(screen.queryByText("Join path endpoints")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accessible list" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Graph" })).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: /datasource relationship graph/i })).toBeVisible();
  });
});

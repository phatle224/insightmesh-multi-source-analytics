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
  it("highlights the shortest join path through keyboard-native endpoint controls", () => {
    render(<RelationshipExplorer entities={entities} relationships={relationships} />);

    fireEvent.change(screen.getByLabelText("From entity"), {
      target: { value: "public.customers" },
    });
    fireEvent.change(screen.getByLabelText("To entity"), {
      target: { value: "public.order_items" },
    });

    expect(screen.getByRole("status")).toHaveTextContent(
      "public.customers → public.orders → public.order_items",
    );
    expect(screen.getByRole("img", { name: /selected join path/i })).toBeVisible();
  });

  it("provides an equivalent list with provenance and generation eligibility", () => {
    render(<RelationshipExplorer entities={entities} relationships={relationships} />);

    fireEvent.click(screen.getByRole("button", { name: "Accessible list" }));

    expect(screen.getByRole("table")).toHaveTextContent(
      "public.order_items.product_id → public.products.id",
    );
    expect(screen.getByRole("table")).toHaveTextContent("Inferred");
    expect(screen.getByRole("table")).toHaveTextContent("62%");
    expect(screen.getByRole("table")).toHaveTextContent("Excluded");
    expect(screen.getByRole("button", { name: "Accessible list" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    fireEvent.change(screen.getByLabelText("From entity"), {
      target: { value: "public.order_items" },
    });
    fireEvent.change(screen.getByLabelText("To entity"), {
      target: { value: "public.products" },
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "No generation-eligible relationship path",
    );
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SemanticManifestPanel } from "@/components/semantic-manifest-panel";
import type { SemanticManifest } from "@/lib/datasources";

const mocks = vi.hoisted(() => ({ getSemanticManifest: vi.fn() }));

vi.mock("@/lib/datasources", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/datasources")>()),
  getSemanticManifest: mocks.getSemanticManifest,
}));

const manifest: SemanticManifest = {
  manifest_id: "manifest-1",
  datasource_id: "source-1",
  datasource_name: "Docker Demo",
  datasource_type: "postgresql",
  version: 3,
  manifest_hash: "a".repeat(64),
  metadata_hash: "b".repeat(64),
  profile_hash: "c".repeat(64),
  configuration: {
    model_config_version: "v1",
    retrieval_config_version: "v2-hybrid",
    generation_provider: "gemini",
    generation_model: "gemini-2.5-flash",
    fallback_provider: "openrouter",
    fallback_model: "openai/gpt-4o-mini",
    embedding_model: "openai/text-embedding-3-large",
    embedding_dimensions: 1536,
    relationship_inferred_min_confidence: 0.8,
    privacy_policy_version: "v1-local-profile",
    skill_versions: { "query-generation": "v1", "query-repair": "v1" },
  },
  entities: [
    {
      id: "entity-1",
      schema_name: "public",
      name: "orders",
      entity_type: "table",
      description: "Orders",
      semantic_terms: [],
      metrics: [],
      embedding_artifact_id: "embedding-1",
      fields: [],
    },
  ],
  relationships: [],
  created_at: "2026-09-21T00:00:00Z",
};

describe("SemanticManifestPanel", () => {
  beforeEach(() => {
    mocks.getSemanticManifest.mockReset().mockResolvedValue(manifest);
  });

  it("shows a privacy-safe version summary with progressive configuration details", async () => {
    render(<SemanticManifestPanel datasourceId="source-1" />);

    expect(await screen.findByText("Semantic manifest")).toBeInTheDocument();
    expect(screen.getByText("v3")).toBeInTheDocument();
    expect(screen.getByText("Immutable, reproducible semantic context.", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Version and configuration")).toBeInTheDocument();
    expect(mocks.getSemanticManifest).toHaveBeenCalledWith("source-1");
  });

  it("exports the sanitized API payload as a versioned JSON file", async () => {
    const createObjectURL = vi.fn(() => "blob:manifest");
    const revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
    render(<SemanticManifestPanel datasourceId="source-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Export JSON" }));

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:manifest");
    click.mockRestore();
  });
});

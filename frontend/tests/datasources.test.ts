import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createDatasource,
  deleteDatasource,
  getDatasourcePreview,
  getSemanticManifest,
  renameDatasource,
  testDatasourceConnection,
  type DatasourceConnectionInput,
  type DatasourceCreateInput,
} from "@/lib/datasources";

const payload: DatasourceCreateInput = {
  name: "Docker demo",
  source_type: "postgresql",
  host: "demo-postgres",
  port: 5432,
  database: "insightmesh_demo",
  username: "demo_reader",
  password: "local-password",
  ssl_mode: "disable",
  allowed_schemas: ["public"],
};

afterEach(() => vi.unstubAllGlobals());

describe("datasource API", () => {
  it("tests a connection without sending the connection name", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ok",
          database: "insightmesh_demo",
          server_version: "16",
          read_only_transaction: true,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetcher);
    const connection: DatasourceConnectionInput = {
      source_type: payload.source_type,
      host: payload.host,
      port: payload.port,
      database: payload.database,
      username: payload.username,
      password: payload.password,
      ssl_mode: payload.ssl_mode,
      allowed_schemas: payload.allowed_schemas,
    };

    await expect(testDatasourceConnection(connection)).resolves.toMatchObject({
      read_only_transaction: true,
    });
    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/datasources/test",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetcher.mock.calls[0]?.[1]?.body).not.toContain('"name"');
  });

  it("sends the full payload only when creating the source", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ id: "source-1", status: "ready" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    await createDatasource(payload);

    expect(fetcher.mock.calls[0]?.[1]?.body).toContain('"name":"Docker demo"');
  });

  it("loads the latest semantic manifest from the datasource boundary", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ manifest_id: "manifest-1", version: 2 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    await expect(getSemanticManifest("source-1")).resolves.toMatchObject({ version: 2 });
    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/datasources/source-1/semantic-manifest",
      expect.any(Object),
    );
  });

  it("renames a datasource through the datasource boundary", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ id: "source-1", name: "Renamed source" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    await expect(renameDatasource("source-1", "Renamed source")).resolves.toMatchObject({
      name: "Renamed source",
    });
    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/datasources/source-1",
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(fetcher.mock.calls[0]?.[1]?.body).toBe(JSON.stringify({ name: "Renamed source" }));
  });

  it("loads a bounded datasource row preview", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ entity_name: "orders", columns: ["id"], rows: [[1]] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    await expect(getDatasourcePreview("source-1", "entity-1")).resolves.toMatchObject({
      entity_name: "orders",
      rows: [[1]],
    });
    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/datasources/source-1/preview/entity-1",
      expect.any(Object),
    );
  });

  it("deletes a datasource without requiring a response body", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetcher);

    await expect(deleteDatasource("source-1")).resolves.toBeNull();
    expect(fetcher).toHaveBeenCalledWith(
      "/api/v1/datasources/source-1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

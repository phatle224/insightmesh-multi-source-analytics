import { apiRequest } from "@/lib/api-client";

export type DatasourceStatus = "draft" | "testing" | "introspecting" | "ready" | "failed";
export type SslMode = "disable" | "prefer" | "require" | "verify-ca" | "verify-full";

export interface DatasourceConnectionInput {
  source_type: "postgresql";
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl_mode: SslMode;
  allowed_schemas: string[];
}

export interface DatasourceCreateInput extends DatasourceConnectionInput {
  name: string;
}

export interface ConnectionTestResult {
  status: "ok";
  database: string;
  server_version: string;
  read_only_transaction: boolean;
}

export interface DatasourceSummary {
  id: string;
  name: string;
  source_type: string;
  database_name: string;
  safe_host: string;
  port: number;
  ssl_mode: string;
  allowed_schemas: string[];
  status: DatasourceStatus;
  is_active: boolean;
  entity_count: number;
  relationship_count: number;
  profile_count: number;
  semantic_term_count: number;
  metric_count: number;
  embedding_count: number;
  pii_excluded_count: number;
  semantic_status: "not_configured" | "configuration_required" | "indexing" | "ready" | "stale" | "failed";
  semantic_error_code: string | null;
  last_refreshed_at: string | null;
  last_error_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasourceField {
  id: string;
  name: string;
  native_type: string;
  normalized_type: string;
  nullable: boolean;
  ordinal: number;
  primary_key: boolean;
  unique: boolean;
  description: string | null;
  profile: Record<string, unknown> | null;
  profile_sample_size: number | null;
  profile_excluded: boolean;
}

export interface DatasourceEntity {
  id: string;
  schema_name: string;
  name: string;
  entity_type: string;
  description: string | null;
  business_terms: string[];
  metrics: string[];
  fields: DatasourceField[];
}

export interface DatasourceRelationship {
  id: string;
  name: string;
  source: string;
  target: string;
}

export interface DatasourceDetail extends DatasourceSummary {
  entities: DatasourceEntity[];
  relationships: DatasourceRelationship[];
}

export const listDatasources = () => apiRequest<DatasourceSummary[]>("/api/v1/datasources");

export function testDatasourceConnection(payload: DatasourceConnectionInput) {
  return apiRequest<ConnectionTestResult>("/api/v1/datasources/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createDatasource(payload: DatasourceCreateInput) {
  return apiRequest<DatasourceDetail>("/api/v1/datasources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export const getDatasource = (id: string) =>
  apiRequest<DatasourceDetail>(`/api/v1/datasources/${id}`);
export const activateDatasource = (id: string) =>
  apiRequest<DatasourceDetail>(`/api/v1/datasources/${id}/activate`, { method: "POST" });
export const refreshDatasource = (id: string) =>
  apiRequest<DatasourceDetail>(`/api/v1/datasources/${id}/refresh`, { method: "POST" });

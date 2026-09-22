import { apiRequest } from "@/lib/api-client";

export interface SavedAnalysis {
  id: string;
  datasource_id: string;
  datasource_name: string;
  name: string;
  description: string | null;
  question: string;
  validated_query: { sql: string; expected_columns: string[] };
  query_type: "postgresql" | "mysql";
  visualization_type: string | null;
  tags: string[];
  source_query_run_id: string | null;
  created_at: string;
  updated_at: string;
}

export const listSavedAnalyses = () =>
  apiRequest<SavedAnalysis[]>('/api/v1/saved-analyses');

export const createSavedAnalysis = (payload: {
  query_run_id: string;
  name: string;
  description?: string;
  tags?: string[];
}) =>
  apiRequest<SavedAnalysis>('/api/v1/saved-analyses', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const updateSavedAnalysis = (
  id: string,
  payload: { name?: string; description?: string | null; tags?: string[] },
) =>
  apiRequest<SavedAnalysis>(`/api/v1/saved-analyses/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });

export const deleteSavedAnalysis = (id: string) =>
  apiRequest<void>(`/api/v1/saved-analyses/${id}`, { method: 'DELETE' });

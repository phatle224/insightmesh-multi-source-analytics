import { describe, expect, it } from "vitest";

import { buildQuestionSuggestions } from "@/components/question-suggestions";
import type { DatasourceDetail } from "@/lib/datasources";

describe("question suggestions", () => {
  it("builds three metadata-backed questions", () => {
    const detail = {
      entities: [
        {
          schema_name: "public",
          name: "orders",
          fields: [
            { name: "total", normalized_type: "number", profile_excluded: false },
          ],
        },
      ],
      relationships: [],
    } as unknown as DatasourceDetail;

    const suggestions = buildQuestionSuggestions(detail);

    expect(suggestions).toHaveLength(3);
    expect(suggestions[0]?.text).toContain("first 10 rows");
    expect(suggestions[1]?.text).toContain("How many records");
    expect(suggestions[2]?.text).toContain("total of total");
  });
});

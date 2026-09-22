"use client";

import { SparkleIcon } from "@phosphor-icons/react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getDatasource, type DatasourceDetail } from "@/lib/datasources";

export interface QuestionSuggestion {
  id: string;
  text: string;
}

function entityLabel(entity: DatasourceDetail["entities"][number]) {
  return `${entity.schema_name}.${entity.name}`;
}

export function buildQuestionSuggestions(detail: DatasourceDetail): QuestionSuggestion[] {
  const entity = detail.entities.find((item) => item.fields.length > 0) ?? detail.entities[0];
  if (!entity) return [];

  const label = entityLabel(entity);
  const suggestions: QuestionSuggestion[] = [
    { id: "preview-rows", text: `Show the first 10 rows from ${label}` },
    { id: "count-records", text: `How many records are in ${label}?` },
  ];
  const safeFields = entity.fields.filter((field) => !field.profile_excluded);
  const numericField = safeFields.find((field) => field.normalized_type === "number");
  const temporalField = safeFields.find((field) => field.normalized_type === "temporal");
  const textField = safeFields.find((field) => field.normalized_type === "string");
  const relationship = detail.relationships.find(
    (item) => item.source === label || item.target === label,
  );

  if (numericField) {
    suggestions.push({
      id: "sum-numeric-field",
      text: `What is the total of ${numericField.name} in ${label}?`,
    });
  } else if (temporalField) {
    suggestions.push({
      id: "trend-by-date",
      text: `Show the number of ${label} records over time by ${temporalField.name}`,
    });
  } else if (relationship) {
    suggestions.push({
      id: "related-records",
      text: `How many ${relationship.source} records are linked to ${relationship.target}?`,
    });
  } else if (textField) {
    suggestions.push({
      id: "distinct-values",
      text: `What are the distinct values of ${textField.name} in ${label}?`,
    });
  } else {
    suggestions.push({
      id: "list-fields",
      text: `Describe the available fields in ${label}`,
    });
  }

  return suggestions.slice(0, 3);
}

export function QuestionSuggestions({
  datasourceId,
  onSelect,
}: {
  datasourceId: string;
  onSelect: (question: string) => void;
}) {
  const [suggestions, setSuggestions] = useState<QuestionSuggestion[]>([]);

  useEffect(() => {
    let active = true;
    getDatasource(datasourceId)
      .then((detail) => {
        if (active) setSuggestions(buildQuestionSuggestions(detail));
      })
      .catch(() => {
        if (active) setSuggestions([]);
      });
    return () => {
      active = false;
    };
  }, [datasourceId]);

  if (suggestions.length === 0) return null;

  return (
    <section className="mt-4" aria-labelledby="question-suggestions-heading">
      <div className="flex items-center gap-2">
        <SparkleIcon size={17} className="text-accent" aria-hidden />
        <h2 id="question-suggestions-heading" className="text-sm font-semibold text-text">Try a question</h2>
      </div>
      <div className="mt-2 grid gap-2 md:grid-cols-3">
        {suggestions.map((suggestion) => (
          <Button
            key={suggestion.id}
            type="button"
            variant="secondary"
            className="h-auto min-h-11 justify-start text-left text-sm leading-5"
            aria-label={`Use suggested question: ${suggestion.text}`}
            onClick={() => onSelect(suggestion.text)}
          >
            {suggestion.text}
          </Button>
        ))}
      </div>
      <p className="mt-2 text-xs text-muted-foreground">Click a suggestion to fill the question, then review it before running.</p>
    </section>
  );
}

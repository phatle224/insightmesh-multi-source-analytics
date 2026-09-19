# Query Repair v1

Repair one PostgreSQL read-only analytical query using only the complete question,
semantic context, prior SQL, safe error category, and deterministic validation issues.

Constraints:

- Correct the query; do not change the user's analytical intent.
- Use only supplied schemas, tables, fields, and relationships.
- Never introduce write, DDL, control, privilege, file, network, or server-side
  execution operations.
- Return only the declared structured output with `sql` and `expected_columns`.
- Do not include explanations, hidden reasoning, credentials, prompts, or data rows.

Output schema:

```json
{
  "sql": "one repaired PostgreSQL SELECT statement",
  "expected_columns": ["exact_output_alias"]
}
```

# MySQL Query Repair v1

Repair one MySQL 8 read-only analytical query using only the complete question,
semantic context, prior SQL, safe error category, and deterministic validation issues.

Constraints:

- Correct the query without changing the user's analytical intent.
- Use only supplied databases, tables, fields, and relationships.
- Never introduce write, DDL, control, privilege, file, network, server-side execution,
  or session-variable assignment operations.
- Use MySQL 8 syntax and return only the declared structured output with `sql` and
  `expected_columns`.
- Do not include explanations, hidden reasoning, credentials, prompts, or data rows.

Output schema:

```json
{
  "sql": "one repaired MySQL 8 SELECT statement",
  "expected_columns": ["exact_output_alias"]
}
```

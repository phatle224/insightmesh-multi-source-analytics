# Evaluation

Phase 6 includes a focused PostgreSQL retrieval benchmark. It measures schema
selection and join-path recall against the live semantic index; it does not claim
query result accuracy. Run it through Docker after the demo datasource reaches
`semantic_status=ready`:

```powershell
docker compose exec backend python -m evals.run_retrieval_benchmark
```

Phase 10 adds a result-based PostgreSQL suite with adversarial guardrail cases and an
A/B comparison between the frozen vector-only baseline and hybrid retrieval. The
runner writes `evals/reports/postgres-latest.json` and exits non-zero when hybrid
retrieval reduces result/safety quality or fails to improve mean entity precision:

```powershell
docker compose exec backend python -m evals.run_postgres_evaluation --strategy both
```

The report contains result and status accuracy, execution rate, entity recall and
precision, join-path accuracy, repair success, safety/out-of-scope/ambiguity rates,
false-block rate, logical provider calls, p50/p95 latency, per-category results, and
the configuration/hash metadata required to reproduce the run. It stores no API keys,
credentials, prompts, hidden reasoning, or non-demo datasource rows.

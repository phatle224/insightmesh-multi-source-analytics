# Evaluation

Phase 6 includes a focused PostgreSQL retrieval benchmark. It measures schema
selection and join-path recall against the live semantic index; it does not claim
query result accuracy. Run it through Docker after the demo datasource reaches
`semantic_status=ready`:

```powershell
docker compose exec backend python -m evals.run_retrieval_benchmark
```

The broader result-accuracy and safety evaluation remains a Phase 10 deliverable.

"""Synchronous deterministic V1 runtime for the PostgreSQL vertical slice."""

import re
import unicodedata
from collections.abc import Callable
from time import perf_counter
from typing import Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from api.errors import AppError
from api.schemas.retrieval import RetrievalResponse
from api.settings import Settings, get_settings
from connectors.base import ConnectorError, DataSourceConnector, QueryLimits, QueryResult
from harness.state import TERMINAL_STATES, RuntimeStatus
from harness.trace import trace_event
from harness.transitions import transition
from persistence.models import Datasource, QueryRun
from query.generation import GeneratedSQL, generate_postgres_sql, repair_postgres_sql
from query.result_verifier import verify_result
from query.sql_validator import SQLValidationResult, validate_postgres_sql
from semantic.provider import LLMProvider, ProviderError
from services.datasources import build_datasource_connector, build_semantic_provider
from services.retrieval import retrieve_context
from visualization.selection import select_visualization

UNSAFE_REQUEST = re.compile(
    r"\b(delete|drop|truncate|update|insert|merge|alter|create|grant|revoke)\b",
    re.IGNORECASE,
)
OBFUSCATED_WRITE_REQUEST = re.compile(
    r"\b(?:d\W*e\W*l\W*e\W*t\W*e|d\W*r\W*o\W*p|t\W*r\W*u\W*n\W*c\W*a\W*t\W*e"
    r"|u\W*p\W*d\W*a\W*t\W*e|i\W*n\W*s\W*e\W*r\W*t|a\W*l\W*t\W*e\W*r)\b",
    re.IGNORECASE,
)
PROMPT_INJECTION = re.compile(
    r"\b(ignore|disregard|override|bypass|reveal|leak)\b.{0,64}"
    r"\b(previous|prior|system|developer|instruction|prompt|guardrail|policy)\b"
    r"|\b(jailbreak|system prompt|developer message)\b",
    re.IGNORECASE,
)
VAGUE_CUSTOMER_RANKING = re.compile(r"\b(best|top)\s+customers?\b", re.IGNORECASE)
CUSTOMER_MEASURES = re.compile(
    r"\b(revenue|sales|spend|order count|number of orders|average order value|aov|quantity)\b",
    re.IGNORECASE,
)
TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
META_REQUEST = re.compile(
    r"(?:\b(?:ban|you|system|he thong)\b.{0,48}\b(?:model|llm|prompt|mo hinh)\b)"
    r"|(?:\b(?:model|llm|prompt|mo hinh)\b.{0,48}\b(?:ban|you|system|he thong)\b)",
    re.IGNORECASE,
)
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "for",
    "from",
    "how",
    "is",
    "of",
    "our",
    "the",
    "this",
    "to",
    "what",
    "when",
    "which",
    "who",
    "with",
    "show",
    "give",
}
ANALYTICAL_CUES = {
    "average",
    "bottom",
    "compare",
    "comparison",
    "count",
    "daily",
    "dem",
    "group",
    "highest",
    "lowest",
    "max",
    "mean",
    "min",
    "monthly",
    "percent",
    "percentage",
    "ratio",
    "rate",
    "revenue",
    "sales",
    "so",
    "sum",
    "theo",
    "thong",
    "top",
    "total",
    "trend",
    "trung",
    "ty",
    "weekly",
    "yearly",
    "xu",
}

ConnectorFactory = Callable[[Session, Datasource, Settings], DataSourceConnector]


def _append_trace(
    session: Session,
    run: QueryRun,
    current: RuntimeStatus,
    event: str,
    outcome: str,
    *,
    duration_ms: int | None = None,
    error_code: str | None = None,
    details: dict[str, object] | None = None,
) -> RuntimeStatus:
    next_status = transition(current, outcome)
    run.trace_json = [
        *run.trace_json,
        trace_event(
            len(run.trace_json) + 1,
            current,
            event,
            outcome,
            duration_ms=duration_ms,
            error_code=error_code,
            details=details,
        ),
    ]
    run.status = next_status.value
    session.commit()
    return next_status


def _fail(
    session: Session,
    run: QueryRun,
    current: RuntimeStatus,
    outcome: str,
    event: str,
    code: str,
    message: str,
) -> RuntimeStatus:
    run.error_code = code
    run.error_message = message
    return _append_trace(
        session,
        run,
        current,
        event,
        outcome,
        error_code=code,
    )


def _is_ambiguous(question: str) -> bool:
    return bool(VAGUE_CUSTOMER_RANKING.search(question)) and not bool(
        CUSTOMER_MEASURES.search(question)
    )


def _clarification_suggestions() -> list[str]:
    return [
        "Top customers by revenue",
        "Top customers by order count",
        "Top customers by average order value",
    ]


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", value))
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).lower()


def _tokens(value: str) -> set[str]:
    result: set[str] = set()
    for token in TOKEN.findall(_normalized(value)):
        if token in STOP_WORDS:
            continue
        result.add(token)
        if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
            result.add(token[:-1])
    return result


def _is_meta_request(question: str) -> bool:
    return bool(META_REQUEST.search(_normalized(question)))


def _unsafe_request_code(question: str) -> str | None:
    normalized = _normalized(question)
    if PROMPT_INJECTION.search(normalized):
        return "prompt_injection_blocked"
    if UNSAFE_REQUEST.search(normalized) or OBFUSCATED_WRITE_REQUEST.search(normalized):
        return "unsafe_request_blocked"
    return None


def _is_out_of_scope(question: str, context: RetrievalResponse, minimum_similarity: float) -> bool:
    semantic_scores = [
        entity.semantic_score
        for entity in context.entities
        if entity.selection_source != "relationship_expansion"
        and entity.semantic_score is not None
    ]
    vocabulary: set[str] = set()
    for entity in context.entities:
        vocabulary.update(_tokens(entity.name))
        vocabulary.update(_tokens(entity.description or ""))
        for field in entity.fields:
            vocabulary.update(_tokens(field.name))
            vocabulary.update(_tokens(field.description or ""))
        for term in entity.business_terms:
            vocabulary.update(_tokens(term))
        for metric in entity.metrics:
            vocabulary.update(_tokens(metric.name))
            vocabulary.update(_tokens(metric.description or ""))
    question_tokens = _tokens(question)
    has_domain_anchor = bool(question_tokens & vocabulary)
    has_analytical_cue = bool(question_tokens & ANALYTICAL_CUES)
    similarity_sufficient = bool(semantic_scores and max(semantic_scores) >= minimum_similarity)
    return not has_domain_anchor and not (has_analytical_cue and similarity_sufficient)


def _validation_payload(result: SQLValidationResult, explain_valid: bool) -> dict[str, object]:
    return {
        "ast_valid": result.valid,
        "explain_valid": explain_valid,
        "unsafe": result.unsafe,
        "error_code": result.error_code,
        "issues": list(result.issues),
    }


def run_postgres_query(
    session: Session,
    datasource_id: UUID,
    question: str,
    *,
    settings: Settings | None = None,
    generation_provider: LLMProvider | None = None,
    retrieval_provider: LLMProvider | None = None,
    connector_factory: ConnectorFactory = build_datasource_connector,
    retrieval_strategy: Literal["vector", "hybrid"] | None = None,
) -> QueryRun:
    app_settings = settings or get_settings()
    datasource = session.get(Datasource, datasource_id)
    if datasource is None:
        raise AppError("datasource_not_found", "Datasource was not found", status_code=404)
    run = QueryRun(
        datasource_id=datasource.id,
        question=question,
        retrieved_context_ids=[],
        generated_query={},
        query_type=datasource.source_type,
        validation_result={},
        status=RuntimeStatus.RECEIVED.value,
        trace_json=[],
        warnings=[],
    )
    session.add(run)
    session.commit()
    state = RuntimeStatus.RECEIVED

    if datasource.status != "ready" or datasource.source_type != "postgresql":
        _fail(
            session,
            run,
            state,
            "datasource_unavailable",
            "resolve_datasource",
            "datasource_unavailable",
            "The selected PostgreSQL datasource is not ready",
        )
        return run
    unsafe_code = _unsafe_request_code(question)
    if unsafe_code is not None:
        _fail(
            session,
            run,
            state,
            "unsafe_request",
            "question_safety_precheck",
            unsafe_code,
            (
                "The request attempted to override system instructions and was blocked"
                if unsafe_code == "prompt_injection_blocked"
                else "The request asks to modify datasource data and was blocked"
            ),
        )
        return run
    if _is_meta_request(question):
        run.warnings = ["Ask only accepts analytical questions about the active datasource"]
        _fail(
            session,
            run,
            state,
            "out_of_scope",
            "question_scope_precheck",
            "question_out_of_scope",
            "Ask cannot answer questions about its model, prompt, or system configuration",
        )
        return run

    state = _append_trace(session, run, state, "resolve_datasource", "datasource_ready")
    try:
        context = retrieve_context(
            session,
            datasource.id,
            question,
            settings=app_settings,
            provider=retrieval_provider,
            query_run=run,
            strategy=retrieval_strategy,
        )
    except AppError as error:
        _fail(
            session,
            run,
            state,
            "retrieval_failed",
            "retrieve_context",
            error.code,
            error.message,
        )
        return run
    if _is_ambiguous(question):
        suggestions = _clarification_suggestions()
        run.validation_result = {"clarification_suggestions": suggestions}
        run.warnings = ["A complete metric is required before query generation"]
        _append_trace(
            session,
            run,
            state,
            "evaluate_context",
            "ambiguous",
            details={"suggestion_count": len(suggestions)},
        )
        return run
    if _is_out_of_scope(question, context, app_settings.retrieval_min_similarity):
        run.warnings = [
            "The question does not match the active datasource's known analytical context"
        ]
        _fail(
            session,
            run,
            state,
            "out_of_scope",
            "evaluate_context",
            "question_out_of_scope",
            "This question is outside the analytical scope of the active datasource",
        )
        return run
    state = _append_trace(
        session,
        run,
        state,
        "evaluate_context",
        "context_sufficient",
        details={
            "entity_count": len(context.entities),
            "relationship_count": len(context.relationships),
            "retrieval_strategy": context.strategy,
            "retrieval_config_version": context.config_version,
            "top_lexical_score": max(
                (item.lexical_score or 0.0 for item in context.entities), default=0.0
            ),
            "top_semantic_score": max(
                (item.semantic_score or -1.0 for item in context.entities), default=-1.0
            ),
            "top_fused_score": max(
                (item.fused_score or 0.0 for item in context.entities), default=0.0
            ),
        },
    )

    owns_generation_provider = generation_provider is None
    provider = generation_provider or build_semantic_provider(app_settings)
    if provider is None:
        _fail(
            session,
            run,
            state,
            "generation_failed",
            "generate_query",
            "generation_provider_not_configured",
            "Query generation provider is not configured",
        )
        return run

    connector: DataSourceConnector | None = None
    execution_result: QueryResult | None = None
    generated: GeneratedSQL
    validation: SQLValidationResult | None = None
    last_error_code = "query_invalid"
    last_issues: list[str] = []
    try:
        try:
            generated = generate_postgres_sql(provider, question, context)
        except (ProviderError, ValidationError) as error:
            code = error.code if isinstance(error, ProviderError) else "provider_invalid_response"
            message = (
                error.safe_message
                if isinstance(error, ProviderError)
                else "Query provider returned invalid structured data"
            )
            _fail(
                session,
                run,
                state,
                "generation_failed",
                "generate_query",
                code,
                message,
            )
            return run
        run.generated_query = generated.model_dump(mode="json")
        state = _append_trace(session, run, state, "generate_query", "structured_output_valid")
        try:
            connector = connector_factory(session, datasource, app_settings)
        except (AppError, ConnectorError) as error:
            _fail(
                session,
                run,
                state,
                "runtime_failed",
                "create_connector",
                error.code,
                error.message if isinstance(error, AppError) else error.safe_message,
            )
            return run

        while state not in TERMINAL_STATES:
            if state == RuntimeStatus.VALIDATE_QUERY:
                validation = validate_postgres_sql(
                    generated.sql,
                    context.entities,
                    set(datasource.allowed_schemas),
                )
                if validation.unsafe:
                    run.validation_result = _validation_payload(validation, False)
                    _fail(
                        session,
                        run,
                        state,
                        "unsafe",
                        "validate_query",
                        validation.error_code or "unsafe_sql_blocked",
                        "The generated query violated the read-only safety policy",
                    )
                    break
                if not validation.valid or validation.query is None:
                    last_error_code = validation.error_code or "query_validation_failed"
                    last_issues = list(validation.issues)
                    run.validation_result = _validation_payload(validation, False)
                    outcome = (
                        "repairable"
                        if run.repair_count < app_settings.query_max_repair_attempts
                        else "retry_exhausted"
                    )
                    if outcome == "retry_exhausted":
                        _fail(
                            session,
                            run,
                            state,
                            outcome,
                            "validate_query",
                            last_error_code,
                            "The query could not be validated within the repair limit",
                        )
                        break
                    state = _append_trace(
                        session,
                        run,
                        state,
                        "validate_query",
                        outcome,
                        error_code=last_error_code,
                    )
                    continue
                try:
                    connector.explain(
                        validation.query,
                        limits=_query_limits(app_settings),
                    )
                except ConnectorError as error:
                    last_error_code = error.code
                    last_issues = [error.safe_message]
                    run.validation_result = _validation_payload(validation, False)
                    if error.code == "query_blocked":
                        _fail(
                            session,
                            run,
                            state,
                            "unsafe",
                            "explain_query",
                            error.code,
                            error.safe_message,
                        )
                        break
                    outcome = (
                        "repairable"
                        if run.repair_count < app_settings.query_max_repair_attempts
                        else "retry_exhausted"
                    )
                    if outcome == "retry_exhausted":
                        _fail(
                            session,
                            run,
                            state,
                            outcome,
                            "explain_query",
                            error.code,
                            "PostgreSQL could not validate the query within the repair limit",
                        )
                        break
                    state = _append_trace(
                        session,
                        run,
                        state,
                        "explain_query",
                        outcome,
                        error_code=error.code,
                    )
                    continue
                run.validation_result = _validation_payload(validation, True)
                state = _append_trace(session, run, state, "validate_and_explain", "valid")
                continue

            if state == RuntimeStatus.REPAIR_QUERY:
                run.repair_count += 1
                try:
                    generated = repair_postgres_sql(
                        provider,
                        question,
                        context,
                        generated.sql,
                        last_error_code,
                        last_issues,
                    )
                except (ProviderError, ValidationError) as error:
                    code = (
                        error.code
                        if isinstance(error, ProviderError)
                        else "provider_invalid_response"
                    )
                    message = (
                        error.safe_message
                        if isinstance(error, ProviderError)
                        else "Query repair provider returned invalid structured data"
                    )
                    _fail(
                        session,
                        run,
                        state,
                        "repair_failed",
                        "repair_query",
                        code,
                        message,
                    )
                    break
                run.generated_query = generated.model_dump(mode="json")
                state = _append_trace(
                    session,
                    run,
                    state,
                    "repair_query",
                    "structured_output_valid",
                    details={"repair_count": run.repair_count},
                )
                continue

            if state == RuntimeStatus.EXECUTE_QUERY:
                if validation is None or validation.query is None:
                    raise AssertionError("Execution reached without a validated query")
                started = perf_counter()
                try:
                    execution_result = connector.execute_readonly(
                        validation.query,
                        limits=_query_limits(app_settings),
                    )
                except ConnectorError as error:
                    elapsed_ms = round((perf_counter() - started) * 1000)
                    last_error_code = error.code
                    last_issues = [error.safe_message]
                    if error.code == "query_blocked":
                        _fail(
                            session,
                            run,
                            state,
                            "unsafe",
                            "execute_query",
                            error.code,
                            error.safe_message,
                        )
                        break
                    repairable = error.code in {"query_invalid", "query_timeout"}
                    outcome = (
                        "repairable"
                        if repairable and run.repair_count < app_settings.query_max_repair_attempts
                        else "failed"
                    )
                    if outcome == "failed":
                        _fail(
                            session,
                            run,
                            state,
                            outcome,
                            "execute_query",
                            error.code,
                            error.safe_message,
                        )
                        break
                    state = _append_trace(
                        session,
                        run,
                        state,
                        "execute_query",
                        outcome,
                        duration_ms=elapsed_ms,
                        error_code=error.code,
                    )
                    continue
                run.duration_ms = round((perf_counter() - started) * 1000)
                run.row_count = len(execution_result.rows)
                state = _append_trace(
                    session,
                    run,
                    state,
                    "execute_query",
                    "success",
                    duration_ms=run.duration_ms,
                    details={
                        "row_count": run.row_count,
                        "truncated": execution_result.truncated,
                    },
                )
                continue

            if state == RuntimeStatus.VERIFY_RESULT:
                if execution_result is None:
                    raise AssertionError("Verification reached without an execution result")
                try:
                    verified = verify_result(
                        execution_result,
                        generated.expected_columns,
                        app_settings.datasource_max_rows,
                        run.duration_ms or 0,
                    )
                except (TypeError, ValueError):
                    _fail(
                        session,
                        run,
                        state,
                        "checks_failed",
                        "verify_result",
                        "result_verification_failed",
                        "The query result could not be verified safely",
                    )
                    break
                run.result_json = verified.payload
                run.warnings = list(verified.warnings)
                state = _append_trace(
                    session,
                    run,
                    state,
                    "verify_result",
                    "checks_complete",
                    details={"warning_count": len(verified.warnings)},
                )
                continue

            if state == RuntimeStatus.SELECT_VISUALIZATION:
                run.visualization_type = select_visualization(run.result_json)
                state = _append_trace(
                    session,
                    run,
                    state,
                    "select_visualization",
                    "config_produced",
                    details={"visualization_type": run.visualization_type},
                )
                continue

            raise AssertionError(f"Unhandled runtime state: {state.value}")
    finally:
        if connector is not None:
            connector.close()
        if owns_generation_provider:
            provider.close()
    return run


def _query_limits(settings: Settings) -> QueryLimits:
    return QueryLimits(
        timeout_ms=settings.datasource_statement_timeout_ms,
        max_rows=settings.datasource_max_rows,
    )

"""The complete deterministic V1 transition table."""

from harness.state import RuntimeStatus

TransitionKey = tuple[RuntimeStatus, str]

TRANSITIONS: dict[TransitionKey, RuntimeStatus] = {
    (RuntimeStatus.RECEIVED, "datasource_ready"): RuntimeStatus.RETRIEVE_CONTEXT,
    (RuntimeStatus.RECEIVED, "unsafe_request"): RuntimeStatus.BLOCKED,
    (RuntimeStatus.RECEIVED, "datasource_unavailable"): RuntimeStatus.FAILED,
    (RuntimeStatus.RETRIEVE_CONTEXT, "context_sufficient"): RuntimeStatus.GENERATE_QUERY,
    (RuntimeStatus.RETRIEVE_CONTEXT, "ambiguous"): RuntimeStatus.CLARIFICATION_REQUIRED,
    (RuntimeStatus.RETRIEVE_CONTEXT, "out_of_scope"): RuntimeStatus.OUT_OF_SCOPE,
    (RuntimeStatus.RETRIEVE_CONTEXT, "retrieval_failed"): RuntimeStatus.FAILED,
    (RuntimeStatus.GENERATE_QUERY, "structured_output_valid"): RuntimeStatus.VALIDATE_QUERY,
    (RuntimeStatus.GENERATE_QUERY, "generation_failed"): RuntimeStatus.FAILED,
    (RuntimeStatus.VALIDATE_QUERY, "unsafe"): RuntimeStatus.BLOCKED,
    (RuntimeStatus.VALIDATE_QUERY, "valid"): RuntimeStatus.EXECUTE_QUERY,
    (RuntimeStatus.VALIDATE_QUERY, "repairable"): RuntimeStatus.REPAIR_QUERY,
    (RuntimeStatus.VALIDATE_QUERY, "retry_exhausted"): RuntimeStatus.FAILED,
    (RuntimeStatus.VALIDATE_QUERY, "runtime_failed"): RuntimeStatus.FAILED,
    (RuntimeStatus.EXECUTE_QUERY, "success"): RuntimeStatus.VERIFY_RESULT,
    (RuntimeStatus.EXECUTE_QUERY, "repairable"): RuntimeStatus.REPAIR_QUERY,
    (RuntimeStatus.EXECUTE_QUERY, "unsafe"): RuntimeStatus.BLOCKED,
    (RuntimeStatus.EXECUTE_QUERY, "failed"): RuntimeStatus.FAILED,
    (RuntimeStatus.REPAIR_QUERY, "structured_output_valid"): RuntimeStatus.VALIDATE_QUERY,
    (RuntimeStatus.REPAIR_QUERY, "repair_failed"): RuntimeStatus.FAILED,
    (RuntimeStatus.VERIFY_RESULT, "checks_complete"): RuntimeStatus.SELECT_VISUALIZATION,
    (RuntimeStatus.VERIFY_RESULT, "checks_failed"): RuntimeStatus.FAILED,
    (RuntimeStatus.SELECT_VISUALIZATION, "config_produced"): RuntimeStatus.COMPLETED,
}


def transition(current: RuntimeStatus, outcome: str) -> RuntimeStatus:
    try:
        return TRANSITIONS[(current, outcome)]
    except KeyError as exc:
        raise ValueError(f"Invalid runtime transition: {current.value} + {outcome}") from exc

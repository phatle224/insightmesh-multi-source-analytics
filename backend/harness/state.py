"""Typed runtime states and terminal-state policy."""

from enum import StrEnum


class RuntimeStatus(StrEnum):
    RECEIVED = "received"
    RETRIEVE_CONTEXT = "retrieve_context"
    GENERATE_QUERY = "generate_query"
    VALIDATE_QUERY = "validate_query"
    EXECUTE_QUERY = "execute_query"
    REPAIR_QUERY = "repair_query"
    VERIFY_RESULT = "verify_result"
    SELECT_VISUALIZATION = "select_visualization"
    COMPLETED = "completed"
    CLARIFICATION_REQUIRED = "clarification_required"
    BLOCKED = "blocked"
    FAILED = "failed"


TERMINAL_STATES = {
    RuntimeStatus.COMPLETED,
    RuntimeStatus.CLARIFICATION_REQUIRED,
    RuntimeStatus.BLOCKED,
    RuntimeStatus.FAILED,
}

"""Atlas diagnostics are assembled by the runtime manager from cached state only."""

from typing import Any


def safe_provider_diagnostic(value: dict[str, Any]) -> dict[str, Any]:
    """Return the explicit public provider-diagnostic shape, never provider internals."""
    fields = (
        "provider_id",
        "display_name",
        "version",
        "contract_version",
        "lifecycle_state",
        "readiness",
        "capabilities",
        "required",
        "enabled",
        "consecutive_health_failures",
        "consecutive_health_successes",
        "last_health_check_at",
        "safe_dependency_states",
    )
    return {field: value.get(field) for field in fields}

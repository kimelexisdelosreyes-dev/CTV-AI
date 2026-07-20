"""Safe Atlas error taxonomy.

Raw exception details are deliberately retained only in server logs.
"""

from enum import StrEnum


class AtlasErrorCategory(StrEnum):
    DISABLED = "atlas_disabled"
    NOT_INITIALIZED = "atlas_not_initialized"
    RUNTIME_FAILED = "atlas_runtime_failed"
    PROVIDER_DUPLICATE = "atlas_provider_duplicate"
    PROVIDER_INVALID_DEFINITION = "atlas_provider_invalid_definition"
    PROVIDER_CONTRACT_MISMATCH = "atlas_provider_contract_mismatch"
    PROVIDER_DISABLED = "atlas_provider_disabled"
    PROVIDER_NOT_READY = "atlas_provider_not_ready"
    PROVIDER_UNAVAILABLE = "atlas_provider_unavailable"
    PROVIDER_INITIALIZATION_FAILED = "atlas_provider_initialization_failed"
    PROVIDER_HEALTH_FAILED = "atlas_provider_health_failed"
    PROVIDER_READINESS_FAILED = "atlas_provider_readiness_failed"
    PROVIDER_SHUTDOWN_FAILED = "atlas_provider_shutdown_failed"
    PROVIDER_TIMEOUT = "atlas_provider_timeout"
    PROVIDER_DEPENDENCY_UNAVAILABLE = "atlas_provider_dependency_unavailable"
    INVALID_LIFECYCLE_TRANSITION = "atlas_invalid_lifecycle_transition"
    CONTEXT_PACKAGE_INVALID = "atlas_context_package_invalid"
    INTERNAL_ERROR = "atlas_internal_error"


SAFE_ATLAS_MESSAGES: dict[AtlasErrorCategory, str] = {
    AtlasErrorCategory.DISABLED: "Atlas is disabled.",
    AtlasErrorCategory.NOT_INITIALIZED: "Atlas is not initialized.",
    AtlasErrorCategory.RUNTIME_FAILED: "Atlas is unavailable.",
    AtlasErrorCategory.PROVIDER_DUPLICATE: "The Atlas provider is already registered.",
    AtlasErrorCategory.PROVIDER_INVALID_DEFINITION: "The Atlas provider definition is invalid.",
    AtlasErrorCategory.PROVIDER_CONTRACT_MISMATCH: "The Atlas provider contract is incompatible.",
    AtlasErrorCategory.PROVIDER_DISABLED: "The Atlas provider is disabled.",
    AtlasErrorCategory.PROVIDER_NOT_READY: "The Atlas provider is not ready.",
    AtlasErrorCategory.PROVIDER_UNAVAILABLE: "The Atlas provider is unavailable.",
    AtlasErrorCategory.PROVIDER_INITIALIZATION_FAILED: "The Atlas provider could not be initialized.",
    AtlasErrorCategory.PROVIDER_HEALTH_FAILED: "The Atlas provider health check failed.",
    AtlasErrorCategory.PROVIDER_READINESS_FAILED: "The Atlas provider readiness check failed.",
    AtlasErrorCategory.PROVIDER_SHUTDOWN_FAILED: "The Atlas provider shutdown failed.",
    AtlasErrorCategory.PROVIDER_TIMEOUT: "The Atlas provider operation timed out.",
    AtlasErrorCategory.PROVIDER_DEPENDENCY_UNAVAILABLE: "An Atlas provider dependency is unavailable.",
    AtlasErrorCategory.INVALID_LIFECYCLE_TRANSITION: "The Atlas provider lifecycle transition is invalid.",
    AtlasErrorCategory.CONTEXT_PACKAGE_INVALID: "The Atlas context package is invalid.",
    AtlasErrorCategory.INTERNAL_ERROR: "Atlas failed safely.",
}


class AtlasRuntimeError(RuntimeError):
    def __init__(self, category: AtlasErrorCategory, safe_message: str | None = None) -> None:
        self.category = category
        self.safe_message = safe_message or SAFE_ATLAS_MESSAGES[category]
        super().__init__(self.safe_message)


class AtlasProviderRegistrationError(ValueError):
    """A server-owned provider could not be registered safely."""

    def __init__(self, category: AtlasErrorCategory, message: str | None = None) -> None:
        self.category = category
        super().__init__(message or SAFE_ATLAS_MESSAGES[category])

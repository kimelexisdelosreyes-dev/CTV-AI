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
    COMPILER_CONTRACT_MISMATCH = "atlas_compiler_contract_mismatch"
    COMPILE_REQUEST_INVALID = "atlas_compile_request_invalid"
    COMPILATION_SNAPSHOT_INVALID = "atlas_compilation_snapshot_invalid"
    COMPILER_POLICY_INVALID = "atlas_compiler_policy_invalid"
    PROVIDER_INPUT_INVALID = "atlas_provider_input_invalid"
    AIR_INVALID = "atlas_air_invalid"
    PROVENANCE_INVALID = "atlas_provenance_invalid"
    GRAPH_CONTRACT_INVALID = "atlas_graph_contract_invalid"
    SCORE_CONTRACT_INVALID = "atlas_score_contract_invalid"
    BUDGET_CONTRACT_INVALID = "atlas_budget_contract_invalid"
    CONFLICT_CONTRACT_INVALID = "atlas_conflict_contract_invalid"
    MANIFEST_INVALID = "atlas_manifest_invalid"
    PACKAGE_FINGERPRINT_INVALID = "atlas_package_fingerprint_invalid"
    CANONICALIZATION_FAILED = "atlas_canonicalization_failed"
    DEEP_IMMUTABILITY_VIOLATION = "atlas_deep_immutability_violation"
    CONTRACT_SIZE_EXCEEDED = "atlas_contract_size_exceeded"
    COMPILER_NOT_READY = "atlas_not_ready"
    COMPILER_STOPPING = "atlas_stopping"
    COMPILATION_FAILED = "atlas_compilation_failed"
    PROVIDER_ORCHESTRATION_FAILED = "atlas_provider_orchestration_failed"
    PROVIDER_ORCHESTRATION_REQUIRED_FAILED = "atlas_required_provider_unavailable"


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
    AtlasErrorCategory.COMPILER_CONTRACT_MISMATCH: "The Atlas compiler contract is incompatible.",
    AtlasErrorCategory.COMPILE_REQUEST_INVALID: "The Atlas compile request is invalid.",
    AtlasErrorCategory.COMPILATION_SNAPSHOT_INVALID: "The Atlas compilation snapshot is invalid.",
    AtlasErrorCategory.COMPILER_POLICY_INVALID: "The Atlas compiler policy is invalid.",
    AtlasErrorCategory.PROVIDER_INPUT_INVALID: "The Atlas provider input is invalid.",
    AtlasErrorCategory.AIR_INVALID: "The Atlas intermediate representation is invalid.",
    AtlasErrorCategory.PROVENANCE_INVALID: "The Atlas provenance is invalid.",
    AtlasErrorCategory.GRAPH_CONTRACT_INVALID: "The Atlas graph contract is invalid.",
    AtlasErrorCategory.SCORE_CONTRACT_INVALID: "The Atlas score contract is invalid.",
    AtlasErrorCategory.BUDGET_CONTRACT_INVALID: "The Atlas budget contract is invalid.",
    AtlasErrorCategory.CONFLICT_CONTRACT_INVALID: "The Atlas conflict contract is invalid.",
    AtlasErrorCategory.MANIFEST_INVALID: "The Atlas manifest is invalid.",
    AtlasErrorCategory.PACKAGE_FINGERPRINT_INVALID: "The Atlas package fingerprint is invalid.",
    AtlasErrorCategory.CANONICALIZATION_FAILED: "Atlas canonicalization failed safely.",
    AtlasErrorCategory.DEEP_IMMUTABILITY_VIOLATION: "The Atlas contract is not immutable.",
    AtlasErrorCategory.CONTRACT_SIZE_EXCEEDED: "The Atlas contract exceeds its size limit.",
    AtlasErrorCategory.COMPILER_NOT_READY: "Atlas is not ready to compile context.",
    AtlasErrorCategory.COMPILER_STOPPING: "Atlas is stopping and cannot compile context.",
    AtlasErrorCategory.COMPILATION_FAILED: "Atlas compilation failed safely.",
    AtlasErrorCategory.PROVIDER_ORCHESTRATION_FAILED: "Atlas provider orchestration failed safely.",
    AtlasErrorCategory.PROVIDER_ORCHESTRATION_REQUIRED_FAILED: "A required Atlas provider is unavailable.",
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

"""Safe state-derived Atlas readiness helpers."""

from app.atlas.models import AtlasProviderLifecycleState, AtlasProviderReadiness, AtlasProviderRuntimeRecord


def state_readiness(record: AtlasProviderRuntimeRecord) -> AtlasProviderReadiness:
    ready = record.state in {
        AtlasProviderLifecycleState.READY,
        AtlasProviderLifecycleState.DEGRADED,
    }
    capabilities = record.definition.capabilities if ready else frozenset()
    return AtlasProviderReadiness(
        ready=ready,
        reason_category=None if ready else f"atlas_provider_{record.state.value}",
        available_capabilities=capabilities,
        unavailable_capabilities=(frozenset() if ready else record.definition.capabilities),
    )

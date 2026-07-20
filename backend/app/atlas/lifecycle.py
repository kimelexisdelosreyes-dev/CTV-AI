from __future__ import annotations

from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError
from app.atlas.models import AtlasProviderLifecycleState, AtlasProviderRuntimeRecord, utc_now


VALID_PROVIDER_TRANSITIONS: dict[
    AtlasProviderLifecycleState, frozenset[AtlasProviderLifecycleState]
] = {
    AtlasProviderLifecycleState.REGISTERED: frozenset(
        {AtlasProviderLifecycleState.INITIALIZING, AtlasProviderLifecycleState.DISABLED}
    ),
    AtlasProviderLifecycleState.INITIALIZING: frozenset(
        {
            AtlasProviderLifecycleState.READY,
            AtlasProviderLifecycleState.DEGRADED,
            AtlasProviderLifecycleState.UNAVAILABLE,
            AtlasProviderLifecycleState.FAILED,
        }
    ),
    AtlasProviderLifecycleState.READY: frozenset(
        {
            AtlasProviderLifecycleState.DEGRADED,
            AtlasProviderLifecycleState.UNAVAILABLE,
            AtlasProviderLifecycleState.DRAINING,
        }
    ),
    AtlasProviderLifecycleState.DEGRADED: frozenset(
        {
            AtlasProviderLifecycleState.READY,
            AtlasProviderLifecycleState.UNAVAILABLE,
            AtlasProviderLifecycleState.DRAINING,
        }
    ),
    AtlasProviderLifecycleState.UNAVAILABLE: frozenset(
        {
            AtlasProviderLifecycleState.READY,
            AtlasProviderLifecycleState.DEGRADED,
            AtlasProviderLifecycleState.DRAINING,
        }
    ),
    AtlasProviderLifecycleState.DISABLED: frozenset({AtlasProviderLifecycleState.STOPPED}),
    AtlasProviderLifecycleState.DRAINING: frozenset({AtlasProviderLifecycleState.STOPPED}),
    AtlasProviderLifecycleState.STOPPED: frozenset(),
    AtlasProviderLifecycleState.FAILED: frozenset({AtlasProviderLifecycleState.STOPPED}),
}


def transition_record(
    record: AtlasProviderRuntimeRecord,
    target: AtlasProviderLifecycleState,
) -> None:
    if target == record.state:
        return
    if target not in VALID_PROVIDER_TRANSITIONS[record.state]:
        raise AtlasRuntimeError(AtlasErrorCategory.INVALID_LIFECYCLE_TRANSITION)
    now = utc_now()
    record.previous_state = record.state
    record.state = target
    record.state_changed_at = now
    if target == AtlasProviderLifecycleState.STOPPED:
        record.stopped_at = now

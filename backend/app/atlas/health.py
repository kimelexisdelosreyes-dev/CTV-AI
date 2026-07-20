"""Atlas health result helpers.

The runtime invokes health hooks only during bounded initialization/polling;
these helpers never call collection, inference, or enterprise services.
"""

from app.atlas.models import AtlasHealthStatus, AtlasProviderHealth, utc_now


def failed_health(
    *,
    unavailable: bool,
    consecutive_failures: int,
    timeout: bool = False,
) -> AtlasProviderHealth:
    return AtlasProviderHealth(
        status=AtlasHealthStatus.UNAVAILABLE if unavailable else AtlasHealthStatus.DEGRADED,
        safe_message=(
            "Atlas provider health check timed out."
            if timeout
            else "Atlas provider health check failed safely."
        ),
        consecutive_failures=consecutive_failures,
        last_failure_at=utc_now(),
    )

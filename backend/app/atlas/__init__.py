"""Atlas Enterprise Context Engine runtime foundation.

Sprint 3.1 intentionally provides lifecycle and contract infrastructure only.
It does not register providers, collect enterprise data, or participate in
request processing.
"""

from app.atlas.constants import (
    ATLAS_CONTEXT_PACKAGE_VERSION,
    ATLAS_PROVIDER_CONTRACT_VERSION,
    ATLAS_RUNTIME_VERSION,
)

__all__ = [
    "ATLAS_CONTEXT_PACKAGE_VERSION",
    "ATLAS_PROVIDER_CONTRACT_VERSION",
    "ATLAS_RUNTIME_VERSION",
]

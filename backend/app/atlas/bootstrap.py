"""Static Atlas runtime ownership.

No provider is registered in Sprint 3.1. Future providers must be approved and
registered here during application construction, never from requests or config.
"""

from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager


atlas_provider_registry = AtlasProviderRegistry()
atlas_runtime_manager = AtlasRuntimeManager(atlas_provider_registry)

"""Static Atlas runtime ownership.

No provider is registered in Sprint 3.1. Future providers must be approved and
registered here during application construction, never from requests or config.
"""

from app.atlas.registry import AtlasProviderRegistry
from app.atlas.runtime_manager import AtlasRuntimeManager
from app.atlas.providers.nexus import NexusProvider
from app.shadow_mode import AtlasShadowModeService


atlas_provider_registry = AtlasProviderRegistry()
atlas_nexus_provider = NexusProvider()
atlas_provider_registry.register(atlas_nexus_provider)
atlas_runtime_manager = AtlasRuntimeManager(atlas_provider_registry)
atlas_shadow_mode_service = AtlasShadowModeService(atlas_runtime_manager)

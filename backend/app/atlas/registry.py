from __future__ import annotations

from collections.abc import Iterable

from app.atlas.constants import ATLAS_PROVIDER_CONTRACT_VERSION
from app.atlas.errors import AtlasErrorCategory, AtlasProviderRegistrationError
from app.atlas.models import AtlasProviderDefinition
from app.atlas.provider import AtlasProvider


def contract_compatible(
    candidate: str,
    runtime: str = ATLAS_PROVIDER_CONTRACT_VERSION,
) -> bool:
    """Accept same-major contracts no newer than the runtime's minor version."""
    try:
        candidate_major, candidate_minor = (int(part) for part in candidate.split(".", 1))
        runtime_major, runtime_minor = (int(part) for part in runtime.split(".", 1))
    except (TypeError, ValueError):
        return False
    return candidate_major == runtime_major and candidate_minor <= runtime_minor


class AtlasProviderRegistry:
    """Static, server-owned Atlas provider registry with no discovery mechanism."""

    def __init__(self) -> None:
        self._providers: dict[str, AtlasProvider] = {}
        self._runtime_initialization_started = False

    def begin_runtime_initialization(self) -> None:
        self._runtime_initialization_started = True

    def register(self, provider: AtlasProvider) -> None:
        if not isinstance(provider, AtlasProvider):
            raise AtlasProviderRegistrationError(AtlasErrorCategory.PROVIDER_INVALID_DEFINITION)
        definition = getattr(provider, "definition", None)
        if not isinstance(definition, AtlasProviderDefinition):
            raise AtlasProviderRegistrationError(AtlasErrorCategory.PROVIDER_INVALID_DEFINITION)
        if definition.provider_id in self._providers:
            raise AtlasProviderRegistrationError(AtlasErrorCategory.PROVIDER_DUPLICATE)
        if not contract_compatible(definition.contract_version):
            raise AtlasProviderRegistrationError(AtlasErrorCategory.PROVIDER_CONTRACT_MISMATCH)
        self._providers[definition.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        if self._runtime_initialization_started:
            raise AtlasProviderRegistrationError(
                AtlasErrorCategory.PROVIDER_INVALID_DEFINITION,
                "Providers cannot be unregistered after Atlas runtime initialization.",
            )
        if provider_id not in self._providers:
            raise AtlasProviderRegistrationError(AtlasErrorCategory.PROVIDER_INVALID_DEFINITION)
        del self._providers[provider_id]

    def get(self, provider_id: str) -> AtlasProvider:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise AtlasProviderRegistrationError(AtlasErrorCategory.PROVIDER_INVALID_DEFINITION) from exc

    def definitions(self) -> tuple[AtlasProviderDefinition, ...]:
        return tuple(self._providers[provider_id].definition for provider_id in sorted(self._providers))

    def providers(self) -> Iterable[tuple[str, AtlasProvider]]:
        for provider_id in sorted(self._providers):
            yield provider_id, self._providers[provider_id]

    def __contains__(self, provider_id: object) -> bool:
        return provider_id in self._providers

    def __len__(self) -> int:
        return len(self._providers)

from __future__ import annotations

from enum import StrEnum


class ForgeContextErrorCategory(StrEnum):
    ADAPTER_DISABLED = "forge_atlas_adapter_disabled"
    ATLAS_DISABLED = "forge_atlas_runtime_disabled"
    PACKAGE_INVALID = "forge_atlas_package_invalid"
    PACKAGE_VERSION_UNSUPPORTED = "forge_atlas_package_version_unsupported"
    PACKAGE_FINGERPRINT_INVALID = "forge_atlas_package_fingerprint_invalid"
    MANIFEST_REFERENCE_INVALID = "forge_atlas_manifest_reference_invalid"
    PACKAGE_LIMIT_EXCEEDED = "forge_atlas_package_limit_exceeded"


class ForgeContextError(RuntimeError):
    """Stable, content-free adapter failure."""

    def __init__(self, category: ForgeContextErrorCategory) -> None:
        self.category = category
        super().__init__(category.value)

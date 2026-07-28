from __future__ import annotations

from app.atlas.canonical import canonical_json
from app.forge.context_adapter import ForgeContextWindow


MEMORY_SECTION_MARKER = "\n\nMemory\n"


def render_atlas_context(window: ForgeContextWindow) -> str:
    return canonical_json(
        {
            "blocks": [block.canonical_dict() for block in window.context_blocks],
            "package_fingerprint": window.package_fingerprint,
            "manifest_reference": window.manifest_reference.canonical_dict(),
        }
    )


def integrate_atlas_context(
    existing_prompt: str,
    context_window: ForgeContextWindow | None,
    *,
    atlas_enabled: bool,
    forge_adapter_enabled: bool,
) -> str:
    """Insert Atlas immediately before Memory; disabled paths return the same string object."""
    if not atlas_enabled or not forge_adapter_enabled or context_window is None:
        return existing_prompt
    section = f"\n\nAtlas Context\n{render_atlas_context(context_window)}"
    if MEMORY_SECTION_MARKER in existing_prompt:
        return existing_prompt.replace(MEMORY_SECTION_MARKER, section + MEMORY_SECTION_MARKER, 1)
    return existing_prompt + section

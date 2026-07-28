"""Forge consumes immutable Atlas artifacts through a one-way adapter boundary."""

from app.forge.context_adapter import (
    FORGE_CONTEXT_VERSION,
    ForgeContextAdapter,
    ForgeContextBlock,
    ForgeContextWindow,
)

__all__ = [
    "FORGE_CONTEXT_VERSION",
    "ForgeContextAdapter",
    "ForgeContextBlock",
    "ForgeContextWindow",
]

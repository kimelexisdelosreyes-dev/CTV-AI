from dataclasses import dataclass


@dataclass(frozen=True)
class CompositionTrace:
    """Safe operational trace: deliberately excludes all composition content."""
    composition_id: str
    stage_order: tuple[str, ...]
    duration_ms: int
    warnings: tuple[str, ...]

from dataclasses import dataclass


@dataclass(frozen=True)
class CompositionStatistics:
    stage_count: int
    duration_ms: int
    warning_count: int

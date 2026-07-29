from dataclasses import dataclass
@dataclass(frozen=True)
class MemoryPolicy: minimum_confidence:float=0.0

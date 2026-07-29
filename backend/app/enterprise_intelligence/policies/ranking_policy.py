from dataclasses import dataclass
@dataclass(frozen=True)
class RankingPolicy: preserve_input_order:bool=True

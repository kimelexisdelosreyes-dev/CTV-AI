from dataclasses import dataclass
@dataclass(frozen=True)
class CapabilityMetadata: author:str; version:str; created:str; updated:str; compatibility:tuple[str,...]=(); category:str=""

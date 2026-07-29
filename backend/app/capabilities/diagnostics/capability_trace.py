from dataclasses import dataclass
@dataclass(frozen=True)
class CapabilityTrace: capability_id:str; action:str; duration_ms:int; warnings:tuple[str,...]=()

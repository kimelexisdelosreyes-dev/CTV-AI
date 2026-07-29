from dataclasses import dataclass
@dataclass(frozen=True)
class CapabilityHealth: healthy:bool; warnings:tuple[str,...]=(); errors:tuple[str,...]=(); last_validation:str|None=None

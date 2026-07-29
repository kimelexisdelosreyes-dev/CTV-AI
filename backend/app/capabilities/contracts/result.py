from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class CapabilityResult:
 status:str; metadata:tuple[tuple[str,str],...]=(); warnings:tuple[str,...]=(); output_reference:str|None=None
 def to_dict(self): return asdict(self)

from dataclasses import dataclass
@dataclass(frozen=True)
class CapabilityRequest:
 capability_id:str; request_context:tuple[tuple[str,str],...]=(); enterprise_context:tuple[tuple[str,str],...]=(); parameters:tuple[tuple[str,str],...]=()

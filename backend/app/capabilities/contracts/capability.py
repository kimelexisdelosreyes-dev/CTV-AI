from dataclasses import dataclass
@dataclass(frozen=True)
class CapabilityDefinition:
 id:str; name:str; description:str; category:str; version:str; permissions:tuple[str,...]=(); supported_inputs:tuple[str,...]=(); supported_outputs:tuple[str,...]=()

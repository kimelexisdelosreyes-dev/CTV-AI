from dataclasses import dataclass
@dataclass(frozen=True)
class ExecutionContext: request:object; enterprise_context:tuple[tuple[str,str],...]=(); trace:tuple[tuple[str,str],...]=()

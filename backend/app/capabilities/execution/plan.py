from dataclasses import dataclass
@dataclass(frozen=True)
class ExecutionPlan: capability_id:str; prepared_context:tuple[tuple[str,str],...]=(); parameters:tuple[tuple[str,str],...]=(); execution_mode:str="synchronous"

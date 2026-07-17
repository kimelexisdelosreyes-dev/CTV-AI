from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextRequirements:
    include_knowledge: bool = False
    include_operations: bool = False
    include_employee: bool = False
    include_history: bool = False
    include_system_instructions: bool = True
    knowledge_collections: list[str] = field(default_factory=list)
    max_knowledge_chunks: int = 0
    max_knowledge_chars: int = 0
    max_operational_tasks: int = 0
    max_operational_chars: int = 0
    max_employee_context_chars: int = 0
    max_history_messages: int = 0
    max_history_chars: int = 0
    max_total_prompt_chars: int = 0

    def selected_context_types(self) -> list[str]:
        selected: list[str] = []
        if self.include_knowledge:
            selected.append("knowledge")
        if self.include_operations:
            selected.append("operations")
        if self.include_employee:
            selected.append("employee")
        if self.include_history:
            selected.append("history")
        if self.include_system_instructions:
            selected.append("system")
        return selected

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "include_knowledge": self.include_knowledge,
            "include_operations": self.include_operations,
            "include_employee": self.include_employee,
            "include_history": self.include_history,
            "include_system_instructions": self.include_system_instructions,
            "knowledge_collections": list(self.knowledge_collections),
            "max_knowledge_chunks": self.max_knowledge_chunks,
            "max_knowledge_chars": self.max_knowledge_chars,
            "max_operational_tasks": self.max_operational_tasks,
            "max_operational_chars": self.max_operational_chars,
            "max_employee_context_chars": self.max_employee_context_chars,
            "max_history_messages": self.max_history_messages,
            "max_history_chars": self.max_history_chars,
            "max_total_prompt_chars": self.max_total_prompt_chars,
            "selected_context_types": self.selected_context_types(),
        }

from __future__ import annotations

import warnings

from app.agents.errors import AgentRegistrationError
from app.agents.models import CapabilityDefinition


class CapabilityCatalog:
    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityDefinition] = {}

    def register(self, definition: CapabilityDefinition) -> None:
        if definition.capability_id in self._capabilities:
            raise AgentRegistrationError(
                f"Duplicate capability ID: {definition.capability_id}"
            )
        if definition.external_side_effects or not definition.read_only:
            raise AgentRegistrationError(
                "Chapter 2 accepts only read-only capabilities without external side effects."
            )
        self._capabilities[definition.capability_id] = definition

    def get(self, capability_id: str) -> CapabilityDefinition:
        try:
            definition = self._capabilities[capability_id]
        except KeyError as exc:
            raise AgentRegistrationError(f"Unknown capability: {capability_id}") from exc
        if definition.deprecated:
            warnings.warn(
                f"Capability {capability_id} is deprecated.",
                DeprecationWarning,
                stacklevel=2,
            )
        return definition

    def definitions(self) -> list[CapabilityDefinition]:
        return list(self._capabilities.values())

    def __contains__(self, capability_id: str) -> bool:
        return capability_id in self._capabilities


def build_core_capability_catalog() -> CapabilityCatalog:
    catalog = CapabilityCatalog()
    groups = {
        "knowledge": (
            {"knowledge_search", "policy_lookup", "document_summary", "evidence_retrieval"},
            frozenset({"knowledge.read"}),
            "KnowledgeEvidenceV1",
            True,
        ),
        "operations": (
            {"operations_status", "overdue_tasks", "priorities", "workload_summary", "project_status"},
            frozenset({"operations.read"}),
            "OperationsSnapshotEvidenceV1",
            True,
        ),
        "employee": (
            {"employee_context", "responsibility_lookup", "role_context", "department_context"},
            frozenset({"employee.self"}),
            "EmployeeSelfContextV1",
            True,
        ),
        "reasoning": (
            {"compare", "synthesize", "recommend", "risk_analysis", "tradeoff_analysis"},
            frozenset({"reasoning.use"}),
            "ReasoningSummaryV1",
            False,
        ),
        "composition": (
            {"executive_summary", "final_answer", "structured_brief"},
            frozenset({"compose.use"}),
            "CompanyBrainAnswerV1",
            False,
        ),
    }
    for group, (capabilities, permissions, output_schema, evidence_required) in groups.items():
        for capability_id in sorted(capabilities):
            catalog.register(
                CapabilityDefinition(
                    capability_id=capability_id,
                    description=f"Read-only {group} capability: {capability_id}.",
                    input_schema=f"{group.title()}CapabilityInputV1",
                    output_schema=output_schema,
                    required_permissions=permissions,
                    data_classification="confidential" if group == "employee" else "internal",
                    evidence_required=evidence_required,
                    allow_partial=group not in {"composition"},
                )
            )
    return catalog


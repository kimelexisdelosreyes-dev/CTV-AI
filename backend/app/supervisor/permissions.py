from dataclasses import dataclass
from uuid import UUID

from app.db.models.user import User, UserRole


CAPABILITY_PERMISSIONS: dict[str, frozenset[str]] = {
    "knowledge_search": frozenset({"knowledge.read"}),
    "policy_lookup": frozenset({"knowledge.read"}),
    "document_summary": frozenset({"knowledge.read"}),
    "evidence_retrieval": frozenset({"knowledge.read"}),
    "operations_status": frozenset({"operations.read"}),
    "overdue_tasks": frozenset({"operations.read"}),
    "priorities": frozenset({"operations.read"}),
    "workload_summary": frozenset({"operations.read"}),
    "project_status": frozenset({"operations.read"}),
    "employee_context": frozenset({"employee.self"}),
    "responsibility_lookup": frozenset({"employee.self"}),
    "role_context": frozenset({"employee.self"}),
    "department_context": frozenset({"employee.self"}),
    "compare": frozenset({"reasoning.use"}),
    "synthesize": frozenset({"reasoning.use"}),
    "recommend": frozenset({"reasoning.use"}),
    "risk_analysis": frozenset({"reasoning.use"}),
    "tradeoff_analysis": frozenset({"reasoning.use"}),
    "executive_summary": frozenset({"compose.use"}),
    "final_answer": frozenset({"compose.use"}),
    "structured_brief": frozenset({"compose.use"}),
}


@dataclass(frozen=True)
class AuthenticatedUserContext:
    id: UUID
    full_name: str
    role: UserRole


def snapshot_authenticated_user(
    user: User | AuthenticatedUserContext,
) -> AuthenticatedUserContext:
    if isinstance(user, AuthenticatedUserContext):
        return user
    return AuthenticatedUserContext(
        id=user.id,
        full_name=getattr(user, "full_name", "Authenticated user"),
        role=getattr(user, "role", UserRole.employee),
    )


def permissions_for_user(user: User | AuthenticatedUserContext) -> set[str]:
    permissions = {
        "knowledge.read",
        "operations.read",
        "employee.self",
        "reasoning.use",
        "compose.use",
    }
    if user.role in {UserRole.admin, UserRole.manager}:
        permissions.add("employee.manage")
    return permissions


def capability_allowed(capability: str, permissions: set[str]) -> bool:
    required = CAPABILITY_PERMISSIONS.get(capability)
    return required is not None and required.issubset(permissions)

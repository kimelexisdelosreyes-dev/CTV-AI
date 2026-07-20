from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.agents.bootstrap import agent_runtime_manager
from app.api.dependencies import get_current_user
from app.db.models.user import UserRole
from app.main import app


def _user(role: UserRole):
    return SimpleNamespace(role=role)


def test_agent_runtime_diagnostics_require_admin_and_remain_safe(monkeypatch) -> None:
    async def safe_status():
        return {
            "runtime_enabled": True,
            "runtime_contract_version": "1.0",
            "agents": [
                {
                    "agent_id": "knowledge_agent",
                    "lifecycle_state": "ready",
                    "capabilities": ["knowledge_search"],
                }
            ],
        }

    monkeypatch.setattr(agent_runtime_manager, "status", safe_status)
    app.dependency_overrides[get_current_user] = lambda: _user(UserRole.employee)
    try:
        forbidden = TestClient(app).get("/api/v1/runtime/agents/status")
        app.dependency_overrides[get_current_user] = lambda: _user(UserRole.admin)
        allowed = TestClient(app).get("/api/v1/runtime/agents/status")
    finally:
        app.dependency_overrides.clear()
    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    serialized = str(allowed.json()).lower()
    for secret_field in ("prompt", "task input", "employee id", "secret", "stack trace"):
        assert secret_field not in serialized


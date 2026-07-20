from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.atlas.bootstrap import atlas_runtime_manager
from app.db.models.user import UserRole
from app.main import app


def _user(role: UserRole):
    return SimpleNamespace(role=role)


def test_atlas_diagnostics_require_admin_and_hide_runtime_internals(monkeypatch) -> None:
    async def safe_status():
        return {
            "atlas_enabled": True,
            "runtime_state": "ready",
            "runtime_ready": True,
            "registered_provider_count": 0,
            "providers": [],
        }

    monkeypatch.setattr(atlas_runtime_manager, "status", safe_status)
    app.dependency_overrides[get_current_user] = lambda: _user(UserRole.employee)
    try:
        forbidden = TestClient(app).get("/api/v1/runtime/atlas/status")
        app.dependency_overrides[get_current_user] = lambda: _user(UserRole.admin)
        allowed = TestClient(app).get("/api/v1/runtime/atlas/status")
    finally:
        app.dependency_overrides.clear()
    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    serialized = str(allowed.json()).lower()
    for prohibited in ("prompt", "employee", "secret", "traceback", "database_url"):
        assert prohibited not in serialized


def test_normal_company_brain_modules_do_not_import_or_call_atlas() -> None:
    import inspect

    from app.services import knowledge_service
    from app.supervisor import service as supervisor_service

    assert "app.atlas" not in inspect.getsource(knowledge_service)
    assert "app.atlas" not in inspect.getsource(supervisor_service)


@pytest.mark.asyncio
async def test_fastapi_lifespan_initializes_and_stops_atlas_after_forge(monkeypatch) -> None:
    import app.main as main_module

    events: list[str] = []

    class Runtime:
        async def initialize(self, *_args):
            events.append("initialize")

        async def shutdown(self):
            events.append("shutdown")

    class Queue:
        async def start(self):
            events.append("queue_start")

        async def shutdown(self):
            events.append("queue_shutdown")

    forge = Runtime()
    atlas = Runtime()
    queue = Queue()

    async def embedding_ready():
        return {"status": "healthy"}

    monkeypatch.setattr(main_module, "configure_logging", lambda: None)
    monkeypatch.setattr(main_module, "register_builtin_connectors", lambda: None)
    monkeypatch.setattr(main_module, "inference_queue", queue)
    monkeypatch.setattr(main_module, "agent_runtime_manager", forge)
    monkeypatch.setattr(main_module, "atlas_runtime_manager", atlas)
    monkeypatch.setattr(main_module, "builtin_runtime_dependencies", lambda: {})
    monkeypatch.setattr(main_module.embedding_service, "readiness", embedding_ready)
    monkeypatch.setattr(main_module.settings, "ctv_one_monday_snapshot_refresh_enabled", False)

    async with main_module.lifespan(main_module.app):
        assert events == ["queue_start", "initialize", "initialize"]
    assert events == [
        "queue_start",
        "initialize",
        "initialize",
        "shutdown",
        "shutdown",
        "queue_shutdown",
    ]

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.routes import conversations as conversation_route
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.main import app
from app.services.conversation_service import ConversationNotFoundError


def user(user_id: uuid.UUID | None = None) -> User:
    return User(
        id=user_id or uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        password_hash="not-used",
        role=UserRole.employee,
    )


async def current_user():
    return user(uuid.UUID("00000000-0000-0000-0000-000000000001"))


async def fake_db():
    yield object()


def conversation(
    conversation_id: uuid.UUID | None = None,
    title: str = "Priorities",
):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=conversation_id or uuid.uuid4(),
        title=title,
        created_at=now,
        updated_at=now,
        archived_at=None,
    )


def message(
    conversation_id: uuid.UUID,
    role: str = "user",
    content: str = "Visible message",
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc),
    )


def test_conversation_routes_require_auth() -> None:
    response = TestClient(app).get("/api/v1/conversations")

    assert response.status_code == 401


def test_create_list_read_append_rename_archive_delete(monkeypatch) -> None:
    conversation_id = uuid.uuid4()
    created = conversation(conversation_id)
    stored_message = message(conversation_id)

    async def create_conversation(*_, **__):
        return created

    async def list_conversations(*_, **__):
        return [created], False

    async def read_conversation(*_, **__):
        return created, [stored_message], False

    async def append_message(*_, **__):
        return stored_message

    async def rename_conversation(*args):
        return conversation(conversation_id, args[-1])

    async def archive_conversation(*_, **__):
        archived = conversation(conversation_id)
        archived.archived_at = datetime.now(timezone.utc)
        return archived

    async def delete_conversation(*_, **__):
        return None

    monkeypatch.setattr(
        conversation_route.conversation_service,
        "create_conversation",
        create_conversation,
    )
    monkeypatch.setattr(
        conversation_route.conversation_service,
        "list_conversations",
        list_conversations,
    )
    monkeypatch.setattr(
        conversation_route.conversation_service,
        "read_conversation",
        read_conversation,
    )
    monkeypatch.setattr(
        conversation_route.conversation_service,
        "append_message",
        append_message,
    )
    monkeypatch.setattr(
        conversation_route.conversation_service,
        "rename_conversation",
        rename_conversation,
    )
    monkeypatch.setattr(
        conversation_route.conversation_service,
        "archive_conversation",
        archive_conversation,
    )
    monkeypatch.setattr(
        conversation_route.conversation_service,
        "delete_conversation",
        delete_conversation,
    )

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = fake_db
    client = TestClient(app)

    try:
        assert client.post("/api/v1/conversations", json={}).status_code == 201

        listed = client.get("/api/v1/conversations?limit=10&offset=0")
        assert listed.status_code == 200
        assert listed.json()["conversations"][0]["id"] == str(conversation_id)
        assert listed.json()["has_more"] is False

        read = client.get(f"/api/v1/conversations/{conversation_id}")
        assert read.status_code == 200
        assert read.json()["messages"][0]["content"] == "Visible message"

        appended = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"role": "user", "content": "Visible message"},
        )
        assert appended.status_code == 201
        assert appended.json()["role"] == "user"

        renamed = client.patch(
            f"/api/v1/conversations/{conversation_id}",
            json={"title": "Renamed"},
        )
        assert renamed.status_code == 200
        assert renamed.json()["title"] == "Renamed"

        archived = client.post(f"/api/v1/conversations/{conversation_id}/archive")
        assert archived.status_code == 200
        assert archived.json()["archived_at"] is not None

        deleted = client.delete(f"/api/v1/conversations/{conversation_id}")
        assert deleted.status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_conversation_ownership_not_found(monkeypatch) -> None:
    async def read_conversation(*_, **__):
        raise ConversationNotFoundError()

    monkeypatch.setattr(
        conversation_route.conversation_service,
        "read_conversation",
        read_conversation,
    )

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = fake_db

    try:
        response = TestClient(app).get(f"/api/v1/conversations/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404

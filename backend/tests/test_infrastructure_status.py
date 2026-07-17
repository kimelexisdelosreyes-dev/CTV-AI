import pytest

from app.services import infrastructure_service


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_embedding_status_uses_embedding_readiness(monkeypatch) -> None:
    async def fake_readiness():
        return {
            "status": "unavailable",
            "category": "embedding_model_missing",
            "model": "embeddinggemma",
        }

    monkeypatch.setattr(
        infrastructure_service.embedding_service,
        "readiness",
        fake_readiness,
    )

    status = await infrastructure_service.embedding_status()

    assert status["status"] == "unavailable"
    assert status["category"] == "embedding_model_missing"

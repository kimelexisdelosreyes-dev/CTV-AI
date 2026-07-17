import pytest

from app.core.knowledge_category_aliases import resolve_category_alias
from app.services import knowledge_service


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_collection_alias_resolution() -> None:
    assert resolve_category_alias("brand-guidelines") == ("branding",)
    assert resolve_category_alias("equipment-manuals") == ("cameras",)
    assert resolve_category_alias("technical-documentation") == ("cameras", "editing")
    assert resolve_category_alias("company-policies") == ("company-policies",)


@pytest.mark.anyio
async def test_empty_retrieval_result_returns_empty_list(monkeypatch) -> None:
    calls: list[str | None] = []

    async def fake_embed(_):
        return [[0.1, 0.2, 0.3]]

    async def fake_search(_embedding, _top_k, category):
        calls.append(category)
        return []

    monkeypatch.setattr(knowledge_service.embedding_service, "embed", fake_embed)
    monkeypatch.setattr(knowledge_service.vector_store, "search", fake_search)

    sources = await knowledge_service.search_knowledge(
        "show me equipment manuals",
        5,
        "equipment-manuals",
    )

    assert sources == []
    assert calls == ["cameras"]

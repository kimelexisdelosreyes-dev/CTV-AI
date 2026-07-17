import httpx
import pytest

from app.services import embedding_service as embedding_module
from app.services.embedding_service import (
    EmbeddingMalformedResponseError,
    EmbeddingModelMissingError,
    EmbeddingService,
    EmbeddingTimeoutError,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeResponse:
    def __init__(self, payload=None, status_code: int = 200) -> None:
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.request = httpx.Request("POST", "http://test")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        return self._payload


def async_client_factory(*, get_response=None, post_response=None, post_exc=None):
    class FakeAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, *_args, **_kwargs):
            return get_response

        async def post(self, *_args, **_kwargs):
            if post_exc:
                raise post_exc
            return post_response

    return FakeAsyncClient


@pytest.mark.anyio
async def test_readiness_reports_missing_embedding_model(monkeypatch) -> None:
    monkeypatch.setattr(
        embedding_module.httpx,
        "AsyncClient",
        async_client_factory(get_response=FakeResponse({"models": []})),
    )

    status = await EmbeddingService().readiness()

    assert status["status"] == "unavailable"
    assert status["category"] == "embedding_model_missing"


@pytest.mark.anyio
async def test_readiness_reports_unsupported_embedding_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        embedding_module.httpx,
        "AsyncClient",
        async_client_factory(
            get_response=FakeResponse({"models": [{"name": "embeddinggemma"}]}),
            post_response=FakeResponse(status_code=404),
        ),
    )

    status = await EmbeddingService().readiness()

    assert status["status"] == "unavailable"
    assert status["category"] == "embedding_endpoint_unsupported"


@pytest.mark.anyio
async def test_embed_raises_timeout_category(monkeypatch) -> None:
    monkeypatch.setattr(
        embedding_module.httpx,
        "AsyncClient",
        async_client_factory(post_exc=httpx.TimeoutException("timeout")),
    )

    with pytest.raises(EmbeddingTimeoutError) as exc:
        await EmbeddingService().embed(["test"])

    assert exc.value.category == "embedding_timeout"


@pytest.mark.anyio
async def test_embed_raises_missing_model_for_404(monkeypatch) -> None:
    monkeypatch.setattr(
        embedding_module.httpx,
        "AsyncClient",
        async_client_factory(post_response=FakeResponse(status_code=404)),
    )

    with pytest.raises(EmbeddingModelMissingError):
        await EmbeddingService().embed(["test"])


@pytest.mark.anyio
async def test_embed_raises_malformed_response(monkeypatch) -> None:
    monkeypatch.setattr(
        embedding_module.httpx,
        "AsyncClient",
        async_client_factory(post_response=FakeResponse({"embeddings": []})),
    )

    with pytest.raises(EmbeddingMalformedResponseError):
        await EmbeddingService().embed(["test"])

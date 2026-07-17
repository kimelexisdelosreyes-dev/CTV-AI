import httpx
import pytest

from app.core.config import settings
from app.services import ollama_service as ollama_module
from app.services.ollama_service import (
    OllamaInferenceTimeoutError,
    OllamaMalformedResponseError,
    OllamaTruncatedResponseError,
    OllamaUpstreamError,
    OllamaService,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeResponse:
    headers = {"content-type": "application/json"}
    status_code = 200

    def __init__(self, payload=None, json_error: bool = False) -> None:
        self._payload = payload
        self._json_error = json_error
        self.text = "{}"

    def raise_for_status(self) -> None:
        return None

    def json(self):
        if self._json_error:
            raise ValueError("bad json")
        if self._payload is not None:
            return self._payload
        return {
            "message": {"content": "ok"},
            "eval_count": 2,
            "eval_duration": 1_000_000_000,
        }


@pytest.mark.anyio
async def test_chat_sends_configured_output_budget(monkeypatch) -> None:
    captured_payloads = []
    monkeypatch.setattr(settings, "ollama_num_predict", 123)

    class FakeAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, _path, json):
            captured_payloads.append(json)
            return FakeResponse()

    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", FakeAsyncClient)

    answer, metadata = await OllamaService().chat(
        [{"role": "user", "content": "hello"}],
        return_metadata=True,
    )

    assert answer == "ok"
    assert metadata["eval_count"] == 2
    assert captured_payloads[0]["options"] == {"num_predict": 123}
    assert captured_payloads[0]["think"] is False


@pytest.mark.anyio
async def test_chat_timeout_has_controlled_category(monkeypatch) -> None:
    class FakeAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(OllamaInferenceTimeoutError) as exc:
        await OllamaService().chat([{"role": "user", "content": "hello"}])

    assert exc.value.category == "model_inference_timeout"
    assert exc.value.status_code == 504


@pytest.mark.anyio
async def test_chat_rejects_empty_content_with_thinking_as_truncated(monkeypatch) -> None:
    class FakeAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse(
                {
                    "message": {"content": "", "thinking": "hidden reasoning"},
                    "done": True,
                    "done_reason": "stop",
                    "eval_count": 10,
                }
            )

    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(OllamaTruncatedResponseError) as exc:
        await OllamaService().chat([{"role": "user", "content": "hello"}])

    assert exc.value.category == "model_inference_truncated"
    assert exc.value.diagnostics["message_thinking_chars"] == 16
    assert "hidden reasoning" not in str(exc.value.diagnostics)


@pytest.mark.anyio
async def test_chat_rejects_missing_message_as_malformed(monkeypatch) -> None:
    class FakeAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse({"done": True})

    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(OllamaMalformedResponseError):
        await OllamaService().chat([{"role": "user", "content": "hello"}])


@pytest.mark.anyio
async def test_chat_rejects_malformed_json(monkeypatch) -> None:
    class FakeAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse(json_error=True)

    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(OllamaMalformedResponseError) as exc:
        await OllamaService().chat([{"role": "user", "content": "hello"}])

    assert exc.value.diagnostics["json_ok"] is False


@pytest.mark.anyio
async def test_chat_rejects_upstream_error_payload(monkeypatch) -> None:
    class FakeAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse({"error": "upstream failed", "done": True})

    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(OllamaUpstreamError) as exc:
        await OllamaService().chat([{"role": "user", "content": "hello"}])

    assert exc.value.category == "model_inference_upstream_error"


@pytest.mark.anyio
async def test_chat_rejects_done_false(monkeypatch) -> None:
    class FakeAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse({"message": {"content": "partial"}, "done": False})

    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(OllamaMalformedResponseError):
        await OllamaService().chat([{"role": "user", "content": "hello"}])


@pytest.mark.anyio
async def test_chat_rejects_done_reason_length(monkeypatch) -> None:
    class FakeAsyncClient:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse(
                {
                    "message": {"content": "partial"},
                    "done": True,
                    "done_reason": "length",
                }
            )

    monkeypatch.setattr(ollama_module.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(OllamaTruncatedResponseError):
        await OllamaService().chat([{"role": "user", "content": "hello"}])

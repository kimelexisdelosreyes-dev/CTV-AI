import importlib.util
import sys
from pathlib import Path

import pytest

from app.core.config import Settings


def load_warmup_module():
    script_path = None
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "scripts" / "warm_ollama_models.py"
        if candidate.exists():
            script_path = candidate
            break
    assert script_path is not None
    spec = importlib.util.spec_from_file_location("warm_ollama_models", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload=None) -> None:
        self.payload = payload or {}

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self) -> None:
        self.models: list[str] = []
        self.payloads: list[dict[str, object]] = []

    async def get(self, path):
        assert path == "/api/tags"
        return FakeResponse(
            {
                "models": [
                    {"name": "qwen3:8b"},
                    {"name": "deepseek-r1:14b"},
                ]
            }
        )

    async def post(self, path, json):
        assert path == "/api/chat"
        self.models.append(json["model"])
        self.payloads.append(json)
        return FakeResponse()


def config() -> Settings:
    return Settings(
        _env_file=None,
        ollama_model="qwen3:14b",
        ctv_one_model_fast="qwen3:8b",
        ctv_one_model_knowledge="qwen3:8b",
        ctv_one_model_operations="qwen3:8b",
        ctv_one_model_balanced="qwen3:8b",
        ctv_one_model_reasoning="deepseek-r1:14b",
        ctv_one_model_default="qwen3:8b",
    )


def test_configured_models_are_deduplicated_with_default_last() -> None:
    warmup = load_warmup_module()

    assert warmup.configured_models(config()) == [
        "deepseek-r1:14b",
        "qwen3:8b",
    ]


@pytest.mark.anyio
async def test_warmup_uses_tiny_safe_prompt_and_keep_alive() -> None:
    warmup = load_warmup_module()
    client = FakeClient()

    results = await warmup.warm_configured_models(
        config(),
        client,
        keep_alive="5m",
    )

    assert client.models == ["deepseek-r1:14b", "qwen3:8b"]
    assert [result.status for result in results] == ["warmed", "warmed"]
    assert all(payload["keep_alive"] == "5m" for payload in client.payloads)
    assert all(payload["options"] == {"num_predict": 2} for payload in client.payloads)
    assert "CTV_ONE_BEARER_TOKEN" not in str(client.payloads)

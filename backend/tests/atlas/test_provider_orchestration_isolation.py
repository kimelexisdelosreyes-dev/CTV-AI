import inspect

from app.atlas.compiler.compiler import AtlasContextCompiler
from app.atlas.runtime_manager import AtlasRuntimeManager
import app.atlas.provider_orchestration as module


def test_compiler_and_compile_context_remain_provider_blind():
    assert ".collect(" not in inspect.getsource(AtlasContextCompiler)
    assert ".collect(" not in inspect.getsource(AtlasRuntimeManager.compile_context)


def test_orchestrator_has_no_production_service_dependencies():
    source = inspect.getsource(module)
    for prohibited in ("app.supervisor", "app.agents", "app.db", "ollama", "inference_queue", "fastapi"):
        assert prohibited not in source

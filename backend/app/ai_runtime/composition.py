"""Production composition boundary for the feature-gated local runtime."""
from app.ai_runtime.adapters.ollama.adapter import OllamaModelAdapter
from app.ai_runtime.adapters.ollama.transport import ExistingOllamaServiceTransport
from app.ai_runtime.registry import AIModelAdapterRegistry
from app.ai_runtime.runtime import AIModelRuntime


def build_local_ollama_runtime(ollama_service) -> AIModelRuntime:
    """Construct local objects only; no network, health, or model inventory call occurs here."""
    registry = AIModelAdapterRegistry()
    registry.register(OllamaModelAdapter(ExistingOllamaServiceTransport(ollama_service)))
    return AIModelRuntime(registry)

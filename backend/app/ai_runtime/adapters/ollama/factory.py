from app.services.ollama_service import ollama_service
from .adapter import OllamaModelAdapter
from .transport import ExistingOllamaServiceTransport
def create_ollama_adapter()->OllamaModelAdapter:return OllamaModelAdapter(ExistingOllamaServiceTransport(ollama_service))

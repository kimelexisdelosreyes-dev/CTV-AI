from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class ModelProfile:
    key: str
    ollama_model: str
    capabilities: tuple[str, ...]
    description: str


def get_model_registry() -> dict[str, ModelProfile]:
    return {
        "general": ModelProfile(
            key="general",
            ollama_model=settings.ollama_general_model,
            capabilities=("general", "reasoning", "writing"),
            description="General reasoning and business assistance",
        ),
        "production": ModelProfile(
            key="production",
            ollama_model=settings.ollama_production_model,
            capabilities=("production", "documentary", "editing", "cinematography"),
            description="Production, documentary, editing, and cinematography",
        ),
        "graphics": ModelProfile(
            key="graphics",
            ollama_model=settings.ollama_graphics_model,
            capabilities=("graphics", "branding", "firefly", "design"),
            description="Graphics, branding, and creative prompt development",
        ),
        "drone": ModelProfile(
            key="drone",
            ollama_model=settings.ollama_drone_model,
            capabilities=("drone", "flight", "cinematography", "maintenance"),
            description="Drone operations and aerial cinematography",
        ),
        "it": ModelProfile(
            key="it",
            ollama_model=settings.ollama_it_model,
            capabilities=("it", "network", "nas", "docker", "windows"),
            description="IT support, networking, storage, and local AI",
        ),
        "coder": ModelProfile(
            key="coder",
            ollama_model=settings.ollama_coder_model,
            capabilities=("code", "python", "powershell", "api"),
            description="Programming, scripting, and software development",
        ),
        "light": ModelProfile(
            key="light",
            ollama_model=settings.ollama_light_model,
            capabilities=("simple", "classification", "short-form"),
            description="Lightweight routing and simple tasks",
        ),
        "comedy": ModelProfile(
            key="comedy",
            ollama_model=settings.ollama_comedy_model,
            capabilities=("humor", "roast", "burnout", "banter", "taglish"),
            description="Opt-in workplace humor and burnout breaks",
        ),
    }


MODEL_REGISTRY = get_model_registry()

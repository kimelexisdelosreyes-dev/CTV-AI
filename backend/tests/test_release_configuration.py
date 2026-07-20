import tomllib
from pathlib import Path

from app.core.config import Settings, settings
from app.core.model_registry import get_model_registry
from app.core.version import APP_VERSION
from app.main import app


def test_application_version_has_one_runtime_source() -> None:
    assert settings.app_version == APP_VERSION
    assert app.version == APP_VERSION


def test_packaging_version_is_dynamic_from_runtime_source() -> None:
    backend = Path(__file__).resolve().parents[1]
    project = tomllib.loads((backend / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dynamic"] == ["version"]
    assert "version" not in project["project"]
    assert project["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "app.core.version.APP_VERSION"
    }


def test_model_registry_reads_current_settings(monkeypatch) -> None:
    configured = {
        "general": "general:test",
        "production": "production:test",
        "graphics": "graphics:test",
        "drone": "drone:test",
        "it": "it:test",
        "coder": "coder:test",
        "light": "light:test",
        "comedy": "comedy:test",
    }
    for role, model in configured.items():
        monkeypatch.setattr(settings, f"ollama_{role}_model", model)

    registry = get_model_registry()

    assert {
        role: profile.ollama_model for role, profile in registry.items()
    } == configured


def test_unit_test_settings_cannot_target_live_services() -> None:
    assert "127.0.0.1:1" in settings.database_url
    assert settings.ollama_base_url == "http://127.0.0.1:1"
    assert settings.qdrant_url == "http://127.0.0.1:1"
    assert settings.ctv_one_monday_snapshot_refresh_enabled is False
    assert settings.ctv_one_inference_queue_enabled is False


def test_production_queue_defaults_are_single_gpu_safe() -> None:
    defaults = Settings.model_fields
    assert defaults["ctv_one_inference_queue_enabled"].default is True
    assert defaults["ctv_one_inference_global_concurrency"].default == 2
    assert defaults["ctv_one_inference_global_queue_size"].default == 20
    assert defaults["ctv_one_inference_model_qwen3_8b_concurrency"].default == 2
    assert (
        defaults["ctv_one_inference_model_deepseek_r1_14b_concurrency"].default
        == 1
    )
    assert defaults["ctv_one_inference_per_user_active_limit"].default == 1
    assert defaults["ctv_one_inference_per_user_queue_limit"].default == 3

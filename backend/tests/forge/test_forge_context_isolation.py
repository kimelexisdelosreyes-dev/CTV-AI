from pathlib import Path

from app.forge.context_adapter import ForgeContextAdapter


ROOT = Path(__file__).resolve().parents[2] / "app"


def test_forge_does_not_mutate_atlas_package(atlas_package) -> None:
    before = atlas_package.deterministic_json()
    ForgeContextAdapter(token_budget=1000, atlas_enabled=True, adapter_enabled=True).adapt(atlas_package)
    assert atlas_package.deterministic_json() == before


def test_dependency_direction_and_runtime_isolation() -> None:
    atlas_sources = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "atlas").rglob("*.py"))
    forge_source = (ROOT / "forge" / "context_adapter.py").read_text(encoding="utf-8").lower()
    assert "app.forge" not in atlas_sources
    for forbidden in ("contextcompiler", "providerorchestrator", ".collect(", "nexus", "database", "inference"):
        assert forbidden not in forge_source

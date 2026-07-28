import ast
from pathlib import Path


def test_compiler_has_no_runtime_or_production_dependencies():
    root = Path(__file__).resolve().parents[2] / "app" / "atlas" / "compiler"
    forbidden = ("app.main", "app.supervisor", "app.agents", "app.services", "app.api", "app.db", "fastapi", "sqlalchemy", "ollama", "registry", "runtime_manager")
    imports = []
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module: imports.append(node.module)
    assert not [item for item in imports if any(term in item for term in forbidden)]

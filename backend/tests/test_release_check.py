import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from alembic.config import Config
from alembic.script import ScriptDirectory


def load_release_check():
    script = Path(__file__).resolve().parents[2] / "scripts" / "release_check.py"
    spec = importlib.util.spec_from_file_location("release_check", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_release_check_success_path_with_mocked_subprocess() -> None:
    release_check = load_release_check()

    def successful(command, **_kwargs):
        stdout = "0011 (head)\n" if command[-1] == "heads" else ""
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    result = release_check.run_release_check(
        runner=successful,
        which=lambda _tool: None,
        python="python",
    )
    assert result == 0


def test_release_check_propagates_required_step_failure() -> None:
    release_check = load_release_check()

    def failing_tests(command, **_kwargs):
        failed = "pytest" in command
        stdout = "0011 (head)\n" if command[-1] == "heads" else ""
        return SimpleNamespace(
            returncode=1 if failed else 0,
            stdout=stdout,
            stderr="simulated" if failed else "",
        )

    result = release_check.run_release_check(
        runner=failing_tests,
        which=lambda _tool: None,
        python="python",
    )
    assert result == 1


def test_release_check_converts_launch_error_to_failure() -> None:
    release_check = load_release_check()

    def unavailable(_command, **_kwargs):
        raise OSError("simulated")

    result = release_check.run_release_check(
        runner=unavailable,
        which=lambda _tool: None,
        python="python",
    )
    assert result == 1


def test_alembic_has_exactly_one_source_head() -> None:
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1


def test_generated_benchmark_reports_are_gitignored() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "check-ignore", "benchmarks/reports/generated-release-check.json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0

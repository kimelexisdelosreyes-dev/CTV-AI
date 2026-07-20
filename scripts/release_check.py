from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_ROOT = REPO_ROOT / "frontend" / "enterprise-ui"
Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class CheckStep:
    name: str
    command: tuple[str, ...]
    cwd: Path
    capture_output: bool = False


def _run_step(step: CheckStep, runner: Runner) -> subprocess.CompletedProcess[str]:
    print(f"\n==> {step.name}")
    try:
        result = runner(
            list(step.command),
            cwd=str(step.cwd),
            text=True,
            capture_output=step.capture_output,
            check=False,
        )
    except OSError as exc:
        result = subprocess.CompletedProcess(
            list(step.command),
            returncode=127,
            stdout="",
            stderr=f"Could not launch command: {type(exc).__name__}",
        )
    if result.returncode == 0:
        print("PASS")
    else:
        print(f"FAIL (exit {result.returncode})")
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
    return result


def _required_steps(python: str) -> list[CheckStep]:
    return [
        CheckStep(
            "Backend full test suite",
            (python, "-m", "pytest", "tests", "-q"),
            BACKEND_ROOT,
        ),
        CheckStep(
            "Backend compileall",
            (python, "-m", "compileall", "-q", "app", "tests", "../scripts"),
            BACKEND_ROOT,
        ),
        CheckStep(
            "Git whitespace validation",
            ("git", "diff", "--check"),
            REPO_ROOT,
        ),
    ]


def _migration_steps(python: str) -> list[CheckStep]:
    return [
        CheckStep(
            "Alembic source heads",
            (python, "-m", "alembic", "-c", "alembic.ini", "heads"),
            BACKEND_ROOT,
            capture_output=True,
        ),
        CheckStep(
            "Alembic offline upgrade SQL",
            (
                python,
                "-m",
                "alembic",
                "-c",
                "alembic.ini",
                "upgrade",
                "head",
                "--sql",
            ),
            BACKEND_ROOT,
            capture_output=True,
        ),
    ]


def _one_head(output: str) -> bool:
    heads = [line.strip() for line in output.splitlines() if line.strip()]
    return len(heads) == 1 and "(head)" in heads[0]


def run_release_check(
    *,
    runner: Runner = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
    python: str = sys.executable,
) -> int:
    failures: list[str] = []
    for step in _required_steps(python):
        if _run_step(step, runner).returncode:
            failures.append(step.name)

    migration_steps = _migration_steps(python)
    heads_result = _run_step(migration_steps[0], runner)
    if heads_result.returncode:
        failures.append(migration_steps[0].name)
    elif not _one_head(heads_result.stdout or ""):
        print("FAIL (expected exactly one Alembic head)")
        failures.append("Alembic single-head validation")
    else:
        print(f"Verified one migration head: {(heads_result.stdout or '').strip()}")
    if _run_step(migration_steps[1], runner).returncode:
        failures.append(migration_steps[1].name)

    npm = which("npm.cmd") if os.name == "nt" else which("npm")
    frontend_package = FRONTEND_ROOT.joinpath("package.json")
    frontend_dependencies = FRONTEND_ROOT.joinpath("node_modules")
    if frontend_package.exists() and frontend_dependencies.exists() and npm:
        frontend_steps = [
            CheckStep(
                "Frontend typecheck",
                (npm, "exec", "tsc", "--", "--noEmit"),
                FRONTEND_ROOT,
            ),
            CheckStep(
                "Frontend production build",
                (npm, "run", "build"),
                FRONTEND_ROOT,
            ),
        ]
        for step in frontend_steps:
            if _run_step(step, runner).returncode:
                failures.append(step.name)
    elif frontend_package.exists() and not npm:
        print("\nSKIP Frontend checks: npm is not installed.")
    elif frontend_package.exists():
        print("\nSKIP Frontend checks: run npm ci to install dependencies.")
    else:
        print("\nSKIP Frontend checks: frontend package is absent.")

    if importlib.util.find_spec("ruff") is not None:
        lint_step = CheckStep(
            "Optional backend lint",
            (python, "-m", "ruff", "check", "app", "tests"),
            BACKEND_ROOT,
        )
        if _run_step(lint_step, runner).returncode:
            failures.append(lint_step.name)
    else:
        print("\nSKIP Optional backend lint: ruff is not installed.")

    if failures:
        print("\nRelease check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("\nRelease check passed.")
    return 0


def main(_argv: Sequence[str] | None = None) -> int:
    return run_release_check()


if __name__ == "__main__":
    raise SystemExit(main())

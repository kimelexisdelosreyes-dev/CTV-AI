from __future__ import annotations

from datetime import datetime, timezone
import inspect

import pytest
from pydantic import ValidationError

from app.atlas.compiler import AtlasContextCompiler
from app.atlas.compiler_contracts import (
    AtlasCompilationSnapshot,
    AtlasCompilerPolicy,
    AtlasContextRequest,
    AtlasProvenance,
    AtlasProviderInputSnapshot,
    AtlasProviderSelectionEntry,
    AtlasProviderSelectionPlan,
    AtlasSelectionAction,
)
from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError


NOW = datetime(2026, 2, 3, 4, 5, 6, tzinfo=timezone.utc)


def _input(
    provider_id: str,
    *,
    sequence: int = 0,
    status: str = "success",
) -> AtlasProviderInputSnapshot:
    return AtlasProviderInputSnapshot(
        provider_id=provider_id,
        provider_version="1.0",
        provider_contract_version="1.0",
        result_schema_version="1.0",
        status=status,
        source_sequence=sequence,
        collected_at=NOW,
        records=({"id": f"record-{provider_id}", "content": provider_id},),
        provenance=AtlasProvenance(
            provider_id=provider_id,
            source_id=f"source-{provider_id}-{sequence}",
            source_type="fixture",
            source_sequence=sequence,
            collected_at=NOW,
            original_reference=f"reference-{provider_id}-{sequence}",
            content_digest="d" * 64,
        ),
    )


def _entry(
    provider_id: str,
    *,
    selected: bool = True,
    required: bool = False,
    ordinal: int = 0,
) -> AtlasProviderSelectionEntry:
    return AtlasProviderSelectionEntry(
        provider_id=provider_id,
        selected=selected,
        required=required,
        ordinal=ordinal,
    )


def _snapshot(
    entries: tuple[AtlasProviderSelectionEntry, ...],
    inputs: tuple[AtlasProviderInputSnapshot, ...],
    *,
    policy: AtlasCompilerPolicy | None = None,
) -> AtlasCompilationSnapshot:
    return AtlasCompilationSnapshot(
        request=AtlasContextRequest(request_id="request-selection", intent="summary"),
        compiler_policy=policy or AtlasCompilerPolicy(),
        provider_selection_plan=AtlasProviderSelectionPlan(entries=entries),
        provider_inputs=inputs,
        compilation_time=NOW,
        source_configuration_fingerprint="e" * 64,
    )


def test_select_includes_selected_available_provider() -> None:
    alpha = _input("alpha_provider")
    selected, decisions, warnings = AtlasContextCompiler()._select(
        _snapshot((_entry("alpha_provider"),), (alpha,))
    )

    assert selected == (alpha,)
    assert decisions[0].action == AtlasSelectionAction.SELECTED
    assert decisions[0].reason_categories == ("provider_selected",)
    assert warnings == ()


def test_select_excludes_plan_excluded_provider_even_when_supplied() -> None:
    alpha = _input("alpha_provider")
    selected, decisions, warnings = AtlasContextCompiler()._select(
        _snapshot((_entry("alpha_provider", selected=False),), (alpha,))
    )

    assert selected == ()
    assert decisions[0].action == AtlasSelectionAction.EXCLUDED
    assert decisions[0].provider_id == "alpha_provider"
    assert warnings == ()


def test_select_warns_when_a_selected_optional_provider_is_missing() -> None:
    snapshot = _snapshot((_entry("optional_provider"),), ())

    first = AtlasContextCompiler()._select(snapshot)
    second = AtlasContextCompiler()._select(snapshot)

    assert first == second
    assert first[0] == ()
    assert first[1][0].reason_categories == ("provider_missing",)
    assert first[2] == ("provider_missing",)


def test_required_missing_provider_fails_before_selection() -> None:
    snapshot = _snapshot(
        (_entry("required_provider", required=True),),
        (),
    )

    with pytest.raises(AtlasRuntimeError) as raised:
        AtlasContextCompiler()._validate(snapshot)

    assert raised.value.category == AtlasErrorCategory.COMPILATION_SNAPSHOT_INVALID


def test_required_unavailable_provider_obeys_fail_policy() -> None:
    snapshot = _snapshot(
        (_entry("required_provider", required=True),),
        (_input("required_provider", status="unavailable"),),
    )

    with pytest.raises(AtlasRuntimeError) as raised:
        AtlasContextCompiler()._validate(snapshot)

    assert raised.value.category == AtlasErrorCategory.PROVIDER_INPUT_INVALID


def test_select_returns_canonical_selected_provider_order() -> None:
    zeta = _input("zeta_provider")
    alpha = _input("alpha_provider")
    snapshot = _snapshot(
        (_entry("zeta_provider", ordinal=1), _entry("alpha_provider")),
        (zeta, alpha),
    )

    selected, decisions, _ = AtlasContextCompiler()._select(snapshot)

    assert tuple(item.provider_id for item in selected) == (
        "alpha_provider",
        "zeta_provider",
    )
    assert tuple(item.provider_id for item in decisions) == (
        "alpha_provider",
        "zeta_provider",
    )


def test_select_returns_canonical_excluded_provider_order() -> None:
    inputs = (
        _input("zeta_provider"),
        _input("beta_provider"),
        _input("alpha_provider"),
    )
    snapshot = _snapshot(
        (
            _entry("zeta_provider", selected=False, ordinal=2),
            _entry("beta_provider", selected=False, ordinal=1),
            _entry("alpha_provider"),
        ),
        inputs,
    )

    _, decisions, _ = AtlasContextCompiler()._select(snapshot)
    excluded = tuple(
        item.provider_id
        for item in decisions
        if item.action == AtlasSelectionAction.EXCLUDED
    )

    assert excluded == ("beta_provider", "zeta_provider")


def test_selection_plan_contract_rejects_duplicate_entries() -> None:
    with pytest.raises(ValidationError, match="unique and ordered"):
        AtlasProviderSelectionPlan(
            entries=(
                _entry("alpha_provider", ordinal=0),
                _entry("alpha_provider", ordinal=1),
            )
        )


def test_select_ignores_supplied_unplanned_provider() -> None:
    alpha = _input("alpha_provider")
    unplanned = _input("unplanned_provider")

    selected, decisions, warnings = AtlasContextCompiler()._select(
        _snapshot((_entry("alpha_provider"),), (unplanned, alpha))
    )

    assert tuple(item.provider_id for item in selected) == ("alpha_provider",)
    assert all(item.provider_id != "unplanned_provider" for item in decisions)
    assert warnings == ()


def test_selection_is_provider_input_permutation_invariant() -> None:
    entries = (
        _entry("alpha_provider"),
        _entry("zeta_provider", ordinal=1),
    )
    alpha = _input("alpha_provider")
    zeta = _input("zeta_provider")
    compiler = AtlasContextCompiler()

    first = compiler._select(_snapshot(entries, (alpha, zeta)))
    second = compiler._select(_snapshot(entries, (zeta, alpha)))

    assert first == second
    assert tuple(item.canonical_bytes() for item in first[0]) == tuple(
        item.canonical_bytes() for item in second[0]
    )


def test_selection_stage_has_no_runtime_or_provider_method_dependency() -> None:
    source = inspect.getsource(AtlasContextCompiler._select)

    for forbidden in (
        "registry",
        "runtime_manager",
        ".collect(",
        "health_check",
        "readiness_check",
    ):
        assert forbidden not in source

    compiler = AtlasContextCompiler()
    assert not hasattr(compiler, "registry")
    assert not hasattr(compiler, "runtime_manager")

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

import app.atlas.compiler.compiler as compiler_module
from app.atlas.compiler import AtlasContextCompiler
from app.atlas.compiler_contracts import (
    AtlasCompilationSnapshot,
    AtlasCompilerPolicy,
    AtlasContextRequest,
    AtlasProvenance,
    AtlasProviderInputSnapshot,
    AtlasProviderSelectionEntry,
    AtlasProviderSelectionPlan,
)
from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError


NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _provider_input(
    provider_id: str = "alpha_provider",
    *,
    source_sequence: int = 0,
    status: str = "success",
) -> AtlasProviderInputSnapshot:
    provenance = AtlasProvenance(
        provider_id=provider_id,
        source_id=f"source-{provider_id}-{source_sequence}",
        source_type="fixture",
        source_sequence=source_sequence,
        collected_at=NOW,
        original_reference=f"reference-{provider_id}-{source_sequence}",
        content_digest=("a" if provider_id == "alpha_provider" else "b") * 64,
    )
    return AtlasProviderInputSnapshot(
        provider_id=provider_id,
        provider_version="1.0",
        provider_contract_version="1.0",
        result_schema_version="1.0",
        status=status,
        source_sequence=source_sequence,
        collected_at=NOW,
        records=({"id": "record-1", "content": "fixture"},),
        provenance=provenance,
    )


def _snapshot(
    *,
    entries: tuple[AtlasProviderSelectionEntry, ...] | None = None,
    inputs: tuple[AtlasProviderInputSnapshot, ...] | None = None,
    policy: AtlasCompilerPolicy | None = None,
) -> AtlasCompilationSnapshot:
    source = _provider_input()
    return AtlasCompilationSnapshot(
        request=AtlasContextRequest(request_id="request-validation", intent="summary"),
        compiler_policy=policy or AtlasCompilerPolicy(),
        provider_selection_plan=AtlasProviderSelectionPlan(
            entries=entries
            if entries is not None
            else (
                AtlasProviderSelectionEntry(
                    provider_id="alpha_provider", selected=True, ordinal=0
                ),
            )
        ),
        provider_inputs=inputs if inputs is not None else (source,),
        compilation_time=NOW,
        source_configuration_fingerprint="c" * 64,
    )


class _TamperedFingerprintSnapshot(AtlasCompilationSnapshot):
    @property
    def snapshot_fingerprint(self) -> str:
        return "0" * 64


def _tampered(snapshot: AtlasCompilationSnapshot) -> _TamperedFingerprintSnapshot:
    return _TamperedFingerprintSnapshot.model_construct(**snapshot.__dict__)


def test_validate_accepts_a_valid_snapshot_directly() -> None:
    snapshot = _snapshot()

    assert AtlasContextCompiler()._validate(snapshot) is None


def test_validate_rejects_a_tampered_snapshot_fingerprint_safely() -> None:
    snapshot = _tampered(_snapshot())

    with pytest.raises(AtlasRuntimeError) as raised:
        AtlasContextCompiler()._validate(snapshot)

    assert raised.value.category == AtlasErrorCategory.COMPILATION_SNAPSHOT_INVALID
    assert str(raised.value) == "The Atlas compilation snapshot is invalid."
    assert "fingerprint" not in str(raised.value).lower()


def test_validate_rejects_an_incompatible_compiler_major_version() -> None:
    snapshot = _snapshot().model_copy(update={"contract_version": "2.0"})

    with pytest.raises(AtlasRuntimeError) as raised:
        AtlasContextCompiler()._validate(snapshot)

    assert raised.value.category == AtlasErrorCategory.COMPILER_CONTRACT_MISMATCH


def test_snapshot_contract_rejects_duplicate_provider_inputs_before_validation() -> None:
    source = _provider_input()

    with pytest.raises(ValidationError, match="uniquely and canonically ordered"):
        _snapshot(inputs=(source, source))


def test_validate_rejects_a_missing_selected_required_provider() -> None:
    entry = AtlasProviderSelectionEntry(
        provider_id="required_provider",
        selected=True,
        required=True,
        ordinal=0,
    )

    with pytest.raises(AtlasRuntimeError) as raised:
        AtlasContextCompiler()._validate(_snapshot(entries=(entry,), inputs=()))

    assert raised.value.category == AtlasErrorCategory.COMPILATION_SNAPSHOT_INVALID


def test_validate_accepts_a_missing_optional_provider_deterministically() -> None:
    entry = AtlasProviderSelectionEntry(
        provider_id="optional_provider",
        selected=True,
        required=False,
        ordinal=0,
    )
    snapshot = _snapshot(entries=(entry,), inputs=())
    compiler = AtlasContextCompiler()

    assert compiler._validate(snapshot) is None
    assert compiler._validate(snapshot) is None


def test_required_unavailable_provider_uses_warn_policy_without_failure() -> None:
    unavailable = _provider_input("required_provider", status="unavailable")
    entry = AtlasProviderSelectionEntry(
        provider_id="required_provider",
        selected=True,
        required=True,
        ordinal=0,
    )
    snapshot = _snapshot(
        entries=(entry,),
        inputs=(unavailable,),
        policy=AtlasCompilerPolicy(missing_required_provider_policy="warn"),
    )
    compiler = AtlasContextCompiler()

    assert compiler._validate(snapshot) is None
    selected, decisions, warnings = compiler._select(snapshot)
    assert selected == ()
    assert len(decisions) == 1
    assert warnings


def test_required_unavailable_provider_fails_with_safe_category_under_fail_policy() -> None:
    unavailable = _provider_input("required_provider", status="unavailable")
    entry = AtlasProviderSelectionEntry(
        provider_id="required_provider",
        selected=True,
        required=True,
        ordinal=0,
    )

    with pytest.raises(AtlasRuntimeError) as raised:
        AtlasContextCompiler()._validate(
            _snapshot(entries=(entry,), inputs=(unavailable,))
        )

    assert raised.value.category == AtlasErrorCategory.PROVIDER_INPUT_INVALID
    assert "unavailable" not in str(raised.value).lower()


def test_validate_uses_the_supplied_timestamp_and_never_reads_wall_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _WallClockTrap:
        @classmethod
        def now(cls, *_args, **_kwargs):
            raise AssertionError("wall clock must not be read")

    snapshot = _snapshot()
    monkeypatch.setattr(compiler_module, "datetime", _WallClockTrap)

    AtlasContextCompiler()._validate(snapshot)
    assert snapshot.compilation_time == NOW


def test_validation_error_precedence_is_deterministic() -> None:
    snapshot = _tampered(_snapshot()).model_copy(update={"contract_version": "2.0"})
    compiler = AtlasContextCompiler()

    categories = []
    for _ in range(3):
        with pytest.raises(AtlasRuntimeError) as raised:
            compiler._validate(snapshot)
        categories.append(raised.value.category)

    assert categories == [AtlasErrorCategory.COMPILER_CONTRACT_MISMATCH] * 3


def test_validate_does_not_mutate_the_snapshot() -> None:
    snapshot = _snapshot()
    before = snapshot.canonical_bytes()

    AtlasContextCompiler()._validate(snapshot)

    assert snapshot.canonical_bytes() == before
    assert snapshot.snapshot_fingerprint == snapshot.deterministic_fingerprint()

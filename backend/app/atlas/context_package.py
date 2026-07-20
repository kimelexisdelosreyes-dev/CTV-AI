from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, field_validator, model_validator

from app.atlas.constants import (
    ATLAS_CONTEXT_PACKAGE_VERSION,
    ATLAS_MAX_CONTEXT_METADATA_ITEMS,
    ATLAS_MAX_CONTEXT_METADATA_VALUE_CHARS,
    ATLAS_MAX_CONTEXT_PACKAGE_BYTES,
    ATLAS_MAX_PROVIDER_RESULT_BYTES,
)
from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError
from app.atlas.metrics import atlas_runtime_metrics
from app.atlas.models import (
    CONTRACT_VERSION_PATTERN,
    STABLE_REFERENCE_PATTERN,
    AtlasProviderResult,
    utc_now,
    validate_safe_json_keys,
)


class AtlasContextNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    node_type: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=256)
    attributes: dict[str, JsonValue] = Field(default_factory=dict, max_length=24)

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        validate_safe_json_keys(value)
        return value


class AtlasContextRelationship(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    relationship_type: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    source_node_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    target_node_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    attributes: dict[str, JsonValue] = Field(default_factory=dict, max_length=16)

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        validate_safe_json_keys(value)
        return value


class AtlasEvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    excerpt: str = Field(min_length=1, max_length=4_000)
    classification: str = Field(pattern=r"^(internal|confidential|restricted)$")
    citation_ids: tuple[str, ...] = Field(default=(), max_length=16)

    @field_validator("citation_ids")
    @classmethod
    def validate_citation_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not STABLE_REFERENCE_PATTERN.fullmatch(value) for value in values):
            raise ValueError("Citation identifiers must be stable references.")
        return values


class AtlasCitation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    citation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    provider_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    source_reference: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    label: str = Field(min_length=1, max_length=256)


class AtlasContextWarning(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    safe_message: str = Field(min_length=1, max_length=512)
    provider_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")


class AtlasContextBudgetUsage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_count: int = Field(default=0, ge=0, le=32)
    node_count: int = Field(default=0, ge=0, le=128)
    relationship_count: int = Field(default=0, ge=0, le=256)
    evidence_count: int = Field(default=0, ge=0, le=256)
    serialized_bytes: int = Field(default=0, ge=0, le=ATLAS_MAX_CONTEXT_PACKAGE_BYTES)


class AtlasOptimizationStats(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    applied: bool = False
    omitted_item_count: int = Field(default=0, ge=0)
    truncated_item_count: int = Field(default=0, ge=0)
    duration_ms: float = Field(default=0.0, ge=0)


class AtlasContextPackage(BaseModel):
    """Versioned, bounded future context artifact; no provider creates one in 3.1."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: str = ATLAS_CONTEXT_PACKAGE_VERSION
    request_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    created_at: datetime = Field(default_factory=utc_now)
    selected_provider_ids: tuple[str, ...] = Field(default=(), max_length=32)
    provider_results: tuple[AtlasProviderResult, ...] = Field(default=(), max_length=32)
    nodes: tuple[AtlasContextNode, ...] = Field(default=(), max_length=128)
    relationships: tuple[AtlasContextRelationship, ...] = Field(default=(), max_length=256)
    evidence: tuple[AtlasEvidenceItem, ...] = Field(default=(), max_length=256)
    citations: tuple[AtlasCitation, ...] = Field(default=(), max_length=256)
    warnings: tuple[AtlasContextWarning, ...] = Field(default=(), max_length=64)
    budgets: AtlasContextBudgetUsage = Field(default_factory=AtlasContextBudgetUsage)
    optimization: AtlasOptimizationStats = Field(default_factory=AtlasOptimizationStats)
    metrics: dict[str, float] = Field(default_factory=dict, max_length=32)
    metadata: dict[str, str] = Field(default_factory=dict, max_length=ATLAS_MAX_CONTEXT_METADATA_ITEMS)

    @field_validator("contract_version")
    @classmethod
    def validate_contract_version(cls, value: str) -> str:
        if value != ATLAS_CONTEXT_PACKAGE_VERSION or not CONTRACT_VERSION_PATTERN.fullmatch(value):
            raise ValueError("Unsupported Atlas context package contract version.")
        return value

    @field_validator("selected_provider_ids")
    @classmethod
    def validate_provider_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not STABLE_REFERENCE_PATTERN.fullmatch(value) for value in values):
            raise ValueError("Selected provider identifiers must be stable references.")
        if len(set(values)) != len(values):
            raise ValueError("Selected provider identifiers must be unique.")
        return values

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, values: dict[str, str]) -> dict[str, str]:
        prohibited = {"prompt", "reasoning", "exception", "traceback", "secret", "credential"}
        for key, value in values.items():
            if not STABLE_REFERENCE_PATTERN.fullmatch(key):
                raise ValueError("Atlas metadata keys must be stable references.")
            if any(term in key.lower() for term in prohibited):
                raise ValueError("Atlas metadata key is not permitted.")
            if len(value) > ATLAS_MAX_CONTEXT_METADATA_VALUE_CHARS:
                raise ValueError("Atlas metadata values are bounded.")
        return values

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, values: dict[str, float]) -> dict[str, float]:
        for key in values:
            if not STABLE_REFERENCE_PATTERN.fullmatch(key):
                raise ValueError("Atlas metric keys must be stable references.")
            if any(term in key.lower() for term in {"prompt", "reasoning", "exception", "traceback"}):
                raise ValueError("Atlas metric key is not permitted.")
        return values

    @model_validator(mode="after")
    def validate_package(self) -> AtlasContextPackage:
        provider_ids = {result.provider_id for result in self.provider_results}
        if not provider_ids.issubset(set(self.selected_provider_ids)):
            raise ValueError("Provider results must correspond to selected providers.")
        node_ids = {node.node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("Atlas context node identifiers must be unique.")
        if any(
            relationship.source_node_id not in node_ids
            or relationship.target_node_id not in node_ids
            for relationship in self.relationships
        ):
            raise ValueError("Atlas relationships must reference included context nodes.")
        citation_ids = {citation.citation_id for citation in self.citations}
        if any(
            citation_id not in citation_ids
            for item in self.evidence
            for citation_id in item.citation_ids
        ):
            raise ValueError("Atlas evidence must reference included citations.")
        expected_usage = {
            "provider_count": len(self.selected_provider_ids),
            "node_count": len(self.nodes),
            "relationship_count": len(self.relationships),
            "evidence_count": len(self.evidence),
        }
        if any(getattr(self.budgets, field) not in {0, expected} for field, expected in expected_usage.items()):
            raise ValueError("Atlas context package budget usage is inconsistent.")
        serialized = self.deterministic_json().encode("utf-8")
        if len(serialized) > ATLAS_MAX_CONTEXT_PACKAGE_BYTES:
            raise ValueError("Atlas context package exceeds its bounded size.")
        if any(
            len(json.dumps(result.model_dump(mode="json"), sort_keys=True).encode("utf-8"))
            > ATLAS_MAX_PROVIDER_RESULT_BYTES
            for result in self.provider_results
        ):
            raise ValueError("Atlas provider result exceeds its bounded size.")
        return self

    def deterministic_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


def create_empty_context_package(request_id: str) -> AtlasContextPackage:
    try:
        package = AtlasContextPackage(request_id=request_id)
    except ValidationError as exc:
        atlas_runtime_metrics.increment(
            "atlas_context_package_validation_failure_count",
            reason_category=AtlasErrorCategory.CONTEXT_PACKAGE_INVALID.value,
        )
        raise AtlasRuntimeError(AtlasErrorCategory.CONTEXT_PACKAGE_INVALID) from exc
    atlas_runtime_metrics.increment("atlas_context_package_created_count")
    return package


def validate_context_package(value: object) -> AtlasContextPackage:
    try:
        return AtlasContextPackage.model_validate(value)
    except ValidationError as exc:
        atlas_runtime_metrics.increment(
            "atlas_context_package_validation_failure_count",
            reason_category=AtlasErrorCategory.CONTEXT_PACKAGE_INVALID.value,
        )
        raise AtlasRuntimeError(AtlasErrorCategory.CONTEXT_PACKAGE_INVALID) from exc

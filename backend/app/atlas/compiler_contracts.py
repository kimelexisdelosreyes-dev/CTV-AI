"""Checkpoint B contracts only.  No compiler execution is implemented here."""
from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from app.atlas.canonical import AtlasCanonicalModel, FrozenJson, fingerprint
from app.atlas.constants import ATLAS_AIR_VERSION, ATLAS_COMPILER_CONTRACT_VERSION, ATLAS_MANIFEST_VERSION
from app.atlas.models import validate_safe_json_keys

StableId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")]
ProviderId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
Version = Annotated[str, Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$")]
HEX64 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class AtlasClassification(StrEnum):
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class AtlasCompilerStage(StrEnum):
    VALIDATION = "validation"; NORMALIZATION = "normalization"; GRAPH = "graph"; RANKING = "ranking"; BUDGET = "budget"; OPTIMIZATION = "optimization"; PACKAGE = "package"


class AtlasSelectionAction(StrEnum):
    SELECTED = "selected"; EXCLUDED = "excluded"; SKIPPED = "skipped"


class AtlasAIRItemType(StrEnum):
    DOCUMENT = "document"; RECORD = "record"; FACT = "fact"; ENTITY = "entity"; RELATION_CANDIDATE = "relation_candidate"


def _stable_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(values) != len(set(values)):
        raise ValueError("Atlas identifiers must be unique.")
    return tuple(sorted(values))


def _frozen(value: Any) -> FrozenJson:
    frozen = value if isinstance(value, FrozenJson) else FrozenJson(value)
    validate_safe_json_keys(frozen.to_python())
    return frozen


class AtlasAccessSnapshot(AtlasCanonicalModel):
    principal_id: StableId
    role_ids: tuple[StableId, ...] = ()
    department_ids: tuple[StableId, ...] = ()
    permission_ids: tuple[StableId, ...] = ()
    data_classification_ceiling: AtlasClassification = AtlasClassification.INTERNAL
    tenant_id: StableId | None = None

    _roles = field_validator("role_ids", "department_ids", "permission_ids")(_stable_unique)


class AtlasContextRequest(AtlasCanonicalModel):
    contract_version: Version = ATLAS_COMPILER_CONTRACT_VERSION
    request_id: StableId
    intent: Annotated[str, Field(min_length=1, max_length=128)]
    execution_mode: Literal["compile", "preview"] = "compile"
    requested_capabilities: tuple[ProviderId, ...] = ()
    provider_hints: tuple[ProviderId, ...] = ()
    required_provider_ids: tuple[ProviderId, ...] = ()
    optional_provider_ids: tuple[ProviderId, ...] = ()
    constraints: FrozenJson = Field(default_factory=FrozenJson)
    budget_profile: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")] = "default"
    metadata: FrozenJson = Field(default_factory=FrozenJson)

    _canonical_ids = field_validator("requested_capabilities", "provider_hints", "required_provider_ids", "optional_provider_ids")(_stable_unique)
    _freeze = field_validator("constraints", "metadata", mode="before")(_frozen)

    @model_validator(mode="after")
    def valid_sets(self):
        if set(self.required_provider_ids) & set(self.optional_provider_ids):
            raise ValueError("Required and optional providers must not overlap.")
        return self


class AtlasCompilerPolicy(AtlasCanonicalModel):
    contract_version: Version = ATLAS_COMPILER_CONTRACT_VERSION
    score_scale_points: int = Field(default=1000, ge=1, le=1_000_000)
    provider_priority_points: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    intent_match_points: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    confidence_points: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    freshness_points: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    relationship_bonus_points: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    duplicate_penalty_points: int = Field(default=0, ge=0, le=1_000_000)
    conflict_penalty_points: int = Field(default=0, ge=0, le=1_000_000)
    minimum_selection_score_points: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    max_total_nodes: int = Field(default=128, ge=0, le=100_000)
    max_total_relationships: int = Field(default=256, ge=0, le=100_000)
    max_total_evidence: int = Field(default=256, ge=0, le=100_000)
    max_total_citations: int = Field(default=256, ge=0, le=100_000)
    max_total_serialized_bytes: int = Field(default=131_072, ge=1, le=10_000_000)
    max_nodes_per_provider: int = Field(default=128, ge=0, le=100_000)
    max_evidence_per_provider: int = Field(default=128, ge=0, le=100_000)
    max_content_chars_per_node: int = Field(default=4000, ge=1, le=100_000)
    truncation_policy: Literal["reject", "truncate"] = "reject"
    conflict_policy: Literal["preserve", "select_ranked"] = "preserve"
    missing_required_provider_policy: Literal["fail", "warn"] = "fail"
    invalid_optional_provider_policy: Literal["exclude", "fail"] = "exclude"
    deterministic_tie_break_policy: Literal["score_provider_confidence_freshness_provider_id_item_id"] = "score_provider_confidence_freshness_provider_id_item_id"
    classification_policy_version: Version = "1.0"

    @property
    def policy_fingerprint(self) -> str:
        return self.deterministic_fingerprint()


class AtlasProviderSelectionEntry(AtlasCanonicalModel):
    provider_id: ProviderId
    selected: bool
    required: bool = False
    priority_points: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    requested_capabilities: tuple[ProviderId, ...] = ()
    matched_capabilities: tuple[ProviderId, ...] = ()
    reason_categories: tuple[ProviderId, ...] = ()
    exclusion_reason_category: ProviderId | None = None
    ordinal: int = Field(ge=0, le=1_000_000)

    _ids = field_validator("requested_capabilities", "matched_capabilities", "reason_categories")(_stable_unique)


class AtlasProviderSelectionPlan(AtlasCanonicalModel):
    entries: tuple[AtlasProviderSelectionEntry, ...] = ()

    @field_validator("entries", mode="before")
    @classmethod
    def normalize_entries(cls, value):
        entries = sorted(value, key=lambda item: item.provider_id if isinstance(item, AtlasProviderSelectionEntry) else item["provider_id"])
        return tuple(
            item.model_copy(update={"ordinal": ordinal}) if isinstance(item, AtlasProviderSelectionEntry)
            else {**item, "ordinal": ordinal}
            for ordinal, item in enumerate(entries)
        )

    @model_validator(mode="after")
    def canonical_entries(self):
        ids = [item.provider_id for item in self.entries]
        if len(ids) != len(set(ids)) or tuple(sorted(ids)) != tuple(ids):
            raise ValueError("Provider selection entries must be unique and ordered by provider ID.")
        if [item.ordinal for item in self.entries] != list(range(len(self.entries))):
            raise ValueError("Provider selection ordinals must be contiguous.")
        return self


class AtlasCompilationSnapshot(AtlasCanonicalModel):
    """All future compiler inputs, captured without global runtime state."""
    contract_version: Version = ATLAS_COMPILER_CONTRACT_VERSION
    request: AtlasContextRequest
    access_snapshot: AtlasAccessSnapshot | None = None
    compiler_policy: AtlasCompilerPolicy
    provider_selection_plan: AtlasProviderSelectionPlan
    provider_inputs: tuple["AtlasProviderInputSnapshot", ...] = ()
    compilation_time: datetime
    source_configuration_fingerprint: HEX64
    metadata: FrozenJson = Field(default_factory=FrozenJson)

    _metadata = field_validator("metadata", mode="before")(_frozen)

    @field_validator("provider_inputs", mode="before")
    @classmethod
    def normalize_inputs(cls, value):
        return tuple(sorted(value, key=lambda item: (item.provider_id, item.source_sequence) if isinstance(item, AtlasProviderInputSnapshot) else (item["provider_id"], item["source_sequence"])))

    @model_validator(mode="after")
    def ordered_inputs(self):
        keys = [(item.provider_id, item.source_sequence) for item in self.provider_inputs]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("Provider inputs must be uniquely and canonically ordered.")
        return self

    @property
    def snapshot_fingerprint(self) -> str:
        return self.deterministic_fingerprint()


class AtlasProvenance(AtlasCanonicalModel):
    provider_id: ProviderId
    source_id: StableId
    source_type: ProviderId
    source_version: Version = "1.0"
    source_sequence: int = Field(ge=0, le=1_000_000)
    collected_at: datetime
    original_reference: StableId
    parent_source_ids: tuple[StableId, ...] = ()
    transformation_steps: tuple[ProviderId, ...] = ()
    classification: AtlasClassification = AtlasClassification.INTERNAL
    content_digest: HEX64

    _parents = field_validator("parent_source_ids", "transformation_steps")(_stable_unique)

    @field_validator("original_reference")
    @classmethod
    def no_path(cls, value: str) -> str:
        if "/" in value or "\\" in value or "@" in value:
            raise ValueError("Atlas provenance references must not contain paths or credentials.")
        return value


class AtlasProviderInputSnapshot(AtlasCanonicalModel):
    provider_id: ProviderId
    provider_version: Version
    provider_contract_version: Version
    result_schema_version: Version
    status: Literal["success", "partial", "unavailable"] = "success"
    source_sequence: int = Field(ge=0, le=1_000_000)
    collected_at: datetime
    expires_at: datetime | None = None
    capabilities: tuple[ProviderId, ...] = ()
    records: tuple[FrozenJson, ...] = ()
    warnings: tuple[ProviderId, ...] = ()
    provenance: AtlasProvenance
    classification: AtlasClassification = AtlasClassification.INTERNAL
    metadata: FrozenJson = Field(default_factory=FrozenJson)

    _ids = field_validator("capabilities", "warnings")(_stable_unique)
    _records = field_validator("records", mode="before")(lambda value: tuple(_frozen(item) for item in value))
    _metadata = field_validator("metadata", mode="before")(_frozen)

    @model_validator(mode="after")
    def provider_matches(self):
        if self.provider_id != self.provenance.provider_id:
            raise ValueError("Provider input provenance must match its provider.")
        if self.expires_at and self.expires_at < self.collected_at:
            raise ValueError("Provider input expiry must not precede collection.")
        return self


class AtlasAIRRecord(AtlasCanonicalModel):
    air_id: StableId
    provider_id: ProviderId
    source_reference: StableId
    item_type: AtlasAIRItemType
    normalized_title: Annotated[str, Field(min_length=1, max_length=512)]
    normalized_content: Annotated[str, Field(max_length=16_000)] = ""
    normalized_attributes: FrozenJson = Field(default_factory=FrozenJson)
    confidence_points: int = Field(ge=0, le=1_000_000)
    freshness_at: datetime | None = None
    priority_points: int = Field(default=0, ge=-1_000_000, le=1_000_000)
    classification: AtlasClassification = AtlasClassification.INTERNAL
    capability_ids: tuple[ProviderId, ...] = ()
    provenance: AtlasProvenance
    ordinal: int = Field(ge=0, le=1_000_000)
    metadata: FrozenJson = Field(default_factory=FrozenJson)

    _freeze = field_validator("normalized_attributes", "metadata", mode="before")(_frozen)
    _capabilities = field_validator("capability_ids")(_stable_unique)

    @model_validator(mode="after")
    def traceable(self):
        if self.provider_id != self.provenance.provider_id:
            raise ValueError("AIR provenance must match the provider.")
        return self


class AtlasAIRPackage(AtlasCanonicalModel):
    contract_version: Version = ATLAS_COMPILER_CONTRACT_VERSION
    air_version: Version = ATLAS_AIR_VERSION
    records: tuple[AtlasAIRRecord, ...] = ()

    @field_validator("records", mode="before")
    @classmethod
    def normalize_records(cls, value):
        ordered = sorted(value, key=lambda item: (item.provider_id, item.ordinal, item.air_id) if isinstance(item, AtlasAIRRecord) else (item["provider_id"], item.get("ordinal", 0), item["air_id"]))
        return tuple(
            item.model_copy(update={"ordinal": ordinal}) if isinstance(item, AtlasAIRRecord)
            else {**item, "ordinal": ordinal}
            for ordinal, item in enumerate(ordered)
        )

    @model_validator(mode="after")
    def ordered(self):
        keys = [(item.provider_id, item.ordinal, item.air_id) for item in self.records]
        if keys != sorted(keys) or len({item.air_id for item in self.records}) != len(self.records):
            raise ValueError("AIR records must have unique identifiers and canonical order.")
        return self


class AtlasScoreBreakdown(AtlasCanonicalModel):
    provider_priority_points: int = 0; intent_match_points: int = 0; confidence_points: int = 0; freshness_points: int = 0; relationship_bonus_points: int = 0; duplicate_penalty_points: int = 0; conflict_penalty_points: int = 0; classification_adjustment_points: int = 0
    total_score_points: int
    score_scale_points: int = Field(default=1000, ge=1)

    @model_validator(mode="after")
    def sums(self):
        expected = self.provider_priority_points + self.intent_match_points + self.confidence_points + self.freshness_points + self.relationship_bonus_points - self.duplicate_penalty_points - self.conflict_penalty_points + self.classification_adjustment_points
        if self.total_score_points != expected:
            raise ValueError("Total score must equal its integer components.")
        return self

    @property
    def normalized_score(self) -> float:
        return self.total_score_points / self.score_scale_points


class AtlasRankedContextItem(AtlasCanonicalModel):
    item_id: StableId; provider_id: ProviderId; total_score_points: int; provider_priority_points: int; confidence_points: int
    freshness_sort_value: int = Field(default=0, ge=0); deterministic_rank: int = Field(ge=0); tie_break_values: tuple[str, ...] = ()


class AtlasContextBudget(AtlasCanonicalModel):
    max_total_nodes: int = Field(ge=0); max_nodes_per_provider: int = Field(ge=0); max_total_relationships: int = Field(ge=0); max_total_evidence: int = Field(ge=0); max_total_citations: int = Field(ge=0); max_text_characters: int = Field(ge=0); max_serialized_bytes: int = Field(ge=0); max_warnings: int = Field(ge=0); max_conflicts: int = Field(ge=0)


class AtlasBudgetUsage(AtlasCanonicalModel):
    nodes: int = Field(default=0, ge=0); relationships: int = Field(default=0, ge=0); evidence: int = Field(default=0, ge=0); citations: int = Field(default=0, ge=0); text_characters: int = Field(default=0, ge=0); serialized_bytes: int = Field(default=0, ge=0); warnings: int = Field(default=0, ge=0); conflicts: int = Field(default=0, ge=0)


class AtlasBudgetDecision(AtlasCanonicalModel):
    item_id: StableId; provider_id: ProviderId; selected: bool; budget_category: ProviderId; limit: int = Field(ge=0); usage_before: int = Field(ge=0); item_cost: int = Field(ge=0); usage_after: int = Field(ge=0); reason_category: ProviderId; deterministic_rank: int = Field(ge=0)

    @model_validator(mode="after")
    def usage(self):
        if self.usage_after != self.usage_before + self.item_cost:
            raise ValueError("Budget usage must be arithmetically consistent.")
        return self


class AtlasConflict(AtlasCanonicalModel):
    conflict_id: StableId; conflict_type: ProviderId; subject_key: StableId; item_ids: tuple[StableId, ...]; provider_ids: tuple[ProviderId, ...]; values: tuple[FrozenJson, ...] = (); classification: AtlasClassification = AtlasClassification.INTERNAL; resolution_policy: Literal["preserve", "select_ranked"] = "preserve"; selected_item_id: StableId | None = None; status: Literal["open", "resolved"] = "open"; reason_categories: tuple[ProviderId, ...] = (); provenance: tuple[AtlasProvenance, ...] = (); metadata: FrozenJson = Field(default_factory=FrozenJson)
    _ids = field_validator("item_ids", "provider_ids", "reason_categories")(_stable_unique)
    _values = field_validator("values", mode="before")(lambda value: tuple(_frozen(item) for item in value))
    _metadata = field_validator("metadata", mode="before")(_frozen)


class AtlasCompilerDecision(AtlasCanonicalModel):
    decision_id: StableId; stage: AtlasCompilerStage; subject_id: StableId; provider_id: ProviderId | None = None; action: AtlasSelectionAction; reason_categories: tuple[ProviderId, ...] = (); rule_ids: tuple[ProviderId, ...] = (); score_points: int | None = None; rank: int | None = Field(default=None, ge=0); budget_category: ProviderId | None = None; conflict_id: StableId | None = None; related_subject_ids: tuple[StableId, ...] = (); metadata: FrozenJson = Field(default_factory=FrozenJson)
    _ids = field_validator("reason_categories", "rule_ids", "related_subject_ids")(_stable_unique)
    _metadata = field_validator("metadata", mode="before")(_frozen)


class AtlasCompilerStageSummary(AtlasCanonicalModel):
    stage: AtlasCompilerStage; decision_count: int = Field(ge=0); selected_count: int = Field(ge=0); excluded_count: int = Field(ge=0)


class AtlasContextManifest(AtlasCanonicalModel):
    contract_version: Version = ATLAS_COMPILER_CONTRACT_VERSION; manifest_version: Version = ATLAS_MANIFEST_VERSION; request_id: StableId; snapshot_fingerprint: HEX64; package_fingerprint: HEX64 | Literal[""] = ""; compiler_policy_fingerprint: HEX64; selected_provider_ids: tuple[ProviderId, ...] = (); excluded_provider_ids: tuple[ProviderId, ...] = (); entries: tuple[AtlasCompilerDecision, ...] = (); stage_summaries: tuple[AtlasCompilerStageSummary, ...] = (); warning_categories: tuple[ProviderId, ...] = (); conflict_ids: tuple[StableId, ...] = (); budget_summary: AtlasBudgetUsage = Field(default_factory=AtlasBudgetUsage); optimization_summary: FrozenJson = Field(default_factory=FrozenJson); deterministic_digest: HEX64 | Literal[""] = ""; metadata: FrozenJson = Field(default_factory=FrozenJson)
    _ids = field_validator("selected_provider_ids", "excluded_provider_ids", "warning_categories", "conflict_ids")(_stable_unique)
    _freeze = field_validator("optimization_summary", "metadata", mode="before")(_frozen)

    @model_validator(mode="after")
    def valid_entries(self):
        if set(self.selected_provider_ids) & set(self.excluded_provider_ids):
            raise ValueError("Manifest provider sets must not overlap.")
        if len({item.decision_id for item in self.entries}) != len(self.entries):
            raise ValueError("Manifest decision identifiers must be unique.")
        return self

    @property
    def computed_digest(self) -> str:
        payload = self.canonical_dict(); payload["deterministic_digest"] = ""
        return fingerprint(payload)


class AtlasManifestReference(AtlasCanonicalModel):
    manifest_version: Version = ATLAS_MANIFEST_VERSION
    manifest_digest: HEX64
    deterministic_digest: HEX64
    decision_count: int = Field(ge=0, le=1_000_000)
    stage_summary_count: int = Field(ge=0, le=64)
    selected_provider_count: int = Field(ge=0, le=32)
    excluded_provider_count: int = Field(ge=0, le=32)
    warning_count: int = Field(ge=0, le=256)
    conflict_count: int = Field(ge=0, le=100_000)
    budget_decision_count: int = Field(ge=0, le=1_000_000)

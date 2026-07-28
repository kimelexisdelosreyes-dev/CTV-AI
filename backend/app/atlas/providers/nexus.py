from __future__ import annotations

import asyncio
import json
import re
from enum import StrEnum
from threading import Lock
from time import perf_counter
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.atlas.canonical import AtlasCanonicalModel, FrozenJson, fingerprint
from app.atlas.models import (
    AtlasHealthStatus,
    AtlasProviderCollectionContext,
    AtlasProviderBudget,
    AtlasProviderDefinition,
    AtlasProviderHealth,
    AtlasProviderReadiness,
    AtlasProviderRequest,
    AtlasProviderResult,
)
from app.atlas.provider import AtlasProvider, AtlasRuntimeContext
from app.core.config import settings


NEXUS_PROVIDER_ID = "nexus"
NEXUS_CAPABILITY = "knowledge_graph"
NEXUS_GRAPH_VERSION = "1.0"
NEXUS_GRAPH_FORMAT_VERSION = "1.0"
NEXUS_BUILDER_VERSION = "1.0"
NEXUS_FINGERPRINT_VERSION = "1.0"
NEXUS_SUPPORTED_SCHEMA_VERSION = "1.0"
NEXUS_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,127}$")


class NexusGraphErrorCategory(StrEnum):
    INVALID_ENTITY = "invalid_entity"
    INVALID_RELATIONSHIP = "invalid_relationship"
    DUPLICATE_CONFLICT = "duplicate_conflict"
    ORPHAN_RELATIONSHIP = "orphan_relationship"
    UNSUPPORTED_SCHEMA = "unsupported_schema"
    GRAPH_LIMIT_EXCEEDED = "graph_limit_exceeded"
    SNAPSHOT_BUILD_FAILED = "snapshot_build_failed"
    SNAPSHOT_UNAVAILABLE = "snapshot_unavailable"
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"
    BUILD_TIMEOUT = "build_timeout"


class NexusGraphInfrastructureError(ValueError):
    def __init__(self, category: NexusGraphErrorCategory) -> None:
        super().__init__(category.value)
        self.category = category


class NexusGraphSchemaVersion(AtlasCanonicalModel):
    major: int = Field(ge=1, le=99)
    minor: int = Field(ge=0, le=99)

    @classmethod
    def current(cls) -> "NexusGraphSchemaVersion":
        return cls(major=1, minor=0)

    @classmethod
    def parse(cls, value: str | "NexusGraphSchemaVersion") -> "NexusGraphSchemaVersion":
        if isinstance(value, NexusGraphSchemaVersion):
            return value
        parts = str(value).split(".")
        if len(parts) != 2:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.UNSUPPORTED_SCHEMA)
        try:
            return cls(major=int(parts[0]), minor=int(parts[1]))
        except ValueError as exc:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.UNSUPPORTED_SCHEMA) from exc

    @property
    def value(self) -> str:
        return f"{self.major}.{self.minor}"

    def ensure_supported(self) -> None:
        current = self.current()
        if self.major != current.major or self.minor > current.minor:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.UNSUPPORTED_SCHEMA)


def normalize_nexus_identifier(value: str) -> str:
    normalized = "_".join(str(value).strip().lower().replace("-", "_").split())
    if not normalized or not NEXUS_ID_PATTERN.fullmatch(normalized):
        raise NexusGraphInfrastructureError(NexusGraphErrorCategory.INVALID_ENTITY)
    return normalized


def deterministic_entity_id(namespace: str, entity_type: str, external_key: str) -> str:
    namespace_id = normalize_nexus_identifier(namespace)
    type_id = normalize_nexus_identifier(entity_type)
    key_id = normalize_nexus_identifier(external_key)
    return f"{namespace_id}:{type_id}:{key_id}"


def deterministic_relationship_id(
    namespace: str,
    source_entity_id: str,
    relationship_type: str,
    target_entity_id: str,
    discriminator: str | None = None,
) -> str:
    namespace_id = normalize_nexus_identifier(namespace)
    source_id = normalize_nexus_identifier(source_entity_id)
    relation_id = normalize_nexus_identifier(relationship_type)
    target_id = normalize_nexus_identifier(target_entity_id)
    if source_id == target_id:
        raise NexusGraphInfrastructureError(NexusGraphErrorCategory.INVALID_RELATIONSHIP)
    values = [namespace_id, source_id, relation_id, target_id]
    if discriminator:
        values.append(normalize_nexus_identifier(discriminator))
    return ":".join(values)


class NexusEntity(AtlasCanonicalModel):
    entity_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    entity_type: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=256)
    confidence: int = Field(default=100, ge=0, le=100)
    source_reference: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class NexusRelationship(AtlasCanonicalModel):
    relationship_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    source_entity_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    target_entity_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    relationship_type: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    confidence: int = Field(default=100, ge=0, le=100)
    source_reference: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class NexusPath(AtlasCanonicalModel):
    entity_ids: tuple[str, ...] = Field(default=(), max_length=16)
    relationship_ids: tuple[str, ...] = Field(default=(), max_length=16)
    confidence: int = Field(default=100, ge=0, le=100)


class NexusEntityInput(AtlasCanonicalModel):
    namespace: str
    entity_type: str
    external_key: str
    label: str = Field(min_length=1, max_length=256)
    aliases: tuple[str, ...] = Field(default=(), max_length=8)
    confidence: int = Field(default=100, ge=0, le=100)
    source_reference: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    metadata: FrozenJson = Field(default_factory=FrozenJson)

    @field_validator("metadata", mode="before")
    @classmethod
    def freeze_metadata(cls, value) -> FrozenJson:
        return value if isinstance(value, FrozenJson) else FrozenJson(value)

    @model_validator(mode="after")
    def validate_identity(self) -> "NexusEntityInput":
        deterministic_entity_id(self.namespace, self.entity_type, self.external_key)
        if len(self.metadata._json.encode("utf-8")) > settings.ctv_one_nexus_max_metadata_bytes:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED)
        if len(self.aliases) > settings.ctv_one_nexus_max_entity_aliases:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED)
        return self

    @property
    def entity_id(self) -> str:
        return deterministic_entity_id(self.namespace, self.entity_type, self.external_key)


class NexusRelationshipInput(AtlasCanonicalModel):
    namespace: str
    source_namespace: str
    source_entity_type: str
    source_external_key: str
    relationship_type: str
    target_namespace: str
    target_entity_type: str
    target_external_key: str
    discriminator: str | None = None
    confidence: int = Field(default=100, ge=0, le=100)
    source_reference: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    metadata: FrozenJson = Field(default_factory=FrozenJson)

    @field_validator("metadata", mode="before")
    @classmethod
    def freeze_metadata(cls, value) -> FrozenJson:
        return value if isinstance(value, FrozenJson) else FrozenJson(value)

    @model_validator(mode="after")
    def validate_identity(self) -> "NexusRelationshipInput":
        deterministic_relationship_id(
            self.namespace,
            self.source_entity_id,
            self.relationship_type,
            self.target_entity_id,
            self.discriminator,
        )
        if len(self.metadata._json.encode("utf-8")) > settings.ctv_one_nexus_max_metadata_bytes:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED)
        return self

    @property
    def source_entity_id(self) -> str:
        return deterministic_entity_id(self.source_namespace, self.source_entity_type, self.source_external_key)

    @property
    def target_entity_id(self) -> str:
        return deterministic_entity_id(self.target_namespace, self.target_entity_type, self.target_external_key)

    @property
    def relationship_id(self) -> str:
        return deterministic_relationship_id(
            self.namespace,
            self.source_entity_id,
            self.relationship_type,
            self.target_entity_id,
            self.discriminator,
        )


class NexusGraphImportBatch(AtlasCanonicalModel):
    source_id: str
    source_version: str = "1.0"
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entities: tuple[NexusEntityInput, ...] = Field(default=(), max_length=100_000)
    relationships: tuple[NexusRelationshipInput, ...] = Field(default=(), max_length=100_000)
    import_metadata: FrozenJson = Field(default_factory=FrozenJson)
    graph_schema_version: NexusGraphSchemaVersion = Field(default_factory=NexusGraphSchemaVersion.current)

    @field_validator("import_metadata", mode="before")
    @classmethod
    def freeze_metadata(cls, value) -> FrozenJson:
        return value if isinstance(value, FrozenJson) else FrozenJson(value)

    @field_validator("graph_schema_version", mode="before")
    @classmethod
    def parse_schema(cls, value) -> NexusGraphSchemaVersion:
        return NexusGraphSchemaVersion.parse(value)

    @model_validator(mode="after")
    def validate_batch(self) -> "NexusGraphImportBatch":
        self.graph_schema_version.ensure_supported()
        if len(self.import_metadata._json.encode("utf-8")) > settings.ctv_one_nexus_max_metadata_bytes:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED)
        return self

    @property
    def batch_fingerprint(self) -> str:
        return self.deterministic_fingerprint()


class NexusGraphResult(AtlasCanonicalModel):
    entities: tuple[NexusEntity, ...] = ()
    relationships: tuple[NexusRelationship, ...] = ()
    paths: tuple[NexusPath, ...] = ()
    confidence: int = Field(default=100, ge=0, le=100)
    source_references: tuple[str, ...] = ()
    graph_version: str = NEXUS_GRAPH_VERSION
    graph_fingerprint: str = ""

    @model_validator(mode="after")
    def canonical_graph(self) -> "NexusGraphResult":
        entities = tuple(sorted(self.entities, key=lambda item: item.entity_id))
        relationships = tuple(sorted(self.relationships, key=lambda item: item.relationship_id))
        references = tuple(sorted(set(self.source_references)))
        object.__setattr__(self, "entities", entities)
        object.__setattr__(self, "relationships", relationships)
        object.__setattr__(self, "source_references", references)
        expected = self.computed_fingerprint()
        if self.graph_fingerprint and self.graph_fingerprint != expected:
            raise ValueError("Nexus graph fingerprint is invalid.")
        return self

    def computed_fingerprint(self) -> str:
        payload = self.canonical_dict()
        payload["graph_fingerprint"] = ""
        return fingerprint(payload)


class NexusSourceSummary(AtlasCanonicalModel):
    source_id_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_version: str
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entity_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)


class NexusGraphSnapshot(AtlasCanonicalModel):
    schema_version: NexusGraphSchemaVersion = Field(default_factory=NexusGraphSchemaVersion.current)
    graph_version: str = NEXUS_GRAPH_VERSION
    graph_format_version: str = NEXUS_GRAPH_FORMAT_VERSION
    builder_version: str = NEXUS_BUILDER_VERSION
    fingerprint_version: str = NEXUS_FINGERPRINT_VERSION
    entities: tuple[NexusEntity, ...] = ()
    relationships: tuple[NexusRelationship, ...] = ()
    entity_index: tuple[tuple[str, int], ...] = ()
    entity_type_index: tuple[tuple[str, tuple[str, ...]], ...] = ()
    relationship_index: tuple[tuple[str, int], ...] = ()
    outgoing_index: tuple[tuple[str, tuple[str, ...]], ...] = ()
    incoming_index: tuple[tuple[str, tuple[str, ...]], ...] = ()
    adjacency_index: tuple[tuple[str, tuple[str, ...]], ...] = ()
    source_summary: tuple[NexusSourceSummary, ...] = ()
    graph_fingerprint: str = ""
    entity_count: int = Field(default=0, ge=0)
    relationship_count: int = Field(default=0, ge=0)

    @field_validator("schema_version", mode="before")
    @classmethod
    def parse_schema(cls, value) -> NexusGraphSchemaVersion:
        return NexusGraphSchemaVersion.parse(value)

    @model_validator(mode="after")
    def validate_snapshot(self) -> "NexusGraphSnapshot":
        self.schema_version.ensure_supported()
        if self.entity_count != len(self.entities) or self.relationship_count != len(self.relationships):
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.SNAPSHOT_BUILD_FAILED)
        expected = self.computed_fingerprint()
        if self.graph_fingerprint and self.graph_fingerprint != expected:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.FINGERPRINT_MISMATCH)
        return self

    def computed_fingerprint(self) -> str:
        payload = self.canonical_dict()
        payload["graph_fingerprint"] = ""
        return fingerprint(payload)

    def entity_by_id(self, entity_id: str) -> NexusEntity | None:
        normalized = normalize_nexus_identifier(entity_id)
        mapping = dict(self.entity_index)
        index = mapping.get(normalized)
        return None if index is None else self.entities[index]

    def relationships_by_ids(self, relationship_ids: tuple[str, ...]) -> tuple[NexusRelationship, ...]:
        mapping = dict(self.relationship_index)
        return tuple(
            self.relationships[mapping[item]]
            for item in relationship_ids
            if item in mapping
        )

    def outgoing(self, entity_id: str) -> tuple[NexusRelationship, ...]:
        ids = dict(self.outgoing_index).get(normalize_nexus_identifier(entity_id), ())
        return self.relationships_by_ids(ids)

    def incoming(self, entity_id: str) -> tuple[NexusRelationship, ...]:
        ids = dict(self.incoming_index).get(normalize_nexus_identifier(entity_id), ())
        return self.relationships_by_ids(ids)


class NexusBuildReport(AtlasCanonicalModel):
    deduplicated_count: int = 0
    conflict_count: int = 0
    limit_rejection_count: int = 0


class NexusGraphBuilder:
    def __init__(self) -> None:
        self._batches: list[NexusGraphImportBatch] = []

    @classmethod
    def from_graph(
        cls,
        entities: tuple[NexusEntity, ...],
        relationships: tuple[NexusRelationship, ...],
    ) -> NexusGraphSnapshot:
        builder = cls()
        builder._enforce_construction_limits(tuple(sorted(entities, key=lambda item: item.entity_id)), tuple(sorted(relationships, key=lambda item: item.relationship_id)))
        snapshot = builder._snapshot(
            tuple(sorted(entities, key=lambda item: item.entity_id)),
            tuple(sorted(relationships, key=lambda item: item.relationship_id)),
        )
        return snapshot

    def add_batch(self, batch: NexusGraphImportBatch) -> None:
        if len(self._batches) + 1 > settings.ctv_one_nexus_max_import_batches:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED)
        self._batches.append(batch)

    def build(self) -> tuple[NexusGraphSnapshot, NexusBuildReport]:
        started = perf_counter()
        try:
            snapshot, report = self._build()
            if (perf_counter() - started) > settings.ctv_one_nexus_max_build_seconds:
                raise NexusGraphInfrastructureError(NexusGraphErrorCategory.BUILD_TIMEOUT)
            if len(snapshot.canonical_bytes()) > settings.ctv_one_nexus_max_snapshot_bytes:
                raise NexusGraphInfrastructureError(NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED)
            return snapshot, report
        except NexusGraphInfrastructureError:
            raise
        except Exception as exc:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.SNAPSHOT_BUILD_FAILED) from exc

    def _build(self) -> tuple[NexusGraphSnapshot, NexusBuildReport]:
        entities_by_id: dict[str, NexusEntity] = {}
        relationships_by_id: dict[str, NexusRelationship] = {}
        deduplicated = conflicts = 0
        for batch in sorted(self._batches, key=lambda item: item.batch_fingerprint):
            for item in sorted(batch.entities, key=lambda entity: entity.entity_id):
                entity = NexusEntity(
                    entity_id=item.entity_id,
                    entity_type=normalize_nexus_identifier(item.entity_type),
                    label=item.label,
                    confidence=item.confidence,
                    source_reference=item.source_reference,
                )
                existing = entities_by_id.get(entity.entity_id)
                if existing is None:
                    entities_by_id[entity.entity_id] = entity
                elif existing == entity:
                    deduplicated += 1
                else:
                    conflicts += 1
                    raise NexusGraphInfrastructureError(NexusGraphErrorCategory.DUPLICATE_CONFLICT)
        for batch in sorted(self._batches, key=lambda item: item.batch_fingerprint):
            for item in sorted(batch.relationships, key=lambda relationship: relationship.relationship_id):
                if item.source_entity_id == item.target_entity_id:
                    raise NexusGraphInfrastructureError(NexusGraphErrorCategory.INVALID_RELATIONSHIP)
                if item.source_entity_id not in entities_by_id or item.target_entity_id not in entities_by_id:
                    raise NexusGraphInfrastructureError(NexusGraphErrorCategory.ORPHAN_RELATIONSHIP)
                relationship = NexusRelationship(
                    relationship_id=item.relationship_id,
                    source_entity_id=item.source_entity_id,
                    target_entity_id=item.target_entity_id,
                    relationship_type=normalize_nexus_identifier(item.relationship_type),
                    confidence=item.confidence,
                    source_reference=item.source_reference,
                )
                existing = relationships_by_id.get(relationship.relationship_id)
                if existing is None:
                    relationships_by_id[relationship.relationship_id] = relationship
                elif existing == relationship:
                    deduplicated += 1
                else:
                    conflicts += 1
                    raise NexusGraphInfrastructureError(NexusGraphErrorCategory.DUPLICATE_CONFLICT)
        entities = tuple(entities_by_id[key] for key in sorted(entities_by_id))
        relationships = tuple(relationships_by_id[key] for key in sorted(relationships_by_id))
        self._enforce_construction_limits(entities, relationships)
        snapshot = self._snapshot(entities, relationships)
        return snapshot, NexusBuildReport(deduplicated_count=deduplicated, conflict_count=conflicts)

    def _enforce_construction_limits(
        self, entities: tuple[NexusEntity, ...], relationships: tuple[NexusRelationship, ...]
    ) -> None:
        if len(entities) > settings.ctv_one_nexus_max_entities:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED)
        if len(relationships) > settings.ctv_one_nexus_max_relationships:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED)
        counts: dict[str, int] = {}
        for relationship in relationships:
            counts[relationship.source_entity_id] = counts.get(relationship.source_entity_id, 0) + 1
            counts[relationship.target_entity_id] = counts.get(relationship.target_entity_id, 0) + 1
        if any(value > settings.ctv_one_nexus_max_relationships_per_entity for value in counts.values()):
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED)

    def _snapshot(self, entities: tuple[NexusEntity, ...], relationships: tuple[NexusRelationship, ...]) -> NexusGraphSnapshot:
        entity_index = tuple((entity.entity_id, index) for index, entity in enumerate(entities))
        entity_type_values: dict[str, list[str]] = {}
        for entity in entities:
            entity_type_values.setdefault(entity.entity_type, []).append(entity.entity_id)
        relationship_index = tuple((relationship.relationship_id, index) for index, relationship in enumerate(relationships))
        outgoing: dict[str, list[str]] = {}
        incoming: dict[str, list[str]] = {}
        adjacency: dict[str, set[str]] = {}
        for relationship in relationships:
            outgoing.setdefault(relationship.source_entity_id, []).append(relationship.relationship_id)
            incoming.setdefault(relationship.target_entity_id, []).append(relationship.relationship_id)
            adjacency.setdefault(relationship.source_entity_id, set()).add(relationship.target_entity_id)
            adjacency.setdefault(relationship.target_entity_id, set()).add(relationship.source_entity_id)
        source_summary = tuple(
            NexusSourceSummary(
                source_id_hash=fingerprint(batch.source_id),
                source_version=batch.source_version,
                source_fingerprint=batch.source_fingerprint,
                entity_count=len(batch.entities),
                relationship_count=len(batch.relationships),
            )
            for batch in sorted(self._batches, key=lambda item: item.batch_fingerprint)
        )
        snapshot = NexusGraphSnapshot(
            entities=entities,
            relationships=relationships,
            entity_index=entity_index,
            entity_type_index=tuple((key, tuple(sorted(value))) for key, value in sorted(entity_type_values.items())),
            relationship_index=relationship_index,
            outgoing_index=tuple((key, tuple(sorted(value))) for key, value in sorted(outgoing.items())),
            incoming_index=tuple((key, tuple(sorted(value))) for key, value in sorted(incoming.items())),
            adjacency_index=tuple((key, tuple(sorted(value))) for key, value in sorted(adjacency.items())),
            source_summary=source_summary,
            entity_count=len(entities),
            relationship_count=len(relationships),
        )
        return snapshot.model_copy(update={"graph_fingerprint": snapshot.computed_fingerprint()})


class NexusQuery(AtlasCanonicalModel):
    query_type: Literal["entity_lookup", "relationship_lookup", "neighborhood", "path_discovery"] = "neighborhood"
    entity_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    target_entity_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    max_entities: int = Field(ge=0, le=256)
    max_relationships: int = Field(ge=0, le=512)
    max_depth: int = Field(ge=0, le=8)


class NexusGraphLimitsExceeded(ValueError):
    pass


class NexusGraphStore:
    def __init__(
        self,
        *,
        entities: tuple[NexusEntity, ...] | None = None,
        relationships: tuple[NexusRelationship, ...] | None = None,
        snapshot: NexusGraphSnapshot | None = None,
    ) -> None:
        self._lock = Lock()
        self._snapshot = snapshot or NexusGraphBuilder.from_graph(
            entities or _default_entities(),
            relationships or _default_relationships(),
        )

    @property
    def snapshot(self) -> NexusGraphSnapshot | None:
        with self._lock:
            return self._snapshot

    @property
    def ready(self) -> bool:
        return self.snapshot is not None

    def replace_snapshot(self, snapshot: NexusGraphSnapshot) -> None:
        if not isinstance(snapshot, NexusGraphSnapshot):
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.SNAPSHOT_BUILD_FAILED)
        with self._lock:
            self._snapshot = snapshot

    def build_and_replace(self, batches: tuple[NexusGraphImportBatch, ...]) -> NexusBuildReport:
        builder = NexusGraphBuilder()
        for batch in batches:
            builder.add_batch(batch)
        snapshot, report = builder.build()
        self.replace_snapshot(snapshot)
        return report

    async def query(self, query: NexusQuery) -> NexusGraphResult:
        self._validate_limits(query)
        snapshot = self.snapshot
        if snapshot is None:
            raise NexusGraphInfrastructureError(NexusGraphErrorCategory.SNAPSHOT_UNAVAILABLE)
        if query.query_type == "entity_lookup":
            entity = snapshot.entity_by_id(query.entity_id or "")
            entities = (entity,) if entity is not None else ()
            relationships: tuple[NexusRelationship, ...] = ()
        elif query.query_type == "relationship_lookup":
            relationships = tuple(sorted(snapshot.outgoing(query.entity_id or "") + snapshot.incoming(query.entity_id or ""), key=lambda item: item.relationship_id))
            entity_ids = {
                value for item in relationships for value in (item.source_entity_id, item.target_entity_id)
            }
            entities = tuple(item for item in snapshot.entities if item.entity_id in entity_ids)
        elif query.query_type == "path_discovery" and query.entity_id and query.target_entity_id:
            entities, relationships = self._path(query, snapshot)
        else:
            entities, relationships = self._neighborhood(query, snapshot)
        result = NexusGraphResult(
            entities=entities[: query.max_entities],
            relationships=relationships[: query.max_relationships],
            confidence=100,
            source_references=tuple(item.source_reference for item in entities)
            + tuple(item.source_reference for item in relationships),
        )
        return result.model_copy(update={"graph_fingerprint": result.computed_fingerprint()})

    def _validate_limits(self, query: NexusQuery) -> None:
        if query.max_depth > settings.ctv_one_nexus_max_traversal_depth:
            raise NexusGraphLimitsExceeded("nexus_traversal_depth_exceeded")
        if query.max_entities > settings.ctv_one_nexus_max_entities:
            raise NexusGraphLimitsExceeded("nexus_entity_limit_exceeded")
        if query.max_relationships > settings.ctv_one_nexus_max_relationships:
            raise NexusGraphLimitsExceeded("nexus_relationship_limit_exceeded")

    def _neighborhood(self, query: NexusQuery, snapshot: NexusGraphSnapshot) -> tuple[tuple[NexusEntity, ...], tuple[NexusRelationship, ...]]:
        start = query.entity_id or (snapshot.entities[0].entity_id if snapshot.entities else None)
        if start is None:
            return (), ()
        seen = {start}
        frontier = {start}
        selected: list[NexusRelationship] = []
        for _ in range(query.max_depth + 1):
            next_frontier: set[str] = set()
            for entity_id in sorted(frontier):
                candidates = snapshot.outgoing(entity_id) + snapshot.incoming(entity_id)
                for relationship in candidates:
                    selected.append(relationship)
                    next_frontier.update((relationship.source_entity_id, relationship.target_entity_id))
            frontier = next_frontier - seen
            seen.update(next_frontier)
            if len(seen) >= query.max_entities or len(selected) >= query.max_relationships:
                break
        entities = tuple(item for item in snapshot.entities if item.entity_id in seen)
        relationships = tuple({item.relationship_id: item for item in selected}.values())
        return entities, tuple(sorted(relationships, key=lambda item: item.relationship_id))

    def _path(self, query: NexusQuery, snapshot: NexusGraphSnapshot) -> tuple[tuple[NexusEntity, ...], tuple[NexusRelationship, ...]]:
        relationships = tuple(
            item
            for item in snapshot.relationships
            if item.source_entity_id == query.entity_id and item.target_entity_id == query.target_entity_id
        )
        ids = {query.entity_id, query.target_entity_id}
        entities = tuple(item for item in snapshot.entities if item.entity_id in ids)
        return entities, relationships


class NexusMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.query_count = 0
        self.success_count = 0
        self.timeout_count = 0
        self.failure_count = 0
        self.total_latency_ms = 0.0
        self.total_entities = 0
        self.total_relationships = 0
        self.graph_version = NEXUS_GRAPH_VERSION
        self.provider_status = "created"
        self.graph_ready = False
        self.graph_schema_version = NEXUS_SUPPORTED_SCHEMA_VERSION
        self.graph_fingerprint_prefix = None
        self.active_entity_count = 0
        self.active_relationship_count = 0
        self.graph_build_count = 0
        self.graph_build_success_count = 0
        self.graph_build_failure_count = 0
        self.snapshot_replacement_count = 0
        self.total_build_latency_ms = 0.0
        self.duplicate_deduplication_count = 0
        self.duplicate_conflict_count = 0
        self.limit_rejection_count = 0
        self.retrieval_count = 0
        self.total_retrieval_latency_ms = 0.0
        self.total_retrieval_hops = 0.0
        self.total_budget_utilization = 0.0
        self.total_selected_entities = 0
        self.total_selected_relationships = 0
        self.total_discarded_entities = 0
        self.total_discarded_relationships = 0
        self.total_retrieval_score = 0.0
        self.retrieval_engine_version = "1.0"
        self.retrieval_mode = "balanced"
        self.last_retrieval_budget_used_bytes = 0

    def record(self, *, latency_ms: float, status: str, entities: int = 0, relationships: int = 0) -> None:
        with self._lock:
            self.query_count += 1
            self.total_latency_ms += latency_ms
            self.provider_status = status
            if status == "success":
                self.success_count += 1
                self.total_entities += entities
                self.total_relationships += relationships
            elif status == "timeout":
                self.timeout_count += 1
            else:
                self.failure_count += 1

    def set_active_snapshot(self, snapshot: NexusGraphSnapshot | None) -> None:
        with self._lock:
            self.graph_ready = snapshot is not None
            if snapshot is not None:
                self.graph_schema_version = snapshot.schema_version.value
                self.graph_version = snapshot.graph_version
                self.graph_fingerprint_prefix = snapshot.graph_fingerprint[:12]
                self.active_entity_count = snapshot.entity_count
                self.active_relationship_count = snapshot.relationship_count

    def record_build(
        self,
        *,
        latency_ms: float,
        success: bool,
        report: NexusBuildReport | None = None,
        category: NexusGraphErrorCategory | None = None,
        replaced: bool = False,
    ) -> None:
        with self._lock:
            self.graph_build_count += 1
            self.total_build_latency_ms += latency_ms
            if success:
                self.graph_build_success_count += 1
            else:
                self.graph_build_failure_count += 1
            if replaced:
                self.snapshot_replacement_count += 1
            if report is not None:
                self.duplicate_deduplication_count += report.deduplicated_count
                self.duplicate_conflict_count += report.conflict_count
                self.limit_rejection_count += report.limit_rejection_count
            if category == NexusGraphErrorCategory.DUPLICATE_CONFLICT:
                self.duplicate_conflict_count += 1
            if category == NexusGraphErrorCategory.GRAPH_LIMIT_EXCEEDED:
                self.limit_rejection_count += 1

    def record_retrieval(self, *, latency_ms: float, request, result) -> None:
        with self._lock:
            self.retrieval_count += 1
            self.total_retrieval_latency_ms += latency_ms
            self.total_retrieval_hops += result.average_hops
            self.total_budget_utilization += result.budget_summary.budget_utilization_percent
            self.total_selected_entities += result.budget_summary.selected_entities
            self.total_selected_relationships += result.budget_summary.selected_relationships
            self.total_discarded_entities += result.budget_summary.discarded_entities
            self.total_discarded_relationships += result.budget_summary.discarded_relationships
            self.total_retrieval_score += result.average_score
            self.retrieval_mode = request.retrieval_mode.value
            self.last_retrieval_budget_used_bytes = result.budget_summary.used_bytes

    def diagnostics(self) -> dict[str, object]:
        with self._lock:
            retrieval_denominator = max(self.retrieval_count, 1)
            return {
                "graph_ready": self.graph_ready,
                "graph_schema_version": self.graph_schema_version,
                "graph_version": self.graph_version,
                "graph_fingerprint_prefix": self.graph_fingerprint_prefix,
                "entity_count": self.active_entity_count,
                "relationship_count": self.active_relationship_count,
                "active_snapshot_available": self.graph_ready,
                "provider_status": self.provider_status,
                "query_count": self.query_count,
                "average_latency_ms": round(self.total_latency_ms / max(self.query_count, 1), 3) if self.query_count else 0.0,
                "success_rate": round((self.success_count / self.query_count) * 100, 3) if self.query_count else 100.0,
                "timeout_count": self.timeout_count,
                "average_entity_count": round(self.total_entities / max(self.success_count, 1), 3) if self.success_count else 0.0,
                "average_relationship_count": round(self.total_relationships / max(self.success_count, 1), 3) if self.success_count else 0.0,
                "successful_builds": self.graph_build_success_count,
                "failed_builds": self.graph_build_failure_count,
                "snapshot_replacements": self.snapshot_replacement_count,
                "average_build_latency_ms": round(self.total_build_latency_ms / max(self.graph_build_count, 1), 3) if self.graph_build_count else 0.0,
                "duplicate_deduplication_count": self.duplicate_deduplication_count,
                "duplicate_conflict_count": self.duplicate_conflict_count,
                "limit_rejection_count": self.limit_rejection_count,
                "retrieval_engine_version": self.retrieval_engine_version,
                "retrieval_mode": self.retrieval_mode,
                "retrieval_count": self.retrieval_count,
                "average_retrieval_latency_ms": round(self.total_retrieval_latency_ms / retrieval_denominator, 3) if self.retrieval_count else 0.0,
                "average_retrieval_hops": round(self.total_retrieval_hops / retrieval_denominator, 3) if self.retrieval_count else 0.0,
                "average_budget_utilization_percent": round(self.total_budget_utilization / retrieval_denominator, 3) if self.retrieval_count else 0.0,
                "average_selected_entity_count": round(self.total_selected_entities / retrieval_denominator, 3) if self.retrieval_count else 0.0,
                "average_selected_relationship_count": round(self.total_selected_relationships / retrieval_denominator, 3) if self.retrieval_count else 0.0,
                "discarded_entity_count": self.total_discarded_entities,
                "discarded_relationship_count": self.total_discarded_relationships,
                "average_retrieval_score": round(self.total_retrieval_score / retrieval_denominator, 3) if self.retrieval_count else 0.0,
                "last_retrieval_budget_used_bytes": self.last_retrieval_budget_used_bytes,
            }


class NexusProvider(AtlasProvider):
    def __init__(self, *, graph_store: NexusGraphStore | None = None, metrics: NexusMetrics | None = None) -> None:
        timeout = max(settings.ctv_one_nexus_max_execution_seconds, 0.001)
        self.definition = AtlasProviderDefinition(
            provider_id=NEXUS_PROVIDER_ID,
            display_name="Nexus Knowledge Graph",
            description="Read-only deterministic Nexus graph context provider.",
            version="1.0.0",
            capabilities=frozenset({NEXUS_CAPABILITY}),
            enabled_by_default=settings.ctv_one_nexus_provider_enabled,
            default_timeout_seconds=timeout,
            max_timeout_seconds=max(timeout, 1.0),
            default_budget=AtlasProviderBudget(max_duration_seconds=timeout),
            tags=frozenset({"nexus", "graph"}),
        )
        self.graph_store = graph_store or NexusGraphStore()
        self.metrics = metrics or NexusMetrics()
        self.metrics.set_active_snapshot(getattr(self.graph_store, "snapshot", None))
        self._initialized = False

    async def initialize(self, runtime_context: AtlasRuntimeContext) -> None:
        self._initialized = True
        self.metrics.provider_status = "ready"

    async def health_check(self) -> AtlasProviderHealth:
        return AtlasProviderHealth(status=AtlasHealthStatus.HEALTHY, safe_message="Nexus provider is ready.")

    async def readiness_check(self) -> AtlasProviderReadiness:
        return AtlasProviderReadiness(
            ready=self._initialized,
            available_capabilities=frozenset({NEXUS_CAPABILITY}) if self._initialized else frozenset(),
            unavailable_capabilities=frozenset() if self._initialized else frozenset({NEXUS_CAPABILITY}),
        )

    async def collect(self, request: AtlasProviderRequest, context: AtlasProviderCollectionContext) -> AtlasProviderResult:
        started = perf_counter()
        query = NexusQuery(
            query_type="neighborhood",
            max_entities=min(context.budget.max_items, settings.ctv_one_nexus_max_entities),
            max_relationships=settings.ctv_one_nexus_max_relationships,
            max_depth=settings.ctv_one_nexus_max_traversal_depth,
        )
        try:
            async with asyncio.timeout(min(context.budget.max_duration_seconds, settings.ctv_one_nexus_max_execution_seconds)):
                snapshot = getattr(self.graph_store, "snapshot", None)
                if isinstance(snapshot, NexusGraphSnapshot):
                    from app.atlas.nexus_retrieval import NexusRetrievalEngine, NexusRetrievalRequest

                    retrieval_started = perf_counter()
                    retrieval_request = NexusRetrievalRequest(
                        maximum_hops=min(settings.ctv_one_nexus_max_traversal_depth, 3),
                        maximum_entities=min(context.budget.max_items, settings.ctv_one_nexus_max_entities),
                        maximum_relationships=settings.ctv_one_nexus_max_relationships,
                        maximum_bytes=max(512, context.budget.max_output_chars),
                        maximum_tokens_estimate=max(16, context.budget.max_output_chars // 4),
                        provider_timeout_seconds=min(context.budget.max_duration_seconds, settings.ctv_one_nexus_max_execution_seconds),
                    )
                    retrieval = NexusRetrievalEngine().retrieve(snapshot, retrieval_request)
                    self.metrics.record_retrieval(
                        latency_ms=(perf_counter() - retrieval_started) * 1000,
                        request=retrieval_request,
                        result=retrieval,
                    )
                    graph = retrieval.to_graph_result()
                else:
                    graph = await self.graph_store.query(query)
            self.metrics.record(
                latency_ms=(perf_counter() - started) * 1000,
                status="success",
                entities=len(graph.entities),
                relationships=len(graph.relationships),
            )
            return nexus_graph_to_provider_result(graph)
        except TimeoutError:
            self.metrics.record(latency_ms=(perf_counter() - started) * 1000, status="timeout")
            return AtlasProviderResult(
                provider_id=NEXUS_PROVIDER_ID,
                status="unavailable",
                warnings=("nexus_timeout",),
                safe_error_category="nexus_timeout",
            )
        except NexusGraphLimitsExceeded as exc:
            self.metrics.record(latency_ms=(perf_counter() - started) * 1000, status="failure")
            return AtlasProviderResult(provider_id=NEXUS_PROVIDER_ID, status="partial", warnings=(str(exc),))
        except NexusGraphInfrastructureError as exc:
            self.metrics.record(latency_ms=(perf_counter() - started) * 1000, status="failure")
            return AtlasProviderResult(
                provider_id=NEXUS_PROVIDER_ID,
                status="unavailable",
                warnings=(exc.category.value,),
                safe_error_category=exc.category.value,
            )

    def build_and_replace_snapshot(self, batches: tuple[NexusGraphImportBatch, ...]) -> NexusBuildReport:
        started = perf_counter()
        try:
            builder = NexusGraphBuilder()
            for batch in batches:
                builder.add_batch(batch)
            snapshot, report = builder.build()
            self.graph_store.replace_snapshot(snapshot)
            self.metrics.set_active_snapshot(snapshot)
            self.metrics.record_build(
                latency_ms=(perf_counter() - started) * 1000,
                success=True,
                report=report,
                replaced=True,
            )
            return report
        except NexusGraphInfrastructureError as exc:
            self.metrics.record_build(
                latency_ms=(perf_counter() - started) * 1000,
                success=False,
                category=exc.category,
            )
            raise

    async def shutdown(self) -> None:
        self._initialized = False
        self.metrics.provider_status = "stopped"


def nexus_graph_to_provider_result(graph: NexusGraphResult) -> AtlasProviderResult:
    records = []
    for entity in graph.entities:
        records.append(
            {
                "id": f"nexus_entity_{entity.entity_id}",
                "title": entity.label,
                "content": f"{entity.entity_type}:{entity.label}",
                "source_reference": entity.source_reference,
                "confidence_points": entity.confidence,
                "attributes": {"entity_type": entity.entity_type, "graph_version": graph.graph_version},
            }
        )
    for relationship in graph.relationships:
        records.append(
            {
                "id": f"nexus_relationship_{relationship.relationship_id}",
                "title": relationship.relationship_type,
                "content": f"{relationship.source_entity_id}->{relationship.target_entity_id}:{relationship.relationship_type}",
                "source_reference": relationship.source_reference,
                "confidence_points": relationship.confidence,
                "attributes": {"relationship_type": relationship.relationship_type, "graph_version": graph.graph_version},
            }
        )
    return AtlasProviderResult(
        provider_id=NEXUS_PROVIDER_ID,
        data={
            "records": records,
            "metadata": {
                "graph_version": graph.graph_version,
                "graph_fingerprint": graph.graph_fingerprint,
                "entity_count": len(graph.entities),
                "relationship_count": len(graph.relationships),
            },
            "classification": "internal",
        },
    )


def _default_entities() -> tuple[NexusEntity, ...]:
    return (
        NexusEntity(entity_id="ctv_one", entity_type="platform", label="CTV ONE", source_reference="nexus:ctv_one"),
        NexusEntity(entity_id="atlas", entity_type="system", label="Atlas", source_reference="nexus:atlas"),
        NexusEntity(entity_id="forge", entity_type="system", label="Forge", source_reference="nexus:forge"),
    )


def _default_relationships() -> tuple[NexusRelationship, ...]:
    return (
        NexusRelationship(relationship_id="rel_atlas_ctv", source_entity_id="atlas", target_entity_id="ctv_one", relationship_type="supports", source_reference="nexus:rel_atlas_ctv"),
        NexusRelationship(relationship_id="rel_forge_atlas", source_entity_id="forge", target_entity_id="atlas", relationship_type="adapts", source_reference="nexus:rel_forge_atlas"),
    )

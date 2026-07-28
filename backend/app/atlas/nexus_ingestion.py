from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from enum import StrEnum
from threading import Lock
from time import perf_counter
from typing import Protocol

from pydantic import Field, field_validator, model_validator

from app.atlas.canonical import AtlasCanonicalModel, FrozenJson, fingerprint
from app.atlas.providers.nexus import (
    NexusBuildReport,
    NexusEntityInput,
    NexusGraphBuilder,
    NexusGraphImportBatch,
    NexusGraphInfrastructureError,
    NexusGraphSchemaVersion,
    NexusGraphSnapshot,
    NexusGraphStore,
    NexusRelationshipInput,
    normalize_nexus_identifier,
)
from app.core.config import settings


class NexusImportMode(StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"
    VALIDATE_ONLY = "validate_only"


class NexusSourceRecordType(StrEnum):
    DOCUMENT = "document"
    MEDIA_ASSET = "media_asset"
    PROJECT = "project"
    EVENT = "event"
    PERSON_REFERENCE = "person_reference"
    ORGANIZATION = "organization"
    STORAGE_LOCATION = "storage_location"
    POLICY = "policy"
    TRANSCRIPT = "transcript"
    ARCHIVE_COLLECTION = "archive_collection"
    MEDIA_TYPE = "media_type"
    OTHER = "other"


class NexusDeletionReason(StrEnum):
    SOURCE_DELETED = "source_deleted"
    SOURCE_ARCHIVED = "source_archived"
    SOURCE_REPLACED = "source_replaced"
    SOURCE_WITHDRAWN = "source_withdrawn"
    OTHER = "other"


class NexusConnectorHealthState(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class NexusIngestionErrorCategory(StrEnum):
    CONNECTOR_DISABLED = "connector_disabled"
    CONNECTOR_UNAVAILABLE = "connector_unavailable"
    CONNECTOR_TIMEOUT = "connector_timeout"
    CONNECTOR_FAILURE = "connector_failure"
    CONNECTOR_SCHEMA_MISMATCH = "connector_schema_mismatch"
    INVALID_CONNECTOR_RESULT = "invalid_connector_result"
    SOURCE_FINGERPRINT_MISMATCH = "source_fingerprint_mismatch"
    SOURCE_LIMIT_EXCEEDED = "source_limit_exceeded"
    INCREMENTAL_STATE_UNAVAILABLE = "incremental_state_unavailable"
    IMPORT_BATCH_INVALID = "import_batch_invalid"
    REQUIRED_CONNECTOR_FAILED = "required_connector_failed"
    CANDIDATE_BUILD_FAILED = "candidate_build_failed"
    CANDIDATE_VALIDATION_FAILED = "candidate_validation_failed"
    PUBLICATION_FAILED = "publication_failed"
    ROLLBACK_UNAVAILABLE = "rollback_unavailable"
    INGESTION_DISABLED = "ingestion_disabled"


class NexusPublicationStatus(StrEnum):
    PUBLISHED = "published"
    VALIDATED = "validated"
    NO_CHANGE = "no_change"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class NexusIngestionError(RuntimeError):
    def __init__(self, category: NexusIngestionErrorCategory) -> None:
        super().__init__(category.value)
        self.category = category


class NexusConnectorBudget(AtlasCanonicalModel):
    maximum_records: int = Field(default=100, ge=0, le=100_000)
    timeout_seconds: float = Field(default=5.0, ge=0.001, le=300.0)


class NexusConnectorDefinition(AtlasCanonicalModel):
    connector_id: str
    connector_version: str
    source_type: str
    supported_schema_version: NexusGraphSchemaVersion = Field(default_factory=NexusGraphSchemaVersion.current)
    default_budget: NexusConnectorBudget = Field(default_factory=NexusConnectorBudget)
    maximum_records: int = Field(default=1_000, ge=0, le=100_000)
    supports_full_import: bool = True
    supports_incremental_import: bool = True
    supports_deletions: bool = True
    enabled_by_default: bool = False

    @field_validator("connector_id", "connector_version", "source_type")
    @classmethod
    def normalize_safe_identifier(cls, value: str) -> str:
        return normalize_nexus_identifier(value)

    @field_validator("supported_schema_version", mode="before")
    @classmethod
    def parse_schema(cls, value) -> NexusGraphSchemaVersion:
        return NexusGraphSchemaVersion.parse(value)


class NexusConnectorCursor(AtlasCanonicalModel):
    source_version: str | None = None
    position_fingerprint: str = Field(default="", max_length=64)


class NexusConnectorRequest(AtlasCanonicalModel):
    import_mode: NexusImportMode
    previous_source_version: str | None = None
    previous_source_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    cursor: NexusConnectorCursor | None = None
    maximum_records: int = Field(default=100, ge=0, le=100_000)
    deadline: float | None = None
    requested_graph_schema: NexusGraphSchemaVersion = Field(default_factory=NexusGraphSchemaVersion.current)

    @field_validator("requested_graph_schema", mode="before")
    @classmethod
    def parse_schema(cls, value) -> NexusGraphSchemaVersion:
        return NexusGraphSchemaVersion.parse(value)


class NexusNormalizedSourceRecord(AtlasCanonicalModel):
    source_record_id: str
    source_type: str
    record_type: NexusSourceRecordType
    label: str = Field(min_length=1, max_length=256)
    external_key: str
    parent_references: tuple[str, ...] = Field(default=(), max_length=32)
    related_references: tuple[str, ...] = Field(default=(), max_length=64)
    metadata: FrozenJson = Field(default_factory=FrozenJson)
    content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_version: str
    is_deleted: bool = False

    @field_validator("source_record_id", "source_type", "external_key")
    @classmethod
    def normalize_identifiers(cls, value: str) -> str:
        return normalize_nexus_identifier(value)

    @field_validator("metadata", mode="before")
    @classmethod
    def freeze_metadata(cls, value) -> FrozenJson:
        return value if isinstance(value, FrozenJson) else FrozenJson(value)

    @model_validator(mode="after")
    def validate_metadata_size(self) -> "NexusNormalizedSourceRecord":
        if len(self.metadata._json.encode("utf-8")) > settings.ctv_one_nexus_max_metadata_bytes:
            raise NexusIngestionError(NexusIngestionErrorCategory.SOURCE_LIMIT_EXCEEDED)
        return self


class NexusSourceTombstone(AtlasCanonicalModel):
    connector_id: str
    source_record_id: str
    source_version: str
    reason: NexusDeletionReason = NexusDeletionReason.SOURCE_DELETED

    @field_validator("connector_id", "source_record_id")
    @classmethod
    def normalize_identifiers(cls, value: str) -> str:
        return normalize_nexus_identifier(value)

    @property
    def tombstone_fingerprint(self) -> str:
        return self.deterministic_fingerprint()


class NexusConnectorWarning(AtlasCanonicalModel):
    category: str
    count: int = Field(default=1, ge=1)


class NexusConnectorFailure(AtlasCanonicalModel):
    category: NexusIngestionErrorCategory


class NexusConnectorMetrics(AtlasCanonicalModel):
    records_collected: int = Field(default=0, ge=0)
    tombstones_collected: int = Field(default=0, ge=0)
    collection_latency_ms: float = Field(default=0.0, ge=0.0)


class NexusConnectorResult(AtlasCanonicalModel):
    definition: NexusConnectorDefinition
    source_version: str
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    records: tuple[NexusNormalizedSourceRecord, ...] = Field(default=(), max_length=100_000)
    tombstones: tuple[NexusSourceTombstone, ...] = Field(default=(), max_length=100_000)
    cursor: NexusConnectorCursor | None = None
    complete: bool = True
    warnings: tuple[NexusConnectorWarning, ...] = ()
    metrics: NexusConnectorMetrics = Field(default_factory=NexusConnectorMetrics)

    @property
    def result_fingerprint(self) -> str:
        return self.deterministic_fingerprint()

    @model_validator(mode="after")
    def validate_bounds(self) -> "NexusConnectorResult":
        if len(self.records) > self.definition.maximum_records:
            raise NexusIngestionError(NexusIngestionErrorCategory.SOURCE_LIMIT_EXCEEDED)
        return self


def compute_source_fingerprint(
    definition: NexusConnectorDefinition,
    records: tuple[NexusNormalizedSourceRecord, ...],
    tombstones: tuple[NexusSourceTombstone, ...] = (),
) -> str:
    payload = {
        "connector_id": definition.connector_id,
        "connector_version": definition.connector_version,
        "source_type": definition.source_type,
        "records": [record.canonical_dict() for record in sorted(records, key=lambda item: item.deterministic_fingerprint())],
        "tombstones": [tombstone.canonical_dict() for tombstone in sorted(tombstones, key=lambda item: item.tombstone_fingerprint)],
    }
    return fingerprint(payload)


class NexusConnectorHealth(AtlasCanonicalModel):
    connector_id: str
    state: NexusConnectorHealthState
    schema_compatible: bool = True
    recent_success_count: int = Field(default=0, ge=0)
    recent_failure_count: int = Field(default=0, ge=0)


class NexusConnector(Protocol):
    def definition(self) -> NexusConnectorDefinition: ...

    def initialize(self) -> None: ...

    def health(self) -> NexusConnectorHealth: ...

    def collect(self, request: NexusConnectorRequest) -> NexusConnectorResult: ...

    def diagnostics(self) -> dict[str, object]: ...


class NexusConnectorRegistry:
    def __init__(self, connectors: tuple[NexusConnector, ...] = ()) -> None:
        self._connectors: dict[str, NexusConnector] = {}
        for connector in connectors:
            self.register(connector)

    def register(self, connector: NexusConnector) -> None:
        connector_id = connector.definition().connector_id
        if connector_id in self._connectors:
            raise NexusIngestionError(NexusIngestionErrorCategory.INVALID_CONNECTOR_RESULT)
        self._connectors[connector_id] = connector

    def connectors(self, *, enabled_ids: tuple[str, ...] | None = None) -> tuple[NexusConnector, ...]:
        selected = tuple(
            connector
            for connector in self._connectors.values()
            if enabled_ids is None or connector.definition().connector_id in set(enabled_ids)
        )
        return tuple(sorted(selected, key=lambda item: (item.definition().connector_id, item.definition().connector_version, item.definition().source_type)))

    def readiness(self) -> tuple[NexusConnectorHealth, ...]:
        return tuple(connector.health() for connector in self.connectors())


class NexusPlanConnector(AtlasCanonicalModel):
    connector_id: str
    connector_version: str
    source_type: str
    required: bool = True
    maximum_records: int
    timeout_seconds: float
    previous_source_version: str | None = None
    previous_source_fingerprint: str | None = None
    unchanged: bool = False


class NexusIngestionPlan(AtlasCanonicalModel):
    import_mode: NexusImportMode
    connectors: tuple[NexusPlanConnector, ...]
    required_graph_schema: NexusGraphSchemaVersion = Field(default_factory=NexusGraphSchemaVersion.current)
    publish_required: bool = True

    @property
    def plan_fingerprint(self) -> str:
        return self.deterministic_fingerprint()


class NexusIngestionPlanner:
    def create_plan(
        self,
        registry: NexusConnectorRegistry,
        *,
        import_mode: NexusImportMode,
        enabled_connector_ids: tuple[str, ...],
        optional_connector_ids: tuple[str, ...] = (),
        previous_sources: dict[str, tuple[str, str]] | None = None,
    ) -> NexusIngestionPlan:
        if len(enabled_connector_ids) > settings.ctv_one_nexus_max_connectors_per_run:
            raise NexusIngestionError(NexusIngestionErrorCategory.SOURCE_LIMIT_EXCEEDED)
        previous_sources = previous_sources or {}
        plan_items: list[NexusPlanConnector] = []
        for connector in registry.connectors(enabled_ids=enabled_connector_ids):
            definition = connector.definition()
            if import_mode == NexusImportMode.FULL and not definition.supports_full_import:
                continue
            if import_mode == NexusImportMode.INCREMENTAL and not definition.supports_incremental_import:
                continue
            previous = previous_sources.get(definition.connector_id)
            maximum_records = min(definition.maximum_records, settings.ctv_one_nexus_max_records_per_connector)
            plan_items.append(
                NexusPlanConnector(
                    connector_id=definition.connector_id,
                    connector_version=definition.connector_version,
                    source_type=definition.source_type,
                    required=definition.connector_id not in set(optional_connector_ids),
                    maximum_records=maximum_records,
                    timeout_seconds=min(definition.default_budget.timeout_seconds, settings.ctv_one_nexus_connector_timeout_seconds),
                    previous_source_version=previous[0] if previous else None,
                    previous_source_fingerprint=previous[1] if previous else None,
                )
            )
        return NexusIngestionPlan(
            import_mode=import_mode,
            connectors=tuple(sorted(plan_items, key=lambda item: (item.connector_id, item.connector_version, item.source_type))),
            publish_required=import_mode != NexusImportMode.VALIDATE_ONLY,
        )


class NexusConnectorRunOutcome(AtlasCanonicalModel):
    connector_id: str
    required: bool
    status: NexusPublicationStatus
    failure_category: NexusIngestionErrorCategory | None = None
    records_processed: int = 0
    tombstones_processed: int = 0
    source_fingerprint_prefix: str | None = None
    duration_ms: float = 0.0


class NexusIngestionOutcome(AtlasCanonicalModel):
    operation_id: str
    plan_fingerprint: str
    import_mode: NexusImportMode
    connector_outcomes: tuple[NexusConnectorRunOutcome, ...]
    candidate_graph_fingerprint: str | None = None
    previous_graph_fingerprint: str | None = None
    publication_status: NexusPublicationStatus
    no_change: bool = False
    validation_status: NexusPublicationStatus = NexusPublicationStatus.VALIDATED
    failure_category: NexusIngestionErrorCategory | None = None
    entity_count: int = 0
    relationship_count: int = 0
    duration_ms: float = 0.0
    build_duration_ms: float = 0.0
    operational_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def safe_history_record(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id,
            "connector_ids": [item.connector_id for item in self.connector_outcomes],
            "mode": self.import_mode.value,
            "status": self.publication_status.value,
            "record_count": sum(item.records_processed for item in self.connector_outcomes),
            "tombstone_count": sum(item.tombstones_processed for item in self.connector_outcomes),
            "failure_category": self.failure_category.value if self.failure_category else None,
            "duration_ms": round(self.duration_ms, 3),
            "graph_fingerprint_prefix": (self.candidate_graph_fingerprint or "")[:12],
            "operational_timestamp": self.operational_timestamp.isoformat(),
        }


class NexusIngestionHistory:
    def __init__(self, capacity: int | None = None) -> None:
        self._capacity = capacity or settings.ctv_one_nexus_import_history_capacity
        self._items: deque[NexusIngestionOutcome] = deque(maxlen=max(1, self._capacity))
        self._lock = Lock()

    def append(self, outcome: NexusIngestionOutcome) -> None:
        with self._lock:
            self._items.append(outcome)

    def items(self) -> tuple[NexusIngestionOutcome, ...]:
        with self._lock:
            return tuple(self._items)

    def safe_records(self) -> tuple[dict[str, object], ...]:
        return tuple(item.safe_history_record for item in self.items())


class NexusIngestionMetrics:
    def __init__(self) -> None:
        self.run_count = 0
        self.successful_run_count = 0
        self.failed_run_count = 0
        self.validate_only_count = 0
        self.no_change_count = 0
        self.publication_count = 0
        self.rollback_count = 0
        self.total_latency_ms = 0.0
        self.total_build_latency_ms = 0.0
        self.connector_collection_count: dict[str, int] = {}
        self.connector_success_count: dict[str, int] = {}
        self.connector_failure_count: dict[str, int] = {}
        self.connector_timeout_count: dict[str, int] = {}
        self.connector_total_latency_ms: dict[str, float] = {}
        self.records_collected = 0
        self.tombstones_collected = 0
        self.source_unchanged_count = 0
        self.last_candidate_snapshot_bytes = 0
        self.active_snapshot_bytes = 0

    def record(self, outcome: NexusIngestionOutcome, *, snapshot: NexusGraphSnapshot | None) -> None:
        self.run_count += 1
        self.total_latency_ms += outcome.duration_ms
        self.total_build_latency_ms += outcome.build_duration_ms
        if outcome.import_mode == NexusImportMode.VALIDATE_ONLY:
            self.validate_only_count += 1
        if outcome.no_change:
            self.no_change_count += 1
        if outcome.publication_status == NexusPublicationStatus.PUBLISHED:
            self.successful_run_count += 1
            self.publication_count += 1
        elif outcome.publication_status == NexusPublicationStatus.ROLLED_BACK:
            self.rollback_count += 1
        elif outcome.publication_status == NexusPublicationStatus.FAILED:
            self.failed_run_count += 1
        for item in outcome.connector_outcomes:
            self.connector_collection_count[item.connector_id] = self.connector_collection_count.get(item.connector_id, 0) + 1
            self.connector_total_latency_ms[item.connector_id] = self.connector_total_latency_ms.get(item.connector_id, 0.0) + item.duration_ms
            self.records_collected += item.records_processed
            self.tombstones_collected += item.tombstones_processed
            if item.status == NexusPublicationStatus.FAILED:
                self.connector_failure_count[item.connector_id] = self.connector_failure_count.get(item.connector_id, 0) + 1
                if item.failure_category == NexusIngestionErrorCategory.CONNECTOR_TIMEOUT:
                    self.connector_timeout_count[item.connector_id] = self.connector_timeout_count.get(item.connector_id, 0) + 1
            else:
                self.connector_success_count[item.connector_id] = self.connector_success_count.get(item.connector_id, 0) + 1
        self.last_candidate_snapshot_bytes = len(snapshot.canonical_bytes()) if snapshot is not None else 0
        self.active_snapshot_bytes = self.last_candidate_snapshot_bytes

    def diagnostics(self) -> dict[str, object]:
        average_latency = self.total_latency_ms / self.run_count if self.run_count else 0.0
        average_build = self.total_build_latency_ms / self.run_count if self.run_count else 0.0
        return {
            "ingestion_run_count": self.run_count,
            "successful_run_count": self.successful_run_count,
            "failed_run_count": self.failed_run_count,
            "validate_only_count": self.validate_only_count,
            "no_change_count": self.no_change_count,
            "publication_count": self.publication_count,
            "rollback_count": self.rollback_count,
            "average_ingestion_latency_ms": round(average_latency, 3),
            "average_graph_build_latency_ms": round(average_build, 3),
            "records_collected": self.records_collected,
            "tombstones_collected": self.tombstones_collected,
            "candidate_snapshot_bytes": self.last_candidate_snapshot_bytes,
            "active_snapshot_bytes": self.active_snapshot_bytes,
        }


class NexusGraphMapper(Protocol):
    def build_batch(
        self,
        definition: NexusConnectorDefinition,
        source_version: str,
        source_fingerprint: str,
        records: tuple[NexusNormalizedSourceRecord, ...],
    ) -> NexusGraphImportBatch: ...


def _ownership(connector_id: str, record: NexusNormalizedSourceRecord, source_fingerprint: str) -> FrozenJson:
    return FrozenJson(
        {
            "owner_connector_id": connector_id,
            "source_record_id": record.source_record_id,
            "source_version": record.source_version,
            "source_fingerprint": source_fingerprint,
            "record_type": record.record_type.value,
        }
    )


class CompanyBrainGraphMapper:
    _metadata_keys = {"document_type", "ingestion_status", "safe_source_reference", "version", "file_type", "page_count", "category"}

    def build_batch(
        self,
        definition: NexusConnectorDefinition,
        source_version: str,
        source_fingerprint: str,
        records: tuple[NexusNormalizedSourceRecord, ...],
    ) -> NexusGraphImportBatch:
        entities: list[NexusEntityInput] = []
        relationships: list[NexusRelationshipInput] = []
        for record in sorted(records, key=lambda item: item.source_record_id):
            metadata = record.metadata.to_python()
            allowed = {key: metadata[key] for key in sorted(metadata) if key in self._metadata_keys}
            if record.record_type == NexusSourceRecordType.DOCUMENT:
                entities.append(
                    NexusEntityInput(
                        namespace="cb",
                        entity_type="knowledge_document",
                        external_key=record.external_key,
                        label=record.label,
                        source_reference=f"company_brain:{record.source_record_id}",
                        metadata=_ownership(definition.connector_id, record, source_fingerprint),
                    )
                )
                if category := allowed.get("category"):
                    category_key = normalize_nexus_identifier(str(category))
                    entities.append(
                        NexusEntityInput(
                            namespace="cb",
                            entity_type="knowledge_collection",
                            external_key=category_key,
                            label=category_key,
                            source_reference=f"company_brain_collection:{category_key}",
                            metadata=FrozenJson({"category": category_key}),
                        )
                    )
                    relationships.append(
                        NexusRelationshipInput(
                            namespace="cb",
                            source_namespace="cb",
                            source_entity_type="knowledge_document",
                            source_external_key=record.external_key,
                            relationship_type="document_in_collection",
                            target_namespace="cb",
                            target_entity_type="knowledge_collection",
                            target_external_key=category_key,
                            source_reference=f"company_brain:{record.source_record_id}",
                            metadata=FrozenJson(allowed),
                        )
                    )
        return NexusGraphImportBatch(
            source_id=definition.connector_id,
            source_version=source_version,
            source_fingerprint=source_fingerprint,
            entities=tuple(entities),
            relationships=tuple(relationships),
            import_metadata=FrozenJson({"connector_id": definition.connector_id, "record_count": len(records)}),
        )


class ArchiveMetadataGraphMapper:
    _metadata_keys = {"media_type", "extension", "duration", "resolution", "file_size", "checksum", "archive_status", "storage_reference"}

    def build_batch(
        self,
        definition: NexusConnectorDefinition,
        source_version: str,
        source_fingerprint: str,
        records: tuple[NexusNormalizedSourceRecord, ...],
    ) -> NexusGraphImportBatch:
        entities: list[NexusEntityInput] = []
        relationships: list[NexusRelationshipInput] = []
        for record in sorted(records, key=lambda item: item.source_record_id):
            metadata = record.metadata.to_python()
            allowed = {key: metadata[key] for key in sorted(metadata) if key in self._metadata_keys}
            entities.append(
                NexusEntityInput(
                    namespace="am",
                    entity_type=record.record_type.value,
                    external_key=record.external_key,
                    label=record.label,
                    source_reference=f"archive:{record.source_record_id}",
                    metadata=_ownership(definition.connector_id, record, source_fingerprint),
                )
            )
            for related_id in sorted(record.related_references):
                entities.append(
                    NexusEntityInput(
                        namespace="am",
                        entity_type="project",
                        external_key=related_id,
                        label=related_id,
                        source_reference=f"archive_project:{related_id}",
                        metadata=FrozenJson({"source": definition.connector_id}),
                    )
                )
                relationships.append(
                    NexusRelationshipInput(
                        namespace="am",
                        source_namespace="am",
                        source_entity_type=record.record_type.value,
                        source_external_key=record.external_key,
                        relationship_type="asset_related_to",
                        target_namespace="am",
                        target_entity_type="project",
                        target_external_key=related_id,
                        source_reference=f"archive:{record.source_record_id}",
                        metadata=FrozenJson(allowed),
                    )
                )
        return NexusGraphImportBatch(
            source_id=definition.connector_id,
            source_version=source_version,
            source_fingerprint=source_fingerprint,
            entities=tuple(entities),
            relationships=tuple(relationships),
            import_metadata=FrozenJson({"connector_id": definition.connector_id, "record_count": len(records)}),
        )


class CompanyBrainDocumentRecord(AtlasCanonicalModel):
    document_id: str
    filename: str
    content_type: str
    category: str
    status: str
    page_count: int = 0
    chunk_count: int = 0
    updated_version: str


class CompanyBrainRepository(Protocol):
    def list_documents(self, maximum_records: int) -> tuple[CompanyBrainDocumentRecord, ...]: ...


class CompanyBrainNexusConnector:
    def __init__(self, repository: CompanyBrainRepository, *, enabled: bool | None = None) -> None:
        self.repository = repository
        self.enabled = settings.ctv_one_nexus_company_brain_connector_enabled if enabled is None else enabled
        self.initialized = False

    def definition(self) -> NexusConnectorDefinition:
        return NexusConnectorDefinition(
            connector_id="company_brain",
            connector_version="1.0",
            source_type="company_brain",
            maximum_records=settings.ctv_one_nexus_max_records_per_connector,
            enabled_by_default=False,
        )

    def initialize(self) -> None:
        self.initialized = True

    def health(self) -> NexusConnectorHealth:
        state = NexusConnectorHealthState.READY if self.enabled and self.initialized else NexusConnectorHealthState.DISABLED
        return NexusConnectorHealth(connector_id=self.definition().connector_id, state=state)

    def collect(self, request: NexusConnectorRequest) -> NexusConnectorResult:
        if not self.enabled:
            raise NexusIngestionError(NexusIngestionErrorCategory.CONNECTOR_DISABLED)
        if request.requested_graph_schema.major != self.definition().supported_schema_version.major:
            raise NexusIngestionError(NexusIngestionErrorCategory.CONNECTOR_SCHEMA_MISMATCH)
        started = perf_counter()
        documents = self.repository.list_documents(min(request.maximum_records, self.definition().maximum_records))
        records = tuple(self._record(document) for document in sorted(documents, key=lambda item: item.document_id))
        source_fingerprint = compute_source_fingerprint(self.definition(), records)
        return NexusConnectorResult(
            definition=self.definition(),
            source_version=fingerprint(tuple(sorted(document.updated_version for document in documents))),
            source_fingerprint=source_fingerprint,
            records=records,
            complete=len(documents) <= request.maximum_records,
            metrics=NexusConnectorMetrics(records_collected=len(records), collection_latency_ms=(perf_counter() - started) * 1000),
        )

    def diagnostics(self) -> dict[str, object]:
        return {"connector_id": self.definition().connector_id, "enabled": self.enabled, "initialized": self.initialized}

    def _record(self, document: CompanyBrainDocumentRecord) -> NexusNormalizedSourceRecord:
        extension = document.filename.rsplit(".", 1)[-1].lower() if "." in document.filename else "unknown"
        safe_label = normalize_nexus_identifier(document.document_id)
        return NexusNormalizedSourceRecord(
            source_record_id=document.document_id,
            source_type="company_brain",
            record_type=NexusSourceRecordType.DOCUMENT,
            label=safe_label,
            external_key=document.document_id,
            metadata=FrozenJson(
                {
                    "document_type": document.content_type,
                    "ingestion_status": document.status,
                    "safe_source_reference": f"company_brain:{normalize_nexus_identifier(document.document_id)}",
                    "file_type": extension,
                    "page_count": document.page_count,
                    "category": document.category,
                }
            ),
            content_fingerprint=fingerprint(
                {
                    "document_id": document.document_id,
                    "content_type": document.content_type,
                    "category": document.category,
                    "status": document.status,
                    "page_count": document.page_count,
                    "chunk_count": document.chunk_count,
                    "updated_version": document.updated_version,
                }
            ),
            source_version=document.updated_version,
            is_deleted=document.status in {"deleted", "archived"},
        )


class ArchiveMetadataRecord(AtlasCanonicalModel):
    asset_id: str
    record_type: NexusSourceRecordType = NexusSourceRecordType.MEDIA_ASSET
    media_type: str
    extension: str
    file_size: int = 0
    checksum: str | None = None
    storage_reference: str
    project_id: str | None = None
    archive_status: str = "active"
    updated_version: str


class ArchiveMetadataRepository(Protocol):
    def list_assets(self, maximum_records: int) -> tuple[ArchiveMetadataRecord, ...]: ...


class ArchiveMetadataNexusConnector:
    def __init__(self, repository: ArchiveMetadataRepository, *, enabled: bool | None = None) -> None:
        self.repository = repository
        self.enabled = settings.ctv_one_nexus_archive_connector_enabled if enabled is None else enabled
        self.initialized = False

    def definition(self) -> NexusConnectorDefinition:
        return NexusConnectorDefinition(
            connector_id="archive_metadata",
            connector_version="1.0",
            source_type="archive_metadata",
            maximum_records=settings.ctv_one_nexus_max_records_per_connector,
            enabled_by_default=False,
        )

    def initialize(self) -> None:
        self.initialized = True

    def health(self) -> NexusConnectorHealth:
        state = NexusConnectorHealthState.READY if self.enabled and self.initialized else NexusConnectorHealthState.DISABLED
        return NexusConnectorHealth(connector_id=self.definition().connector_id, state=state)

    def collect(self, request: NexusConnectorRequest) -> NexusConnectorResult:
        if not self.enabled:
            raise NexusIngestionError(NexusIngestionErrorCategory.CONNECTOR_DISABLED)
        started = perf_counter()
        assets = self.repository.list_assets(min(request.maximum_records, self.definition().maximum_records))
        records = tuple(self._record(asset) for asset in sorted(assets, key=lambda item: item.asset_id))
        source_fingerprint = compute_source_fingerprint(self.definition(), records)
        return NexusConnectorResult(
            definition=self.definition(),
            source_version=fingerprint(tuple(sorted(asset.updated_version for asset in assets))),
            source_fingerprint=source_fingerprint,
            records=records,
            complete=len(assets) <= request.maximum_records,
            metrics=NexusConnectorMetrics(records_collected=len(records), collection_latency_ms=(perf_counter() - started) * 1000),
        )

    def diagnostics(self) -> dict[str, object]:
        return {"connector_id": self.definition().connector_id, "enabled": self.enabled, "initialized": self.initialized}

    def _record(self, asset: ArchiveMetadataRecord) -> NexusNormalizedSourceRecord:
        safe_storage = normalize_nexus_identifier(asset.storage_reference)
        related = (normalize_nexus_identifier(asset.project_id),) if asset.project_id else ()
        return NexusNormalizedSourceRecord(
            source_record_id=asset.asset_id,
            source_type="archive_metadata",
            record_type=asset.record_type,
            label=normalize_nexus_identifier(asset.asset_id),
            external_key=asset.asset_id,
            related_references=related,
            metadata=FrozenJson(
                {
                    "media_type": asset.media_type,
                    "extension": asset.extension,
                    "file_size": asset.file_size,
                    "checksum": asset.checksum,
                    "storage_reference": safe_storage,
                    "archive_status": asset.archive_status,
                }
            ),
            content_fingerprint=fingerprint(asset),
            source_version=asset.updated_version,
            is_deleted=asset.archive_status in {"deleted", "withdrawn"},
        )


class NexusIngestionService:
    def __init__(
        self,
        *,
        graph_store: NexusGraphStore,
        registry: NexusConnectorRegistry,
        mappers: dict[str, NexusGraphMapper] | None = None,
        history: NexusIngestionHistory | None = None,
        metrics: NexusIngestionMetrics | None = None,
    ) -> None:
        self.graph_store = graph_store
        self.registry = registry
        self.mappers = mappers or {
            "company_brain": CompanyBrainGraphMapper(),
            "archive_metadata": ArchiveMetadataGraphMapper(),
        }
        self.history = history or NexusIngestionHistory()
        self.metrics = metrics or NexusIngestionMetrics()
        self._lock = Lock()
        self._source_records: dict[str, dict[str, NexusNormalizedSourceRecord]] = {}
        self._source_versions: dict[str, tuple[str, str]] = {}
        self._previous_snapshot: NexusGraphSnapshot | None = None

    def execute(self, plan: NexusIngestionPlan) -> NexusIngestionOutcome:
        started = perf_counter()
        if not settings.ctv_one_nexus_ingestion_enabled:
            outcome = self._failed_outcome(plan, NexusIngestionErrorCategory.INGESTION_DISABLED, started, ())
            self._record_outcome(outcome, None)
            return outcome
        with self._lock:
            return self._execute_locked(plan, started)

    def rollback_previous_snapshot(self) -> NexusIngestionOutcome:
        started = perf_counter()
        with self._lock:
            if self._previous_snapshot is None:
                outcome = NexusIngestionOutcome(
                    operation_id=fingerprint({"rollback": "unavailable"}),
                    plan_fingerprint=fingerprint({"rollback": "manual"}),
                    import_mode=NexusImportMode.VALIDATE_ONLY,
                    connector_outcomes=(),
                    publication_status=NexusPublicationStatus.FAILED,
                    failure_category=NexusIngestionErrorCategory.ROLLBACK_UNAVAILABLE,
                    duration_ms=(perf_counter() - started) * 1000,
                )
                self._record_outcome(outcome, None)
                return outcome
            current = self.graph_store.snapshot
            self.graph_store.replace_snapshot(self._previous_snapshot)
            self._previous_snapshot = current if settings.ctv_one_nexus_previous_snapshot_retained else None
            snapshot = self.graph_store.snapshot
            outcome = NexusIngestionOutcome(
                operation_id=fingerprint({"rollback": snapshot.graph_fingerprint if snapshot else ""}),
                plan_fingerprint=fingerprint({"rollback": "manual"}),
                import_mode=NexusImportMode.VALIDATE_ONLY,
                connector_outcomes=(),
                candidate_graph_fingerprint=snapshot.graph_fingerprint if snapshot else None,
                publication_status=NexusPublicationStatus.ROLLED_BACK,
                entity_count=snapshot.entity_count if snapshot else 0,
                relationship_count=snapshot.relationship_count if snapshot else 0,
                duration_ms=(perf_counter() - started) * 1000,
            )
            self._record_outcome(outcome, snapshot)
            return outcome

    def diagnostics(self) -> dict[str, object]:
        snapshot = self.graph_store.snapshot
        last = self.history.items()[-1] if self.history.items() else None
        return {
            "ingestion_enabled": settings.ctv_one_nexus_ingestion_enabled,
            "last_run_status": last.publication_status.value if last else None,
            "last_run_mode": last.import_mode.value if last else None,
            "last_successful_publication_time": self._last_successful_publication_time(),
            "active_graph_version": snapshot.graph_version if snapshot else None,
            "active_graph_fingerprint_prefix": snapshot.graph_fingerprint[:12] if snapshot else None,
            "previous_snapshot_available": self._previous_snapshot is not None,
            "connector_count": len(self.registry.connectors()),
            "enabled_connector_ids": [item.definition().connector_id for item in self.registry.connectors()],
            "connector_health_states": {item.connector_id: item.state.value for item in self.registry.readiness()},
            "aggregate_records_processed": self.metrics.records_collected,
            "aggregate_tombstones_processed": self.metrics.tombstones_collected,
            "successful_imports": self.metrics.successful_run_count,
            "failed_imports": self.metrics.failed_run_count,
            "no_change_imports": self.metrics.no_change_count,
            "average_run_latency_ms": self.metrics.diagnostics()["average_ingestion_latency_ms"],
            "bounded_history_size": len(self.history.items()),
        }

    def _execute_locked(self, plan: NexusIngestionPlan, started: float) -> NexusIngestionOutcome:
        connector_outcomes: list[NexusConnectorRunOutcome] = []
        staged_records = {key: dict(value) for key, value in self._source_records.items()}
        source_versions = dict(self._source_versions)
        try:
            for plan_connector in plan.connectors:
                connector = next((item for item in self.registry.connectors() if item.definition().connector_id == plan_connector.connector_id), None)
                if connector is None:
                    if plan_connector.required:
                        raise NexusIngestionError(NexusIngestionErrorCategory.REQUIRED_CONNECTOR_FAILED)
                    continue
                result, run_outcome = self._collect_connector(connector, plan_connector, plan)
                connector_outcomes.append(run_outcome)
                if run_outcome.status == NexusPublicationStatus.FAILED:
                    if plan_connector.required:
                        raise NexusIngestionError(NexusIngestionErrorCategory.REQUIRED_CONNECTOR_FAILED)
                    continue
                if plan.import_mode in {NexusImportMode.FULL, NexusImportMode.VALIDATE_ONLY}:
                    staged_records[plan_connector.connector_id] = {record.source_record_id: record for record in result.records if not record.is_deleted}
                elif plan.import_mode == NexusImportMode.INCREMENTAL:
                    if plan_connector.connector_id not in staged_records:
                        raise NexusIngestionError(NexusIngestionErrorCategory.INCREMENTAL_STATE_UNAVAILABLE)
                    for tombstone in sorted(result.tombstones, key=lambda item: item.tombstone_fingerprint):
                        staged_records[plan_connector.connector_id].pop(tombstone.source_record_id, None)
                    for record in sorted(result.records, key=lambda item: item.source_record_id):
                        if record.is_deleted:
                            staged_records[plan_connector.connector_id].pop(record.source_record_id, None)
                        else:
                            staged_records[plan_connector.connector_id][record.source_record_id] = record
                source_versions[plan_connector.connector_id] = (result.source_version, result.source_fingerprint)
            candidate, report, build_ms, batches = self._build_candidate(staged_records, source_versions)
            active = self.graph_store.snapshot
            no_change = active is not None and active.graph_fingerprint == candidate.graph_fingerprint
            status = NexusPublicationStatus.VALIDATED
            if no_change:
                status = NexusPublicationStatus.NO_CHANGE
            elif plan.import_mode != NexusImportMode.VALIDATE_ONLY and plan.publish_required:
                self._previous_snapshot = active if settings.ctv_one_nexus_previous_snapshot_retained else None
                self.graph_store.replace_snapshot(candidate)
                self._source_records = staged_records
                self._source_versions = source_versions
                status = NexusPublicationStatus.PUBLISHED
            operation_id = fingerprint({"plan": plan.plan_fingerprint, "candidate": candidate.graph_fingerprint, "status": status.value})
            outcome = NexusIngestionOutcome(
                operation_id=operation_id,
                plan_fingerprint=plan.plan_fingerprint,
                import_mode=plan.import_mode,
                connector_outcomes=tuple(sorted(connector_outcomes, key=lambda item: item.connector_id)),
                candidate_graph_fingerprint=candidate.graph_fingerprint,
                previous_graph_fingerprint=active.graph_fingerprint if active else None,
                publication_status=status,
                no_change=no_change,
                entity_count=candidate.entity_count,
                relationship_count=candidate.relationship_count,
                duration_ms=(perf_counter() - started) * 1000,
                build_duration_ms=build_ms,
            )
            self._record_outcome(outcome, candidate)
            return outcome
        except NexusIngestionError as exc:
            outcome = self._failed_outcome(plan, exc.category, started, tuple(connector_outcomes))
            self._record_outcome(outcome, self.graph_store.snapshot)
            return outcome
        except NexusGraphInfrastructureError:
            outcome = self._failed_outcome(plan, NexusIngestionErrorCategory.CANDIDATE_BUILD_FAILED, started, tuple(connector_outcomes))
            self._record_outcome(outcome, self.graph_store.snapshot)
            return outcome

    def _collect_connector(
        self,
        connector: NexusConnector,
        plan_connector: NexusPlanConnector,
        plan: NexusIngestionPlan,
    ) -> tuple[NexusConnectorResult, NexusConnectorRunOutcome]:
        started = perf_counter()
        request = NexusConnectorRequest(
            import_mode=plan.import_mode,
            previous_source_version=plan_connector.previous_source_version,
            previous_source_fingerprint=plan_connector.previous_source_fingerprint,
            maximum_records=plan_connector.maximum_records,
            deadline=perf_counter() + plan_connector.timeout_seconds,
            requested_graph_schema=plan.required_graph_schema,
        )
        try:
            result = connector.collect(request)
            duration = (perf_counter() - started) * 1000
            if duration > plan_connector.timeout_seconds * 1000:
                raise NexusIngestionError(NexusIngestionErrorCategory.CONNECTOR_TIMEOUT)
            return result, NexusConnectorRunOutcome(
                connector_id=plan_connector.connector_id,
                required=plan_connector.required,
                status=NexusPublicationStatus.VALIDATED,
                records_processed=len(result.records),
                tombstones_processed=len(result.tombstones),
                source_fingerprint_prefix=result.source_fingerprint[:12],
                duration_ms=duration,
            )
        except NexusIngestionError as exc:
            return NexusConnectorResult(
                definition=connector.definition(),
                source_version="failed",
                source_fingerprint=fingerprint({"failed": connector.definition().connector_id}),
            ), NexusConnectorRunOutcome(
                connector_id=plan_connector.connector_id,
                required=plan_connector.required,
                status=NexusPublicationStatus.FAILED,
                failure_category=exc.category,
                duration_ms=(perf_counter() - started) * 1000,
            )
        except Exception:
            return NexusConnectorResult(
                definition=connector.definition(),
                source_version="failed",
                source_fingerprint=fingerprint({"failed": connector.definition().connector_id}),
            ), NexusConnectorRunOutcome(
                connector_id=plan_connector.connector_id,
                required=plan_connector.required,
                status=NexusPublicationStatus.FAILED,
                failure_category=NexusIngestionErrorCategory.CONNECTOR_FAILURE,
                duration_ms=(perf_counter() - started) * 1000,
            )

    def _build_candidate(
        self,
        staged_records: dict[str, dict[str, NexusNormalizedSourceRecord]],
        source_versions: dict[str, tuple[str, str]],
    ) -> tuple[NexusGraphSnapshot, NexusBuildReport, float, tuple[NexusGraphImportBatch, ...]]:
        started = perf_counter()
        batches: list[NexusGraphImportBatch] = []
        for connector_id in sorted(staged_records):
            connector = next((item for item in self.registry.connectors() if item.definition().connector_id == connector_id), None)
            if connector is None:
                continue
            mapper = self.mappers.get(connector.definition().source_type)
            if mapper is None:
                raise NexusIngestionError(NexusIngestionErrorCategory.IMPORT_BATCH_INVALID)
            source_version, source_fingerprint = source_versions.get(connector_id, ("1.0", fingerprint({})))
            batches.append(
                mapper.build_batch(
                    connector.definition(),
                    source_version,
                    source_fingerprint,
                    tuple(staged_records[connector_id][key] for key in sorted(staged_records[connector_id])),
                )
            )
        builder = NexusGraphBuilder()
        for batch in sorted(batches, key=lambda item: item.batch_fingerprint):
            builder.add_batch(batch)
        snapshot, report = builder.build()
        return snapshot, report, (perf_counter() - started) * 1000, tuple(batches)

    def _failed_outcome(
        self,
        plan: NexusIngestionPlan,
        category: NexusIngestionErrorCategory,
        started: float,
        connector_outcomes: tuple[NexusConnectorRunOutcome, ...],
    ) -> NexusIngestionOutcome:
        return NexusIngestionOutcome(
            operation_id=fingerprint({"plan": plan.plan_fingerprint, "failure": category.value}),
            plan_fingerprint=plan.plan_fingerprint,
            import_mode=plan.import_mode,
            connector_outcomes=connector_outcomes,
            previous_graph_fingerprint=self.graph_store.snapshot.graph_fingerprint if self.graph_store.snapshot else None,
            publication_status=NexusPublicationStatus.FAILED,
            validation_status=NexusPublicationStatus.FAILED,
            failure_category=category,
            duration_ms=(perf_counter() - started) * 1000,
        )

    def _record_outcome(self, outcome: NexusIngestionOutcome, snapshot: NexusGraphSnapshot | None) -> None:
        self.history.append(outcome)
        self.metrics.record(outcome, snapshot=snapshot)

    def _last_successful_publication_time(self) -> str | None:
        for item in reversed(self.history.items()):
            if item.publication_status == NexusPublicationStatus.PUBLISHED:
                return item.operational_timestamp.isoformat()
        return None

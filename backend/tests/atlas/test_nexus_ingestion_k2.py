from __future__ import annotations

import asyncio
import itertools

import pytest

from app.atlas.nexus_ingestion import (
    ArchiveMetadataGraphMapper,
    ArchiveMetadataNexusConnector,
    ArchiveMetadataRecord,
    CompanyBrainDocumentRecord,
    CompanyBrainGraphMapper,
    CompanyBrainNexusConnector,
    NexusConnectorDefinition,
    NexusConnectorHealthState,
    NexusConnectorRegistry,
    NexusConnectorRequest,
    NexusConnectorResult,
    NexusDeletionReason,
    NexusGraphMapper,
    NexusImportMode,
    NexusIngestionError,
    NexusIngestionErrorCategory,
    NexusIngestionHistory,
    NexusIngestionPlan,
    NexusIngestionPlanner,
    NexusIngestionService,
    NexusNormalizedSourceRecord,
    NexusPlanConnector,
    NexusPublicationStatus,
    NexusSourceRecordType,
    NexusSourceTombstone,
    compute_source_fingerprint,
)
from app.atlas.providers.nexus import NexusGraphStore, NexusQuery
from app.core.config import settings


@pytest.fixture(autouse=True)
def nexus_ingestion_settings(monkeypatch):
    monkeypatch.setattr(settings, "ctv_one_nexus_ingestion_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_nexus_company_brain_connector_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_nexus_archive_connector_enabled", True)
    monkeypatch.setattr(settings, "ctv_one_nexus_max_entities", 200_000)
    monkeypatch.setattr(settings, "ctv_one_nexus_max_relationships", 200_000)
    monkeypatch.setattr(settings, "ctv_one_nexus_max_import_batches", 16)
    monkeypatch.setattr(settings, "ctv_one_nexus_max_snapshot_bytes", 100_000_000)
    monkeypatch.setattr(settings, "ctv_one_nexus_max_relationships_per_entity", 200_000)
    monkeypatch.setattr(settings, "ctv_one_nexus_max_records_per_connector", 100_000)


class CompanyRepo:
    def __init__(self, records: tuple[CompanyBrainDocumentRecord, ...]) -> None:
        self.records = records

    def list_documents(self, maximum_records: int) -> tuple[CompanyBrainDocumentRecord, ...]:
        return self.records[:maximum_records]


class ArchiveRepo:
    def __init__(self, records: tuple[ArchiveMetadataRecord, ...]) -> None:
        self.records = records

    def list_assets(self, maximum_records: int) -> tuple[ArchiveMetadataRecord, ...]:
        return self.records[:maximum_records]


class FailingConnector:
    def __init__(self, connector_id: str = "failing_source") -> None:
        self._definition = NexusConnectorDefinition(
            connector_id=connector_id,
            connector_version="1.0",
            source_type=connector_id,
        )

    def definition(self) -> NexusConnectorDefinition:
        return self._definition

    def initialize(self) -> None:
        return None

    def health(self):
        from app.atlas.nexus_ingestion import NexusConnectorHealth

        return NexusConnectorHealth(connector_id=self._definition.connector_id, state=NexusConnectorHealthState.UNAVAILABLE)

    def collect(self, request: NexusConnectorRequest) -> NexusConnectorResult:
        raise NexusIngestionError(NexusIngestionErrorCategory.CONNECTOR_FAILURE)

    def diagnostics(self) -> dict[str, object]:
        return {"connector_id": self._definition.connector_id}


class TombstoneConnector:
    def __init__(self) -> None:
        self._definition = NexusConnectorDefinition(
            connector_id="company_brain",
            connector_version="1.0",
            source_type="company_brain",
        )
        self.records: tuple[NexusNormalizedSourceRecord, ...] = ()
        self.tombstones: tuple[NexusSourceTombstone, ...] = ()

    def definition(self) -> NexusConnectorDefinition:
        return self._definition

    def initialize(self) -> None:
        return None

    def health(self):
        from app.atlas.nexus_ingestion import NexusConnectorHealth

        return NexusConnectorHealth(connector_id="company_brain", state=NexusConnectorHealthState.READY)

    def collect(self, request: NexusConnectorRequest) -> NexusConnectorResult:
        source_fingerprint = compute_source_fingerprint(self._definition, self.records, self.tombstones)
        return NexusConnectorResult(
            definition=self._definition,
            source_version="v2",
            source_fingerprint=source_fingerprint,
            records=self.records,
            tombstones=self.tombstones,
        )

    def diagnostics(self) -> dict[str, object]:
        return {"connector_id": "company_brain"}


def company_docs(order: tuple[str, ...] = ("doc_1", "doc_2")) -> tuple[CompanyBrainDocumentRecord, ...]:
    values = {
        "doc_1": CompanyBrainDocumentRecord(
            document_id="doc_1",
            filename="Private Manual.pdf",
            content_type="application/pdf",
            category="policy",
            status="ready",
            page_count=3,
            chunk_count=7,
            updated_version="v1",
        ),
        "doc_2": CompanyBrainDocumentRecord(
            document_id="doc_2",
            filename="Transcript Body.txt",
            content_type="text/plain",
            category="production",
            status="ready",
            page_count=1,
            chunk_count=2,
            updated_version="v1",
        ),
    }
    return tuple(values[item] for item in order)


def archive_assets(order: tuple[str, ...] = ("asset_1", "asset_2")) -> tuple[ArchiveMetadataRecord, ...]:
    values = {
        "asset_1": ArchiveMetadataRecord(
            asset_id="asset_1",
            media_type="video",
            extension="mov",
            file_size=100,
            checksum="abc",
            storage_reference="nas_archive_a",
            project_id="project_1",
            updated_version="v1",
        ),
        "asset_2": ArchiveMetadataRecord(
            asset_id="asset_2",
            media_type="audio",
            extension="wav",
            file_size=50,
            checksum="def",
            storage_reference="nas_archive_b",
            project_id="project_1",
            updated_version="v1",
        ),
    }
    return tuple(values[item] for item in order)


def service_for(*connectors) -> NexusIngestionService:
    for connector in connectors:
        connector.initialize()
    return NexusIngestionService(
        graph_store=NexusGraphStore(),
        registry=NexusConnectorRegistry(tuple(connectors)),
    )


def plan_for(registry: NexusConnectorRegistry, *connector_ids: str, mode: NexusImportMode = NexusImportMode.FULL, optional: tuple[str, ...] = ()) -> NexusIngestionPlan:
    return NexusIngestionPlanner().create_plan(
        registry,
        import_mode=mode,
        enabled_connector_ids=tuple(connector_ids),
        optional_connector_ids=optional,
    )


def test_connector_contracts_are_immutable_bounded_and_fingerprinted() -> None:
    definition = NexusConnectorDefinition(connector_id="company_brain", connector_version="1.0", source_type="company_brain")
    with pytest.raises(Exception):
        definition.connector_id = "changed"  # type: ignore[misc]
    record = CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True)._record(company_docs()[0])
    assert record.label == "doc_1"
    assert "Private Manual" not in record.canonical_json()
    assert compute_source_fingerprint(definition, (record,)) == compute_source_fingerprint(definition, (record,))


def test_registry_rejects_duplicates_and_orders_canonically() -> None:
    company = CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True)
    archive = ArchiveMetadataNexusConnector(ArchiveRepo(archive_assets()), enabled=True)
    registry = NexusConnectorRegistry((archive, company))
    assert [item.definition().connector_id for item in registry.connectors()] == ["archive_metadata", "company_brain"]
    with pytest.raises(NexusIngestionError):
        registry.register(CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True))


def test_connector_health_reports_disabled_without_source_details() -> None:
    connector = CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=False)
    assert connector.health().state == NexusConnectorHealthState.DISABLED
    connector.initialize()
    assert connector.diagnostics() == {"connector_id": "company_brain", "enabled": False, "initialized": True}


def test_source_fingerprint_is_record_order_independent_and_includes_deletions() -> None:
    connector = CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True)
    definition = connector.definition()
    records_a = tuple(connector._record(item) for item in company_docs(("doc_1", "doc_2")))
    records_b = tuple(connector._record(item) for item in company_docs(("doc_2", "doc_1")))
    tombstone = NexusSourceTombstone(connector_id="company_brain", source_record_id="doc_2", source_version="v2")
    assert compute_source_fingerprint(definition, records_a) == compute_source_fingerprint(definition, records_b)
    assert compute_source_fingerprint(definition, records_a) != compute_source_fingerprint(definition, records_a, (tombstone,))


def test_planner_is_deterministic_and_preserves_optional_required_distinction() -> None:
    registry = NexusConnectorRegistry(
        (
            ArchiveMetadataNexusConnector(ArchiveRepo(archive_assets()), enabled=True),
            CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True),
        )
    )
    first = plan_for(registry, "company_brain", "archive_metadata", optional=("archive_metadata",))
    second = plan_for(registry, "archive_metadata", "company_brain", optional=("archive_metadata",))
    assert first.plan_fingerprint == second.plan_fingerprint
    assert [item.connector_id for item in first.connectors] == ["archive_metadata", "company_brain"]
    assert [item.required for item in first.connectors] == [False, True]


def test_full_import_builds_complete_candidate_and_publishes_atomically() -> None:
    company = CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True)
    archive = ArchiveMetadataNexusConnector(ArchiveRepo(archive_assets()), enabled=True)
    service = service_for(company, archive)
    outcome = service.execute(plan_for(service.registry, "company_brain", "archive_metadata"))
    assert outcome.publication_status == NexusPublicationStatus.PUBLISHED
    assert outcome.entity_count == service.graph_store.snapshot.entity_count
    assert service.graph_store.snapshot.entity_count >= 7
    assert service.diagnostics()["previous_snapshot_available"] is True


def test_validate_only_runs_validation_without_publication() -> None:
    service = service_for(CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True))
    before = service.graph_store.snapshot.graph_fingerprint
    outcome = service.execute(plan_for(service.registry, "company_brain", mode=NexusImportMode.VALIDATE_ONLY))
    assert outcome.publication_status == NexusPublicationStatus.VALIDATED
    assert service.graph_store.snapshot.graph_fingerprint == before


def test_no_change_import_avoids_unnecessary_publication() -> None:
    service = service_for(CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True))
    plan = plan_for(service.registry, "company_brain")
    assert service.execute(plan).publication_status == NexusPublicationStatus.PUBLISHED
    second = service.execute(plan)
    assert second.publication_status == NexusPublicationStatus.NO_CHANGE
    assert second.no_change is True


def test_incremental_tombstone_rebuilds_complete_snapshot() -> None:
    connector = TombstoneConnector()
    connector.records = tuple(CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True)._record(item) for item in company_docs())
    service = service_for(connector)
    assert service.execute(plan_for(service.registry, "company_brain")).entity_count == 4
    connector.records = ()
    connector.tombstones = (NexusSourceTombstone(connector_id="company_brain", source_record_id="doc_2", source_version="v2", reason=NexusDeletionReason.SOURCE_DELETED),)
    outcome = service.execute(plan_for(service.registry, "company_brain", mode=NexusImportMode.INCREMENTAL))
    assert outcome.publication_status == NexusPublicationStatus.PUBLISHED
    assert outcome.entity_count == 2


def test_incremental_without_retained_state_fails_safely() -> None:
    connector = TombstoneConnector()
    service = service_for(connector)
    before = service.graph_store.snapshot.graph_fingerprint
    outcome = service.execute(plan_for(service.registry, "company_brain", mode=NexusImportMode.INCREMENTAL))
    assert outcome.publication_status == NexusPublicationStatus.FAILED
    assert outcome.failure_category == NexusIngestionErrorCategory.INCREMENTAL_STATE_UNAVAILABLE
    assert service.graph_store.snapshot.graph_fingerprint == before


def test_required_connector_failure_blocks_publication_but_optional_failure_does_not() -> None:
    company = CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True)
    failing = FailingConnector()
    required_service = service_for(company, failing)
    before = required_service.graph_store.snapshot.graph_fingerprint
    failed = required_service.execute(plan_for(required_service.registry, "company_brain", "failing_source"))
    assert failed.publication_status == NexusPublicationStatus.FAILED
    assert required_service.graph_store.snapshot.graph_fingerprint == before

    optional_service = service_for(company, failing)
    published = optional_service.execute(plan_for(optional_service.registry, "company_brain", "failing_source", optional=("failing_source",)))
    assert published.publication_status == NexusPublicationStatus.PUBLISHED


def test_rollback_restores_immediately_previous_snapshot() -> None:
    service = service_for(CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True))
    original = service.graph_store.snapshot.graph_fingerprint
    service.execute(plan_for(service.registry, "company_brain"))
    assert service.graph_store.snapshot.graph_fingerprint != original
    rollback = service.rollback_previous_snapshot()
    assert rollback.publication_status == NexusPublicationStatus.ROLLED_BACK
    assert service.graph_store.snapshot.graph_fingerprint == original


def test_import_history_is_bounded_and_content_free() -> None:
    history = NexusIngestionHistory(capacity=2)
    service = NexusIngestionService(
        graph_store=NexusGraphStore(),
        registry=NexusConnectorRegistry((CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True),)),
        history=history,
    )
    for connector in service.registry.connectors():
        connector.initialize()
    plan = plan_for(service.registry, "company_brain")
    for _ in range(3):
        service.execute(plan)
    records = history.safe_records()
    assert len(records) == 2
    assert "Private Manual" not in str(records)
    assert "Transcript Body" not in str(records)


def test_company_brain_mapper_omits_full_content_and_unsupported_relationships() -> None:
    connector = CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True)
    result = connector.collect(NexusConnectorRequest(import_mode=NexusImportMode.FULL, maximum_records=10))
    batch = CompanyBrainGraphMapper().build_batch(connector.definition(), result.source_version, result.source_fingerprint, result.records)
    assert len(batch.entities) == 4
    assert {item.relationship_type for item in batch.relationships} == {"document_in_collection"}
    assert "Private Manual" not in batch.canonical_json()


def test_archive_mapper_uses_safe_storage_ids_without_filesystem_access() -> None:
    connector = ArchiveMetadataNexusConnector(ArchiveRepo(archive_assets()), enabled=True)
    result = connector.collect(NexusConnectorRequest(import_mode=NexusImportMode.FULL, maximum_records=10))
    batch = ArchiveMetadataGraphMapper().build_batch(connector.definition(), result.source_version, result.source_fingerprint, result.records)
    assert len(batch.relationships) == 2
    assert "\\\\" not in batch.canonical_json()
    assert ":/" not in batch.canonical_json()


def test_multisource_order_independence() -> None:
    results = []
    for order in (("company_brain", "archive_metadata"), ("archive_metadata", "company_brain")):
        company = CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True)
        archive = ArchiveMetadataNexusConnector(ArchiveRepo(archive_assets()), enabled=True)
        service = service_for(company, archive)
        outcome = service.execute(plan_for(service.registry, *order))
        results.append((outcome.candidate_graph_fingerprint, service.graph_store.snapshot.canonical_json()))
    assert results[0] == results[1]


def test_determinism_repeats_identical_ingestion_100_times() -> None:
    fingerprints = set()
    provider_results = set()
    for _ in range(100):
        service = service_for(CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True))
        plan = plan_for(service.registry, "company_brain")
        outcome = service.execute(plan)
        fingerprints.add((plan.plan_fingerprint, outcome.candidate_graph_fingerprint, service.graph_store.snapshot.canonical_json()))
        result = asyncio.run(service.graph_store.query(NexusQuery(query_type="neighborhood", max_entities=20, max_relationships=20, max_depth=1)))
        provider_results.add(result.graph_fingerprint)
    assert len(fingerprints) == 1
    assert len(provider_results) == 1


def test_permutations_are_identical_for_100_logical_orders() -> None:
    fingerprints = set()
    orders = list(itertools.islice(itertools.cycle(itertools.permutations(("doc_1", "doc_2"))), 100))
    for index, order in enumerate(orders):
        connector_order = ("company_brain", "archive_metadata") if index % 2 == 0 else ("archive_metadata", "company_brain")
        service = service_for(
            CompanyBrainNexusConnector(CompanyRepo(company_docs(order)), enabled=True),
            ArchiveMetadataNexusConnector(ArchiveRepo(archive_assets(("asset_2", "asset_1"))), enabled=True),
        )
        outcome = service.execute(plan_for(service.registry, *connector_order))
        fingerprints.add(outcome.candidate_graph_fingerprint)
    assert len(fingerprints) == 1


def test_concurrent_readers_observe_complete_old_or_new_snapshots_only() -> None:
    service = service_for(CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True))
    old = service.graph_store.snapshot.graph_fingerprint
    seen: set[str] = set()

    async def read_many() -> None:
        for _ in range(50):
            result = await service.graph_store.query(NexusQuery(query_type="neighborhood", max_entities=20, max_relationships=20, max_depth=1))
            seen.add(service.graph_store.snapshot.graph_fingerprint)
            assert result.entities

    async def run() -> None:
        task = asyncio.create_task(read_many())
        outcome = service.execute(plan_for(service.registry, "company_brain"))
        await task
        assert outcome.publication_status == NexusPublicationStatus.PUBLISHED

    asyncio.run(run())
    assert seen.issubset({old, service.graph_store.snapshot.graph_fingerprint})


def test_safe_diagnostics_metrics_and_history_do_not_leak_content() -> None:
    service = service_for(CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True))
    service.execute(plan_for(service.registry, "company_brain"))
    safe_text = str(service.diagnostics()) + str(service.metrics.diagnostics()) + str(service.history.safe_records())
    assert "Private Manual" not in safe_text
    assert "Transcript Body" not in safe_text
    assert "document body" not in safe_text.lower()
    assert "Traceback" not in safe_text


def test_ingestion_disabled_preserves_active_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ctv_one_nexus_ingestion_enabled", False)
    service = service_for(CompanyBrainNexusConnector(CompanyRepo(company_docs()), enabled=True))
    before = service.graph_store.snapshot.graph_fingerprint
    outcome = service.execute(plan_for(service.registry, "company_brain"))
    assert outcome.publication_status == NexusPublicationStatus.FAILED
    assert outcome.failure_category == NexusIngestionErrorCategory.INGESTION_DISABLED
    assert service.graph_store.snapshot.graph_fingerprint == before


def test_dependency_boundary_source_has_no_forbidden_imports() -> None:
    import inspect
    import app.atlas.nexus_ingestion as module

    source = inspect.getsource(module)
    assert "app.forge" not in source
    assert "app.services.ai_router" not in source
    assert "app.atlas.compiler" not in source
    assert "os.walk" not in source
    assert "smb" not in source.lower()


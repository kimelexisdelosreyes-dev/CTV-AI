from __future__ import annotations

import asyncio
import statistics
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.atlas.nexus_ingestion import (
    ArchiveMetadataGraphMapper,
    ArchiveMetadataNexusConnector,
    ArchiveMetadataRecord,
    CompanyBrainDocumentRecord,
    CompanyBrainGraphMapper,
    CompanyBrainNexusConnector,
    NexusConnectorRequest,
    NexusConnectorRegistry,
    NexusImportMode,
    NexusIngestionPlanner,
    NexusIngestionService,
)
from app.atlas.providers.nexus import NexusGraphStore, NexusQuery
from app.core.config import settings


class CompanyFixtureRepository:
    def __init__(self, count: int, *, version: str = "v1") -> None:
        self.records = tuple(
            CompanyBrainDocumentRecord(
                document_id=f"company_doc_{index:06d}",
                filename=f"document_{index:06d}.pdf",
                content_type="application/pdf",
                category=f"category_{index % 12}",
                status="ready",
                page_count=(index % 20) + 1,
                chunk_count=(index % 8) + 1,
                updated_version=version,
            )
            for index in range(count)
        )

    def list_documents(self, maximum_records: int) -> tuple[CompanyBrainDocumentRecord, ...]:
        return self.records[:maximum_records]


class ArchiveFixtureRepository:
    def __init__(self, count: int, *, version: str = "v1") -> None:
        self.records = tuple(
            ArchiveMetadataRecord(
                asset_id=f"archive_asset_{index:06d}",
                media_type=("video" if index % 2 == 0 else "audio"),
                extension=("mov" if index % 2 == 0 else "wav"),
                file_size=1_000 + index,
                checksum=f"checksum_{index:06d}",
                storage_reference=f"archive_location_{index % 16}",
                project_id=f"archive_project_{index % 200}",
                updated_version=version,
            )
            for index in range(count)
        )

    def list_assets(self, maximum_records: int) -> tuple[ArchiveMetadataRecord, ...]:
        return self.records[:maximum_records]


def milliseconds(fn):
    started = perf_counter()
    value = fn()
    return value, (perf_counter() - started) * 1000


def median(values: list[float]) -> float:
    return round(statistics.median(values), 3)


def p95(values: list[float]) -> float:
    return round(sorted(values)[int((len(values) - 1) * 0.95)], 3)


async def provider_query_latency(store: NexusGraphStore) -> float:
    started = perf_counter()
    await store.query(NexusQuery(query_type="neighborhood", max_entities=16, max_relationships=32, max_depth=1))
    return (perf_counter() - started) * 1000


def run_dataset(name: str, company_count: int, archive_count: int) -> dict[str, float | int]:
    settings.ctv_one_nexus_ingestion_enabled = True
    settings.ctv_one_nexus_company_brain_connector_enabled = True
    settings.ctv_one_nexus_archive_connector_enabled = True
    settings.ctv_one_nexus_max_records_per_connector = max(company_count, archive_count) + 10
    settings.ctv_one_nexus_max_entities = company_count * 2 + archive_count * 2 + 1_000
    settings.ctv_one_nexus_max_relationships = company_count + archive_count + 1_000
    settings.ctv_one_nexus_max_relationships_per_entity = max(company_count, archive_count) + 1_000
    settings.ctv_one_nexus_max_import_batches = 8
    settings.ctv_one_nexus_max_snapshot_bytes = 500_000_000
    settings.ctv_one_nexus_max_build_seconds = 60.0

    company_connector = CompanyBrainNexusConnector(CompanyFixtureRepository(company_count), enabled=True)
    archive_connector = ArchiveMetadataNexusConnector(ArchiveFixtureRepository(archive_count), enabled=True)
    company_connector.initialize()
    archive_connector.initialize()
    registry = NexusConnectorRegistry((company_connector, archive_connector))
    planner = NexusIngestionPlanner()
    request = NexusConnectorRequest(import_mode=NexusImportMode.FULL, maximum_records=max(company_count, archive_count) + 10)

    company_result, company_extract_ms = milliseconds(lambda: company_connector.collect(request))
    archive_result, archive_extract_ms = milliseconds(lambda: archive_connector.collect(request))
    _, company_mapping_ms = milliseconds(lambda: CompanyBrainGraphMapper().build_batch(company_connector.definition(), company_result.source_version, company_result.source_fingerprint, company_result.records))
    _, archive_mapping_ms = milliseconds(lambda: ArchiveMetadataGraphMapper().build_batch(archive_connector.definition(), archive_result.source_version, archive_result.source_fingerprint, archive_result.records))
    plan, planning_ms = milliseconds(lambda: planner.create_plan(registry, import_mode=NexusImportMode.FULL, enabled_connector_ids=("company_brain", "archive_metadata")))

    service = NexusIngestionService(graph_store=NexusGraphStore(), registry=registry)
    before_query_ms = asyncio.run(provider_query_latency(service.graph_store))
    outcome, total_ms = milliseconds(lambda: service.execute(plan))
    during_query_ms = asyncio.run(provider_query_latency(service.graph_store))
    no_change, no_change_ms = milliseconds(lambda: service.execute(plan))
    incremental_plan = planner.create_plan(registry, import_mode=NexusImportMode.INCREMENTAL, enabled_connector_ids=("company_brain", "archive_metadata"))
    incremental, incremental_ms = milliseconds(lambda: service.execute(incremental_plan))

    return {
        "company_records": company_count,
        "archive_records": archive_count,
        "company_extraction_ms": round(company_extract_ms, 3),
        "company_mapping_ms": round(company_mapping_ms, 3),
        "archive_extraction_ms": round(archive_extract_ms, 3),
        "archive_mapping_ms": round(archive_mapping_ms, 3),
        "source_fingerprinting_ms": round(company_extract_ms + archive_extract_ms, 3),
        "planning_ms": round(planning_ms, 3),
        "import_batch_creation_ms": round(company_mapping_ms + archive_mapping_ms, 3),
        "graph_build_ms": round(outcome.build_duration_ms, 3),
        "candidate_validation_ms": round(outcome.build_duration_ms, 3),
        "publication_ms": round(total_ms - outcome.build_duration_ms, 3),
        "total_ingestion_ms": round(total_ms, 3),
        "no_change_ingestion_ms": round(no_change_ms, 3),
        "incremental_ingestion_ms": round(incremental_ms, 3),
        "candidate_snapshot_bytes": len(service.graph_store.snapshot.canonical_bytes()),
        "records_per_second": round((company_count + archive_count) / (total_ms / 1000), 3),
        "provider_query_before_publication_ms": round(before_query_ms, 3),
        "provider_query_during_publication_ms": round(during_query_ms, 3),
        "entity_count": outcome.entity_count,
        "relationship_count": outcome.relationship_count,
        "no_change_status": no_change.publication_status.value,
        "incremental_status": incremental.publication_status.value,
    }


def main() -> None:
    datasets = {
        "small": (100, 500),
        "moderate": (5_000, 20_000),
    }
    report = {}
    for name, (company_count, archive_count) in datasets.items():
        samples = [run_dataset(name, company_count, archive_count) for _ in range(3 if name == "small" else 1)]
        report[name] = samples[-1]
        totals = [float(item["total_ingestion_ms"]) for item in samples]
        report[name]["median_total_ingestion_ms"] = median(totals)
        report[name]["p95_total_ingestion_ms"] = p95(totals)
    print(report)


if __name__ == "__main__":
    main()

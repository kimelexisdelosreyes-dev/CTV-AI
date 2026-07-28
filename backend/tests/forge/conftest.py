from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.atlas.context_package import (
    AtlasCitation,
    AtlasContextBudgetUsage,
    AtlasContextNode,
    AtlasContextPackage,
    AtlasEvidenceItem,
)
from app.atlas.compiler_contracts import AtlasManifestReference, AtlasProvenance


FIXED_TIME = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def make_package(*, node_count: int = 3, content_chars: int = 20) -> AtlasContextPackage:
    nodes = []
    evidence = []
    citations = []
    for index in range(node_count):
        provenance = AtlasProvenance(
            provider_id="fixture_provider",
            source_id=f"source-{index}",
            source_type="document",
            source_sequence=index,
            collected_at=FIXED_TIME,
            original_reference=f"reference-{index}",
            content_digest=HEX_A,
        )
        nodes.append(
            AtlasContextNode(
                node_id=f"node-{index}",
                node_type="document",
                label=f"Title {index}",
                provenance=provenance,
                classification="confidential" if index == 1 else "internal",
                score_points=900 - index,
                ordinal=index,
            )
        )
        evidence.append(
            AtlasEvidenceItem(
                evidence_id=f"evidence-{index}",
                provider_id="fixture_provider",
                excerpt=f"Content {index} " + ("x" * content_chars),
                classification="confidential" if index == 1 else "internal",
                citation_ids=(f"citation-{index}",),
                provenance=provenance,
                ordinal=index,
            )
        )
        citations.append(
            AtlasCitation(
                citation_id=f"citation-{index}",
                provider_id="fixture_provider",
                source_reference=f"reference-{index}",
                label=f"Citation {index}",
                provenance=provenance,
                classification="confidential" if index == 1 else "internal",
                ordinal=index,
            )
        )
    reference = AtlasManifestReference(
        manifest_digest=HEX_B,
        deterministic_digest=HEX_B,
        decision_count=node_count,
        stage_summary_count=1,
        selected_provider_count=1,
        excluded_provider_count=0,
        warning_count=0,
        conflict_count=0,
        budget_decision_count=node_count,
    )
    package = AtlasContextPackage(
        request_id="forge-fixture",
        created_at=FIXED_TIME,
        snapshot_fingerprint=HEX_C,
        compiler_policy_fingerprint=HEX_A,
        selected_provider_ids=("fixture_provider",),
        nodes=tuple(nodes),
        evidence=tuple(evidence),
        citations=tuple(citations),
        budgets=AtlasContextBudgetUsage(
            provider_count=1,
            node_count=node_count,
            evidence_count=node_count,
        ),
        manifest_reference=reference,
    )
    return package.model_copy(update={"package_fingerprint": package.computed_fingerprint()})


@pytest.fixture
def atlas_package() -> AtlasContextPackage:
    return make_package()

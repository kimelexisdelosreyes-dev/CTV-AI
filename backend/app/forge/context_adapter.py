from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from app.atlas.canonical import AtlasCanonicalModel
from app.atlas.constants import ATLAS_CONTEXT_PACKAGE_VERSION, ATLAS_MAX_CONTEXT_PACKAGE_BYTES
from app.atlas.context_package import AtlasCitation, AtlasContextNode, AtlasContextPackage
from app.atlas.compiler_contracts import AtlasClassification, AtlasManifestReference, AtlasProvenance
from app.core.config import settings
from app.forge.errors import ForgeContextError, ForgeContextErrorCategory


FORGE_CONTEXT_VERSION = "1.0"
FORGE_MAX_CONTEXT_BLOCKS = 128
FORGE_MAX_CONTEXT_TOKENS = 32_000


def estimate_text_tokens(value: str) -> int:
    """Stable local estimate; Forge does not invoke a tokenizer or model."""
    return max(1, (len(value.encode("utf-8")) + 3) // 4)


class ForgeContextBlock(AtlasCanonicalModel):
    node_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
    title: str = Field(min_length=1, max_length=512)
    content: str = Field(min_length=1, max_length=16_000)
    classification: AtlasClassification
    confidence: int = Field(ge=-1_000_000, le=1_000_000)
    citations: tuple[AtlasCitation, ...] = Field(default=(), max_length=256)
    provenance: AtlasProvenance | None = None
    ranking: int = Field(ge=1, le=FORGE_MAX_CONTEXT_BLOCKS)
    estimated_tokens: int = Field(ge=1, le=FORGE_MAX_CONTEXT_TOKENS)

    @field_validator("citations")
    @classmethod
    def preserve_citation_order(cls, value: tuple[AtlasCitation, ...]) -> tuple[AtlasCitation, ...]:
        ids = tuple(item.citation_id for item in value)
        if len(ids) != len(set(ids)):
            raise ValueError("Forge citation identifiers must be unique.")
        return value


class ForgeContextWindow(AtlasCanonicalModel):
    context_blocks: tuple[ForgeContextBlock, ...] = Field(default=(), max_length=FORGE_MAX_CONTEXT_BLOCKS)
    estimated_tokens: int = Field(ge=0, le=FORGE_MAX_CONTEXT_TOKENS)
    dropped_node_count: int = Field(ge=0, le=FORGE_MAX_CONTEXT_BLOCKS)
    retained_node_count: int = Field(ge=0, le=FORGE_MAX_CONTEXT_BLOCKS)
    package_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_reference: AtlasManifestReference
    atlas_package_version: str
    forge_context_version: str = FORGE_CONTEXT_VERSION

    @model_validator(mode="after")
    def verify_counts_and_order(self) -> "ForgeContextWindow":
        if self.retained_node_count != len(self.context_blocks):
            raise ValueError("Forge retained-node count is inconsistent.")
        if tuple(block.ranking for block in self.context_blocks) != tuple(
            range(1, len(self.context_blocks) + 1)
        ):
            raise ValueError("Forge context blocks must preserve Atlas order.")
        if self.estimated_tokens != sum(block.estimated_tokens for block in self.context_blocks):
            raise ValueError("Forge token estimate is inconsistent.")
        return self


class ForgeContextAdapter:
    def __init__(
        self,
        *,
        token_budget: int | None = None,
        atlas_enabled: bool | None = None,
        adapter_enabled: bool | None = None,
    ) -> None:
        budget = settings.ctv_one_forge_atlas_max_tokens if token_budget is None else token_budget
        if isinstance(budget, bool) or not 1 <= budget <= FORGE_MAX_CONTEXT_TOKENS:
            raise ValueError("Forge Atlas token budget is outside supported bounds.")
        self.token_budget = budget
        self.atlas_enabled = settings.ctv_one_atlas_enabled if atlas_enabled is None else atlas_enabled
        self.adapter_enabled = (
            settings.ctv_one_forge_atlas_enabled if adapter_enabled is None else adapter_enabled
        )

    @property
    def available(self) -> bool:
        return bool(self.atlas_enabled and self.adapter_enabled)

    def adapt(self, package: AtlasContextPackage) -> ForgeContextWindow:
        if not self.adapter_enabled:
            raise ForgeContextError(ForgeContextErrorCategory.ADAPTER_DISABLED)
        if not self.atlas_enabled:
            raise ForgeContextError(ForgeContextErrorCategory.ATLAS_DISABLED)
        self._validate_package(package)

        evidence_by_node = {
            f"node-{item.evidence_id.removeprefix('evidence-')}": item
            for item in package.evidence
        }
        citations_by_node: dict[str, tuple[AtlasCitation, ...]] = {}
        for node in package.nodes:
            evidence = evidence_by_node.get(node.node_id)
            explicit_ids = set(evidence.citation_ids if evidence else ())
            derived_id = f"citation-{node.node_id.removeprefix('node-')}"
            matched = tuple(
                citation
                for citation in package.citations
                if citation.citation_id in explicit_ids
                or citation.citation_id == derived_id
                or (node.provenance is not None and citation.provenance == node.provenance)
            )
            citations_by_node[node.node_id] = matched

        retained: list[ForgeContextBlock] = []
        used = 0
        for ranking, node in enumerate(package.nodes, 1):
            evidence = evidence_by_node.get(node.node_id)
            content = evidence.excerpt if evidence is not None else node.label
            estimate = estimate_text_tokens(content)
            if used + estimate > self.token_budget:
                break
            retained.append(
                ForgeContextBlock(
                    node_id=node.node_id,
                    title=node.label,
                    content=content,
                    classification=node.classification,
                    confidence=node.score_points,
                    citations=citations_by_node[node.node_id],
                    provenance=node.provenance,
                    ranking=ranking,
                    estimated_tokens=estimate,
                )
            )
            used += estimate

        assert package.manifest_reference is not None
        return ForgeContextWindow(
            context_blocks=tuple(retained),
            estimated_tokens=used,
            dropped_node_count=len(package.nodes) - len(retained),
            retained_node_count=len(retained),
            package_fingerprint=package.package_fingerprint,
            manifest_reference=package.manifest_reference,
            atlas_package_version=package.contract_version,
        )

    @staticmethod
    def _validate_package(package: AtlasContextPackage) -> None:
        if not isinstance(package, AtlasContextPackage):
            raise ForgeContextError(ForgeContextErrorCategory.PACKAGE_INVALID)
        if package.contract_version != ATLAS_CONTEXT_PACKAGE_VERSION:
            raise ForgeContextError(ForgeContextErrorCategory.PACKAGE_VERSION_UNSUPPORTED)
        if not package.package_fingerprint or package.package_fingerprint != package.computed_fingerprint():
            raise ForgeContextError(ForgeContextErrorCategory.PACKAGE_FINGERPRINT_INVALID)
        reference = package.manifest_reference
        if (
            reference is None
            or reference.manifest_digest != reference.deterministic_digest
            or reference.manifest_version != "1.0"
        ):
            raise ForgeContextError(ForgeContextErrorCategory.MANIFEST_REFERENCE_INVALID)
        if len(package.nodes) > FORGE_MAX_CONTEXT_BLOCKS or package.serialized_bytes() > ATLAS_MAX_CONTEXT_PACKAGE_BYTES:
            raise ForgeContextError(ForgeContextErrorCategory.PACKAGE_LIMIT_EXCEEDED)
        expected_order = tuple(sorted(package.nodes, key=lambda item: (item.ordinal, item.node_id)))
        if package.nodes != expected_order:
            raise ForgeContextError(ForgeContextErrorCategory.PACKAGE_INVALID)

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from pydantic import Field

from app.atlas.canonical import AtlasCanonicalModel, FrozenJson, canonical_json, fingerprint
from app.atlas.compiler_contracts import (
    AtlasAIRItemType, AtlasAIRPackage, AtlasAIRRecord, AtlasBudgetDecision, AtlasBudgetUsage,
    AtlasClassification, AtlasCompilationSnapshot, AtlasCompilerDecision, AtlasCompilerStage,
    AtlasCompilerStageSummary, AtlasConflict, AtlasContextManifest, AtlasProvenance,
    AtlasManifestReference, AtlasRankedContextItem, AtlasScoreBreakdown, AtlasSelectionAction,
)
from app.atlas.constants import ATLAS_COMPILER_CONTRACT_VERSION
from app.atlas.context_package import (
    AtlasCitation, AtlasContextBudgetUsage, AtlasContextNode, AtlasContextPackage,
    AtlasContextRelationship, AtlasContextWarning, AtlasEvidenceItem, AtlasOptimizationStats,
)
from app.atlas.errors import AtlasErrorCategory, AtlasRuntimeError


_CLASS_ORDER = {AtlasClassification.INTERNAL: 0, AtlasClassification.CONFIDENTIAL: 1, AtlasClassification.RESTRICTED: 2}


def _digest(*values: str) -> str:
    return hashlib.sha256("|".join(values).encode()).hexdigest()


def _more_restrictive(*values: AtlasClassification) -> AtlasClassification:
    return max(values, key=lambda value: _CLASS_ORDER[value])


def _decision(stage: AtlasCompilerStage, subject: str, action: AtlasSelectionAction, reason: str, provider: str | None = None, **extra) -> AtlasCompilerDecision:
    return AtlasCompilerDecision(
        decision_id=f"decision-{_digest(stage.value, subject, action.value, reason)[:24]}",
        stage=stage, subject_id=subject, provider_id=provider, action=action,
        reason_categories=(reason,), **extra,
    )


class AtlasCompilationResult(AtlasCanonicalModel):
    contract_version: str = ATLAS_COMPILER_CONTRACT_VERSION
    request_id: str
    snapshot_fingerprint: str
    air_package: AtlasAIRPackage
    graph_nodes: tuple[AtlasContextNode, ...]
    graph_relationships: tuple[AtlasContextRelationship, ...]
    ranked_items: tuple[AtlasRankedContextItem, ...]
    conflicts: tuple[AtlasConflict, ...]
    budget_usage: AtlasBudgetUsage
    budget_decisions: tuple[AtlasBudgetDecision, ...]
    manifest: AtlasContextManifest
    context_package: AtlasContextPackage
    warning_categories: tuple[str, ...] = ()
    status: str = "complete"
    deterministic_digest: str = ""

    @property
    def computed_digest(self) -> str:
        data = self.canonical_dict(); data["deterministic_digest"] = ""
        return fingerprint(data)


@dataclass(frozen=True)
class _Graph:
    nodes: tuple[AtlasContextNode, ...]
    relationships: tuple[AtlasContextRelationship, ...]
    source_by_node: dict[str, AtlasAIRRecord]


class AtlasContextCompiler:
    """Stateless compiler over an immutable supplied snapshot only."""

    def compile(self, snapshot: AtlasCompilationSnapshot) -> AtlasCompilationResult:
        self._validate(snapshot)
        inputs, select_decisions, warnings = self._select(snapshot)
        air, air_decisions = self._normalize(snapshot, inputs)
        graph, graph_decisions = self._graph(air)
        graph, duplicate_decisions = self._deduplicate(graph)
        conflicts, conflict_decisions = self._conflicts(graph)
        scores, score_decisions = self._score(snapshot, graph, conflicts)
        ranked, rank_decisions = self._rank(scores)
        selected, relationships, usage, budget_decisions, budget_stage = self._budget(snapshot, graph, ranked)
        decisions = select_decisions + air_decisions + graph_decisions + duplicate_decisions + conflict_decisions + score_decisions + rank_decisions + budget_stage
        manifest = self._manifest(snapshot, decisions, inputs, conflicts, usage, warnings)
        package = self._package(snapshot, inputs, selected, relationships, conflicts, usage, manifest, warnings, len(budget_decisions))
        result = AtlasCompilationResult(
            request_id=snapshot.request.request_id, snapshot_fingerprint=snapshot.snapshot_fingerprint,
            air_package=air, graph_nodes=selected, graph_relationships=relationships, ranked_items=ranked,
            conflicts=conflicts, budget_usage=usage, budget_decisions=budget_decisions, manifest=manifest,
            context_package=package, warning_categories=tuple(sorted(warnings)), status="partial" if warnings else "complete",
        )
        return result.model_copy(update={"deterministic_digest": result.computed_digest})

    def _validate(self, snapshot: AtlasCompilationSnapshot) -> None:
        if snapshot.contract_version.split(".")[0] != "1":
            raise AtlasRuntimeError(AtlasErrorCategory.COMPILER_CONTRACT_MISMATCH)
        if snapshot.snapshot_fingerprint != snapshot.deterministic_fingerprint():
            raise AtlasRuntimeError(AtlasErrorCategory.COMPILATION_SNAPSHOT_INVALID)
        supplied = {item.provider_id for item in snapshot.provider_inputs}
        required = {item.provider_id for item in snapshot.provider_selection_plan.entries if item.required and item.selected}
        if required - supplied and snapshot.compiler_policy.missing_required_provider_policy == "fail":
            raise AtlasRuntimeError(AtlasErrorCategory.COMPILATION_SNAPSHOT_INVALID)
        unavailable_required = {
            item.provider_id for item in snapshot.provider_inputs
            if item.provider_id in required and item.status == "unavailable"
        }
        if unavailable_required and snapshot.compiler_policy.missing_required_provider_policy == "fail":
            raise AtlasRuntimeError(AtlasErrorCategory.PROVIDER_INPUT_INVALID)

    def _select(self, snapshot):
        by_id = {item.provider_id: item for item in snapshot.provider_inputs}
        selected, decisions, warnings = [], [], []
        for entry in snapshot.provider_selection_plan.entries:
            item = by_id.get(entry.provider_id)
            if entry.selected and item is not None and item.status != "unavailable":
                selected.append(item); decisions.append(_decision(AtlasCompilerStage.VALIDATION, entry.provider_id, AtlasSelectionAction.SELECTED, "provider_selected", entry.provider_id))
            else:
                reason = "provider_missing" if item is None else "provider_excluded"
                decisions.append(_decision(AtlasCompilerStage.VALIDATION, entry.provider_id, AtlasSelectionAction.EXCLUDED, reason, entry.provider_id))
                if item is None and entry.selected:
                    warnings.append(reason)
                elif entry.required and snapshot.compiler_policy.missing_required_provider_policy == "warn":
                    warnings.append(reason)
        return tuple(sorted(selected, key=lambda item: (item.provider_id, item.source_sequence))), tuple(decisions), tuple(warnings)

    def _normalize(self, snapshot, inputs):
        records, decisions = [], []
        for source in inputs:
            for index, raw in enumerate(source.records):
                value = raw.to_python()
                if not isinstance(value, dict):
                    required = any(
                        entry.provider_id == source.provider_id and entry.required
                        for entry in snapshot.provider_selection_plan.entries
                    )
                    if required:
                        raise AtlasRuntimeError(AtlasErrorCategory.PROVIDER_INPUT_INVALID)
                    decisions.append(_decision(
                        AtlasCompilerStage.NORMALIZATION,
                        f"{source.provider_id}:{index}",
                        AtlasSelectionAction.EXCLUDED,
                        "provider_record_invalid",
                        source.provider_id,
                    ))
                    continue
                item_type = value.get("item_type", "record")
                if item_type not in {item.value for item in AtlasAIRItemType}: item_type = "record"
                title = str(value.get("title", value.get("id", f"record-{index}"))).strip()[:512]
                content = str(value.get("content", "")).strip()[:16_000]
                reference = str(value.get("source_reference", source.provenance.original_reference))
                air_id = f"air-{_digest(source.provider_id, reference, item_type, title, content)[:24]}"
                provenance = source.provenance.model_copy(update={"source_sequence": source.source_sequence})
                records.append(AtlasAIRRecord(air_id=air_id, provider_id=source.provider_id, source_reference=reference, item_type=item_type, normalized_title=title or "record", normalized_content=content, normalized_attributes=FrozenJson(value.get("attributes", {})), confidence_points=int(value.get("confidence_points", 0)), freshness_at=source.collected_at, priority_points=int(value.get("priority_points", 0)), classification=_more_restrictive(source.classification, source.provenance.classification), capability_ids=source.capabilities, provenance=provenance, ordinal=0))
                decisions.append(_decision(AtlasCompilerStage.NORMALIZATION, air_id, AtlasSelectionAction.SELECTED, "air_normalized", source.provider_id))
        return AtlasAIRPackage(records=tuple(records)), tuple(decisions)

    def _graph(self, air):
        nodes, relationships, mapping, decisions = [], [], {}, []
        for record in air.records:
            if record.item_type == AtlasAIRItemType.RELATION_CANDIDATE: continue
            node_id = f"node-{record.air_id[4:]}"; mapping[record.air_id] = node_id
            node = AtlasContextNode(node_id=node_id, node_type=record.item_type.value, label=record.normalized_title, attributes=record.normalized_attributes, provenance=record.provenance, classification=record.classification, score_points=0, ordinal=len(nodes))
            nodes.append(node); decisions.append(_decision(AtlasCompilerStage.GRAPH, node_id, AtlasSelectionAction.SELECTED, "node_created", record.provider_id))
        for record in air.records:
            if record.item_type != AtlasAIRItemType.RELATION_CANDIDATE: continue
            attrs = record.normalized_attributes.to_python(); source = mapping.get(str(attrs.get("source_air_id", ""))); target = mapping.get(str(attrs.get("target_air_id", "")))
            if source and target:
                relationships.append(AtlasContextRelationship(relationship_type=str(attrs.get("relationship_type", "related_to")), source_node_id=source, target_node_id=target, attributes=FrozenJson({}), provenance=record.provenance, classification=record.classification, score_points=0, ordinal=len(relationships)))
            else: decisions.append(_decision(AtlasCompilerStage.GRAPH, record.air_id, AtlasSelectionAction.EXCLUDED, "orphan_relationship", record.provider_id))
        unique_relationships = {
            (item.relationship_type, item.source_node_id, item.target_node_id, item.attributes._json): item
            for item in relationships
        }
        ordered_relationships = tuple(
            item.model_copy(update={"ordinal": ordinal})
            for ordinal, item in enumerate(unique_relationships[key] for key in sorted(unique_relationships))
        )
        return _Graph(tuple(nodes), ordered_relationships, {f"node-{r.air_id[4:]}": r for r in air.records if r.item_type != AtlasAIRItemType.RELATION_CANDIDATE}), tuple(decisions)

    def _deduplicate(self, graph):
        seen, keep, decisions = {}, [], []
        for node in graph.nodes:
            record = graph.source_by_node[node.node_id]
            key = (record.source_reference, record.normalized_content, record.normalized_attributes._json)
            if key in seen:
                survivor_index = seen[key]
                survivor = keep[survivor_index]
                keep[survivor_index] = survivor.model_copy(
                    update={"classification": _more_restrictive(survivor.classification, node.classification)}
                )
                decisions.append(_decision(AtlasCompilerStage.OPTIMIZATION, node.node_id, AtlasSelectionAction.EXCLUDED, "exact_duplicate", record.provider_id))
            else:
                seen[key] = len(keep); keep.append(node)
        ids = {node.node_id for node in keep}; rels = tuple(item for item in graph.relationships if item.source_node_id in ids and item.target_node_id in ids)
        return _Graph(tuple(keep), rels, {key: value for key, value in graph.source_by_node.items() if key in ids}), tuple(decisions)

    def _conflicts(self, graph):
        groups = defaultdict(list)
        for node in graph.nodes:
            attrs = node.attributes.to_python();
            if isinstance(attrs, dict) and "subject_key" in attrs and "predicate" in attrs and "value" in attrs: groups[(str(attrs["subject_key"]), str(attrs["predicate"]))].append(node)
        conflicts, decisions = [], []
        for (subject, predicate), nodes in sorted(groups.items()):
            values_by_json = {
                canonical_json(node.attributes.to_python()["value"]): node.attributes.to_python()["value"]
                for node in nodes
            }
            if len(values_by_json) > 1:
                items = tuple(sorted(node.node_id for node in nodes)); providers = tuple(sorted({node.provenance.provider_id for node in nodes if node.provenance}))
                provenance = tuple(sorted(
                    (node.provenance for node in nodes if node.provenance),
                    key=lambda item: (item.provider_id, item.source_id, item.source_sequence),
                ))
                conflict = AtlasConflict(conflict_id=f"conflict-{_digest(subject,predicate,*items)[:24]}", conflict_type="contradictory_fact", subject_key=subject, item_ids=items, provider_ids=providers, values=tuple(FrozenJson(values_by_json[key]) for key in sorted(values_by_json)), classification=_more_restrictive(*(node.classification for node in nodes)), provenance=provenance)
                conflicts.append(conflict); decisions.append(_decision(AtlasCompilerStage.GRAPH, conflict.conflict_id, AtlasSelectionAction.SELECTED, "conflict_preserved"))
        nodes_by_id = {node.node_id: node for node in graph.nodes}
        for relation in graph.relationships:
            if relation.relationship_type != "contradicts":
                continue
            pair = tuple(sorted((relation.source_node_id, relation.target_node_id)))
            if any(set(item.item_ids) == set(pair) for item in conflicts):
                continue
            pair_nodes = [nodes_by_id[item] for item in pair]
            conflict = AtlasConflict(
                conflict_id=f"conflict-{_digest('contradicts', *pair)[:24]}",
                conflict_type="explicit_contradiction",
                subject_key=pair[0],
                item_ids=pair,
                provider_ids=tuple(sorted({node.provenance.provider_id for node in pair_nodes if node.provenance})),
                values=tuple(FrozenJson(node.label) for node in pair_nodes),
                classification=_more_restrictive(*(node.classification for node in pair_nodes)),
                provenance=tuple(sorted((node.provenance for node in pair_nodes if node.provenance), key=lambda item: (item.provider_id, item.source_id))),
            )
            conflicts.append(conflict)
            decisions.append(_decision(AtlasCompilerStage.GRAPH, conflict.conflict_id, AtlasSelectionAction.SELECTED, "conflict_preserved"))
        return tuple(sorted(conflicts, key=lambda item: item.conflict_id)), tuple(sorted(decisions, key=lambda item: item.decision_id))

    def _score(self, snapshot, graph, conflicts):
        conflict_items = {item for conflict in conflicts for item in conflict.item_ids}; scores, decisions = [], []
        plan = {item.provider_id: item for item in snapshot.provider_selection_plan.entries}
        rel_count = defaultdict(int)
        for rel in graph.relationships: rel_count[rel.source_node_id] += 1; rel_count[rel.target_node_id] += 1
        for node in graph.nodes:
            record = graph.source_by_node[node.node_id]; priority = plan.get(record.provider_id).priority_points if record.provider_id in plan else 0
            intent = snapshot.compiler_policy.intent_match_points if (snapshot.request.intent in record.capability_ids or set(snapshot.request.requested_capabilities) & set(record.capability_ids)) else 0
            freshness = snapshot.compiler_policy.freshness_points if record.freshness_at and record.freshness_at >= snapshot.compilation_time else 0
            relationship = min(rel_count[node.node_id], 1) * snapshot.compiler_policy.relationship_bonus_points
            conflict = snapshot.compiler_policy.conflict_penalty_points if node.node_id in conflict_items else 0
            score = AtlasScoreBreakdown(provider_priority_points=priority, intent_match_points=intent, confidence_points=record.confidence_points, freshness_points=freshness, relationship_bonus_points=relationship, conflict_penalty_points=conflict, total_score_points=priority+intent+record.confidence_points+freshness+relationship-conflict)
            scores.append((node, record, score)); decisions.append(_decision(AtlasCompilerStage.RANKING, node.node_id, AtlasSelectionAction.SELECTED, "score_calculated", record.provider_id, score_points=score.total_score_points))
        return tuple(scores), tuple(decisions)

    def _rank(self, scores):
        ordered = sorted(scores, key=lambda item: (-item[2].total_score_points, -item[2].provider_priority_points, -item[2].confidence_points, -int(item[1].freshness_at.timestamp()) if item[1].freshness_at else 0, item[1].provider_id, item[0].node_id))
        ranks, decisions = [], []
        for index, (node, record, score) in enumerate(ordered, 1):
            ranks.append(AtlasRankedContextItem(item_id=node.node_id, provider_id=record.provider_id, total_score_points=score.total_score_points, provider_priority_points=score.provider_priority_points, confidence_points=score.confidence_points, freshness_sort_value=int(record.freshness_at.timestamp()) if record.freshness_at else 0, deterministic_rank=index, tie_break_values=(record.provider_id, node.node_id)))
            decisions.append(_decision(AtlasCompilerStage.RANKING, node.node_id, AtlasSelectionAction.SELECTED, "rank_assigned", record.provider_id, rank=index, score_points=score.total_score_points))
        return tuple(ranks), tuple(decisions)

    def _budget(self, snapshot, graph, ranked):
        rank_by_id = {item.item_id: item for item in ranked}; selected, decisions, stage = [], [], []; provider_counts = defaultdict(int); chars = 0
        for item in ranked:
            node = next(node for node in graph.nodes if node.node_id == item.item_id); content = graph.source_by_node[node.node_id].normalized_content
            allowed = (
                len(selected) < snapshot.compiler_policy.max_total_nodes
                and provider_counts[item.provider_id] < snapshot.compiler_policy.max_nodes_per_provider
                and len(content) <= snapshot.compiler_policy.max_content_chars_per_node
                and chars + len(content) <= snapshot.compiler_policy.max_total_serialized_bytes
            )
            before = len(selected); reason = "budget_selected" if allowed else "budget_exceeded"
            item_cost = 1 if allowed else 0
            decisions.append(AtlasBudgetDecision(item_id=node.node_id, provider_id=item.provider_id, selected=allowed, budget_category="nodes", limit=snapshot.compiler_policy.max_total_nodes, usage_before=before, item_cost=item_cost, usage_after=before+item_cost, reason_category=reason, deterministic_rank=item.deterministic_rank))
            stage.append(_decision(AtlasCompilerStage.BUDGET, node.node_id, AtlasSelectionAction.SELECTED if allowed else AtlasSelectionAction.EXCLUDED, reason, item.provider_id, rank=item.deterministic_rank))
            if allowed: selected.append(node); provider_counts[item.provider_id] += 1; chars += len(content)
        ids = {node.node_id for node in selected}; rels = tuple(rel for rel in graph.relationships if rel.source_node_id in ids and rel.target_node_id in ids)[:snapshot.compiler_policy.max_total_relationships]
        return tuple(selected), rels, AtlasBudgetUsage(nodes=len(selected), relationships=len(rels), text_characters=chars), tuple(decisions), tuple(stage)

    def _manifest(self, snapshot, decisions, inputs, conflicts, usage, warnings):
        selected = tuple(sorted(item.provider_id for item in inputs)); excluded = tuple(sorted(item.provider_id for item in snapshot.provider_selection_plan.entries if not item.selected))
        manifest = AtlasContextManifest(request_id=snapshot.request.request_id, snapshot_fingerprint=snapshot.snapshot_fingerprint, compiler_policy_fingerprint=snapshot.compiler_policy.policy_fingerprint, selected_provider_ids=selected, excluded_provider_ids=excluded, entries=tuple(sorted(decisions, key=lambda item: item.decision_id)), stage_summaries=tuple(AtlasCompilerStageSummary(stage=stage, decision_count=sum(item.stage == stage for item in decisions), selected_count=sum(item.stage == stage and item.action == AtlasSelectionAction.SELECTED for item in decisions), excluded_count=sum(item.stage == stage and item.action == AtlasSelectionAction.EXCLUDED for item in decisions)) for stage in AtlasCompilerStage), warning_categories=tuple(sorted(warnings)), conflict_ids=tuple(conflict.conflict_id for conflict in conflicts), budget_summary=usage)
        return manifest.model_copy(update={"deterministic_digest": manifest.computed_digest})

    def _package(self, snapshot, inputs, nodes, relationships, conflicts, usage, manifest, warnings, budget_decision_count):
        evidence = tuple(AtlasEvidenceItem(evidence_id=f"evidence-{node.node_id[5:]}", provider_id=node.provenance.provider_id, excerpt=node.label, classification=node.classification.value, provenance=node.provenance, ordinal=index) for index, node in enumerate(nodes) if node.provenance)[:snapshot.compiler_policy.max_total_evidence]
        citations = tuple(AtlasCitation(citation_id=f"citation-{node.node_id[5:]}", provider_id=node.provenance.provider_id, source_reference=node.provenance.original_reference, label=node.label, provenance=node.provenance, classification=node.classification, ordinal=index) for index, node in enumerate(nodes) if node.provenance)[:snapshot.compiler_policy.max_total_citations]
        reference = AtlasManifestReference(manifest_digest=manifest.computed_digest, deterministic_digest=manifest.deterministic_digest or manifest.computed_digest, decision_count=len(manifest.entries), stage_summary_count=len(manifest.stage_summaries), selected_provider_count=len(manifest.selected_provider_ids), excluded_provider_count=len(manifest.excluded_provider_ids), warning_count=len(manifest.warning_categories), conflict_count=len(manifest.conflict_ids), budget_decision_count=budget_decision_count)
        package = AtlasContextPackage(request_id=snapshot.request.request_id, created_at=snapshot.compilation_time, snapshot_fingerprint=snapshot.snapshot_fingerprint, compiler_policy_fingerprint=snapshot.compiler_policy.policy_fingerprint, selected_provider_ids=tuple(item.provider_id for item in inputs), nodes=nodes, relationships=relationships, evidence=evidence, citations=citations, conflicts=conflicts, warnings=tuple(AtlasContextWarning(category=warning, safe_message=warning) for warning in warnings), budgets=AtlasContextBudgetUsage(provider_count=len(inputs), node_count=len(nodes), relationship_count=len(relationships), evidence_count=len(evidence), serialized_bytes=0), optimization=AtlasOptimizationStats(applied=bool(warnings), omitted_item_count=0), manifest_reference=reference)
        package = package.model_copy(update={"package_fingerprint": package.computed_fingerprint()})
        if package.serialized_bytes() > snapshot.compiler_policy.max_total_serialized_bytes:
            raise AtlasRuntimeError(AtlasErrorCategory.CONTRACT_SIZE_EXCEEDED)
        return package

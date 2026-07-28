# Enterprise Intelligence v2 - Chapter 5.1.3

## Checkpoint K.3 - Nexus Graph Retrieval And Context Optimization

K.3 adds deterministic graph retrieval on top of the immutable Nexus graph
snapshot created by K.1 and published by K.2. It optimizes which existing graph
entities and relationships become Atlas provider context.

K.3 does not create entities, generate relationships, mutate graph snapshots,
perform AI reasoning, use embeddings, rank by semantic similarity, add public
APIs, add frontend work, add database changes, or add persistence.

## Retrieval Architecture

`NexusRetrievalEngine` consumes only `NexusGraphSnapshot`. It performs bounded
entity retrieval, relationship expansion, multi-hop traversal, deterministic
ranking, deduplication, budget optimization, evidence path construction, and
conversion back to the existing `NexusGraphResult` provider conversion path.

Atlas continues to receive standard Nexus provider records. Atlas never receives
graph snapshot objects or retrieval internals.

## Request And Result

`NexusRetrievalRequest` is immutable and canonical. It contains seed entities,
requested entity types, relationship filters, maximum hops, entity and
relationship limits, byte and token estimates, provider timeout, and retrieval
mode.

`NexusRetrievalResult` is immutable and contains selected entities,
relationships, evidence paths, explanations, budget summary, graph fingerprint,
retrieval fingerprint, warnings, average hops, and average score.

## Traversal

Traversal is breadth-first, deterministic, and capped at three hops. Cycles are
tracked by entity and depth so traversal always terminates. Relationship and
entity ordering uses stable identifiers.

## Ranking

Ranking is deterministic. Scores are based on hop distance, relationship
priority, entity priority, stored graph confidence, and stable identifier
tie-breaks. There are no embeddings, cosine similarity, LLM ranking, or semantic
inference.

Relationship weights include direct reference, document collection, project
association, person reference, and media relation categories. Entity weights
include policy, knowledge document, project, media asset, organization, event,
and storage location categories.

## Budget Optimization

The optimizer applies maximum entities, relationships, bytes, and token
estimate. Overflow is handled by stable rank order and warnings. It preserves
relationship endpoint consistency by adding endpoints only when the same budget
permits them.

## Deduplication

Selected entities, relationships, and evidence paths are deduplicated by stable
IDs. If multiple paths explain the same item, the strongest deterministic
explanation is retained.

## Evidence Paths

Evidence paths explain why an entity or relationship was selected using
deterministic reason categories such as entity priority, relationship priority,
and hop count. They include hop chains, source connector category, confidence
source, and score. They do not contain AI-generated prose.

## Observability And Diagnostics

Nexus metrics now include retrieval count, average retrieval latency, average
hops, budget utilization, selected and discarded counts, average retrieval
score, retrieval mode, and engine version. Diagnostics remain content-free:
they expose no graph labels, relationship contents, source text, prompts,
credentials, paths, or raw graph objects.

## Benchmark

`backend/scripts/benchmark_graph_retrieval.py` measures retrieval, ranking and
budget optimization, provider conversion, and total latency over deterministic
small and moderate synthetic snapshots.

## Future Semantic Retrieval

Future K.4+ work may add semantic retrieval only behind explicit bounded
contracts. K.3 intentionally stays graph-structural and deterministic.


# Enterprise Intelligence v2 - Chapter 6.1

## Checkpoint L - Enterprise Knowledge Evolution

Checkpoint K.3 established deterministic graph retrieval and context
optimization over immutable Nexus snapshots. Checkpoint L adds an observational
enterprise knowledge evolution layer that measures quality, freshness, coverage,
retrieval usefulness, operational trends, gaps, feedback, and review
recommendations.

Checkpoint L observes and recommends. It does not automatically mutate
enterprise knowledge, graph snapshots, connector settings, retrieval priorities,
prompts, model behavior, or provider configuration. All future operational
actions require explicit administrator approval and a separate execution
pathway.

## Architecture

Approved operational signals flow into immutable evolution event contracts.
`KnowledgeEvolutionEventNormalizer` canonicalizes content-free fields and
generates deterministic fingerprints. `KnowledgeEvolutionEventBuffer` stores a
bounded in-memory event history. Evaluators produce immutable
`KnowledgeQualitySnapshot` values. The rule-based recommendation engine emits
bounded, explainable recommendations stored in an in-memory
`KnowledgeEvolutionRecommendationStore` for administrator review.

The evolution service does not invoke connectors, execute ingestion, publish
snapshots, mutate Atlas compilation, alter Forge prompts, change AI Router model
selection, call LLMs, use embeddings, or use vector search.

## Event Contracts And Normalization

`KnowledgeEvolutionEvent` records safe event type, source subsystem, graph
fingerprint prefix, provider or connector category, entity or relationship
category, safe outcome and reason categories, bounded counts, bounded scores,
budget utilization, latency, and operational timestamp.

Event fingerprints exclude operational timestamps so equivalent logical events
normalize identically. Prohibited content markers such as prompts, answer text,
document bodies, transcripts, OCR, paths, credentials, and raw exceptions are
rejected from categorical fields.

## Bounded Event Buffer

The event buffer is in-memory, thread-safe, and capacity-bound. It evicts oldest
entries first and returns deterministic read ordering. It stores no prompts,
answers, source payloads, graph labels, or raw IDs.

## Quality Snapshots

`KnowledgeQualitySnapshot` summarizes freshness distribution, entity and
relationship type counts, isolated entities, source coverage, retrieval rates,
budget utilization, evidence-path availability, reliability rates, selected
type counts, unused ratios, trend categories, gap categories, and bounded
quality scores.

UNKNOWN remains distinct from zero. Scores are advisory 0-100 values when enough
data exists, and formulas are based on observable rates only.

## Freshness

`KnowledgeFreshnessEvaluator` classifies source age as CURRENT, AGING, STALE, or
UNKNOWN using explicit policy thresholds and unchanged-source streaks. It does
not infer freshness with AI and never marks source knowledge invalid
automatically.

## Coverage

`KnowledgeCoverageEvaluator` detects isolated entities, missing configured
entity categories, missing explicitly configured relationship policies, absent
source summaries, and source ownership aggregate gaps. Policies are explicit;
the evaluator does not assume every entity type requires every relationship.

## Retrieval Quality

`RetrievalQualityEvaluator` measures empty retrievals, partial retrievals,
budget pressure, discarded candidate pressure, evidence-path availability,
average hops, and selection counts. It does not inspect generated answers or
evaluate answer truthfulness.

## Administrator Feedback

`KnowledgeFeedbackRecord` captures content-free feedback categories such as
useful context, irrelevant context, missing context, outdated context,
duplicate context, incorrect source link, recommendation acceptance,
recommendation rejection, and needs review. Free-form comments are out of scope
for deterministic scoring.

Feedback never mutates the graph.

## Recommendation Model And Rules

`KnowledgeEvolutionRecommendation` contains stable type, severity, confidence,
affected subsystem, safe categories, reason codes, supporting metrics, graph
fingerprint prefix, lifecycle status, occurrence counts, and deterministic
fingerprint.

`KnowledgeEvolutionRecommendationEngine` is deterministic, rule-based, bounded,
content-free, and explainable. Rules have stable IDs, thresholds, minimum sample
sizes, severity, confidence, reason codes, and suppression policy metadata.

Recommendation priority is deterministic: critical operational failures,
ingestion failures, fallback pressure, freshness issues, coverage gaps, empty
retrievals, budget pressure, unused knowledge, and low-severity optimization
opportunities.

## Deduplication And Lifecycle

Recommendations deduplicate by logical reason and affected scope. The store
retains first detected time, most recent detected time, occurrence count,
current severity, and supporting metrics.

Lifecycle statuses are OPEN, ACKNOWLEDGED, ACCEPTED, REJECTED, RESOLVED, and
EXPIRED. Accepting a recommendation only means an administrator agrees it should
be addressed; it does not execute an action.

## Trend And Gap Analysis

Trends are deterministic and bounded: IMPROVING, STABLE, DEGRADING, or
INSUFFICIENT_DATA. Gap detection is category-based and includes empty retrieval
pressure, evidence gaps, budget pressure, missing configured entity categories,
and configured relationship policy gaps. It does not retain user questions or
infer missing facts from answers.

## Observability And Diagnostics

Metrics include event counts, event type counts, buffer utilization,
recommendation counts, lifecycle counts, severity distribution,
recommendation-type distribution, feedback counts, and feedback category
distribution.

Diagnostics expose enabled state, service status, engine version, buffer sizes,
recommendation store sizes, latest evaluation timestamps, health category,
recommendation severity distribution, coverage-gap aggregates,
empty-retrieval aggregate rate, and connector-failure aggregate rate.

Diagnostics do not expose entity IDs, labels, document titles, filenames,
paths, prompts, answers, transcript text, OCR, raw source IDs, raw exceptions,
administrator identities, or full evidence payloads.

## Performance

`backend/scripts/benchmark_knowledge_evolution.py` measures event normalization,
event append, quality snapshot construction, freshness evaluation, coverage
evaluation, retrieval quality evaluation, recommendation generation,
recommendation deduplication, trend calculation, feedback aggregation, and
diagnostics generation over deterministic small and moderate datasets.

## Testing And Limitations

Focused tests cover event immutability, normalization, bounded buffers,
freshness, coverage, retrieval quality, feedback, recommendation rules,
deduplication, lifecycle, store capacity, service diagnostics, scores, trends,
gap detection, feedback aggregation, policy recommendations, determinism,
permutations, concurrency, privacy, disabled behavior, and dependency
boundaries.

Checkpoint L remains advisory. It introduces no persistence, public APIs,
frontend work, external queues, autonomous agents, model training, embeddings,
vector search, graph mutation, connector execution, or production behavior
changes.


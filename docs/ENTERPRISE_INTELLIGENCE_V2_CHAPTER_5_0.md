# Enterprise Intelligence V2 Chapter 5.0

## Observability Architecture

Atlas observability is an application-level, read-only service. It consumes safe
rollout decisions and Atlas traces, then emits aggregate operational summaries.
It does not modify prompts, compile behavior, provider contracts, package
contracts, or fingerprints.

## Health Model

Health is pure operations logic: healthy, warning, degraded, or failed. It
considers compilation failure rate, provider timeout rate, Atlas latency,
rollback activity, and emergency disable state. No inference is performed.

## Metrics

The service tracks request mode counts, compilation latency and success,
provider latency and failures, Forge adaptation latency, prompt size aggregates,
fallback counts, retained nodes, and dropped nodes.

## Histograms

Latency histograms use bounded buckets: less than 5ms, 5-10ms, 10-25ms,
25-50ms, 50-100ms, and 100ms or more.

## Moving Averages

Moving averages are exposed for 1, 5, and 15 minute windows across compile,
provider, Atlas latency, and request rate.

## Operational Snapshot

`AtlasOperationalSnapshot` is immutable and canonically serializable. It
contains health, summaries, alerts, capacity metrics, version, and an
operational timestamp. It contains no prompts, provider payloads, traces, or
enterprise data.

## Capacity Planning

Capacity values are measured only: requests per hour, peak concurrency, average
package size, average Forge size, average retained nodes, average dropped nodes,
and Atlas utilization. No forecasting is included.

## Alerts

Internal alerts cover provider timeout rate, compilation failure rate, slow
compile average, rollback activity, and emergency disable state. Alerts are not
sent externally.

## Remaining Limitations

Metrics are in-memory only and reset on process restart. There is no dashboard,
database persistence, notification channel, or Nexus integration.

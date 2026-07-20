# CTV ONE Enterprise Intelligence v2.0 — Chapter 3.1

## Atlas runtime foundation

Atlas is the future Enterprise Context Engine. Sprint 3.1 creates its standalone,
server-owned runtime foundation only. It has an empty provider registry by design.
Atlas does not retrieve enterprise data, assemble context, call an LLM, integrate
with the Supervisor or Forge, or run from any Company Brain request path.

## Runtime architecture

`AtlasRuntimeManager` owns an `AtlasProviderRegistry`, immutable provider lifecycle
records, safe process-local metrics, and an optional bounded health-poll task. The
FastAPI lifespan starts Atlas once after the existing Forge runtime has initialized
and shuts it down first during teardown. Atlas has no startup dependency on Forge;
the ordering is operational ownership only.

The registry is static and server-owned. It has no filesystem discovery, dynamic
imports, entry-point discovery, remote plugin installation, or request-controlled
registration. Sprint 3.1 registers no providers.

## Provider contract and lifecycle

`AtlasProviderDefinition` is immutable and validates stable IDs, semantic provider
versions, compatible major/minor contract versions, bounded timeouts, allowlists,
classifications, and schema versions. Runtime contract compatibility accepts only
the same major contract and a provider minor version no newer than the runtime.

`AtlasProvider` defines bounded `initialize`, `health_check`, `readiness_check`,
`drain`, and idempotent `shutdown` hooks. `collect` is only a future contract and
is never invoked in this sprint.

Provider lifecycle states are `registered`, `initializing`, `ready`, `degraded`,
`unavailable`, `disabled`, `draining`, `stopped`, and `failed`. Transitions are
validated. A controlled runtime restart rebuilds records from the already approved
immutable registry; stopped provider records themselves are terminal.

## Health, readiness, and failure isolation

Health, readiness, initialization, drain, and shutdown hooks are timeout-bounded.
Health polling is disabled in test configuration. Health checks never call
collection or inference. Failures move providers from ready to degraded and then
unavailable at the configured threshold; successful health checks restore ready
after the configured recovery threshold. Disabled and stopped providers are not
polled.

Optional provider failures are isolated. Required provider failures leave Atlas in
the safe `degraded` state without crashing application startup. An enabled empty
registry is a ready, idle runtime. Disabled Atlas reports safe stopped diagnostics.

## Context package contract

`AtlasContextPackage` v1.0 and its node, relationship, evidence, citation, warning,
budget, optimization, and provider-result models are typed, `extra=forbid`,
deterministically serializable, and size-bounded. Metadata is intentionally small
and rejects keys associated with prompts, reasoning, exceptions, tracebacks, or
credentials. The package factory creates an empty valid package; no package is
created by the production request path in Sprint 3.1.

## Diagnostics and metrics

`GET /api/v1/runtime/atlas/status` is administrator-only. It returns cached runtime
and provider lifecycle/readiness information and never calls provider hooks. It does
not expose request content, context packages, evidence, prompts, employee data,
credentials, dependency URLs, raw exceptions, or traces.

Bounded process-local metrics use only runtime-owned provider IDs, lifecycle state,
health status, and safe reason categories. They never use request IDs, people,
content, node IDs, document names, or exception text as labels.

## Configuration

Tracked defaults are in `backend/app/core/config.py` and `backend/.env.example`:

- `CTV_ONE_ATLAS_ENABLED`
- runtime, provider-contract, and context-package versions
- health polling interval and timeout
- initialize and shutdown timeouts
- failure and recovery thresholds

The live `backend/.env` remains user-owned and is not edited by this sprint.

## Validation and deferred work

Focused Atlas tests cover registry validation, lifecycle transitions, health and
readiness behavior, timeout mapping, shutdown task cancellation, context-package
validation, diagnostics access, and FastAPI lifespan ordering. Existing Company
Brain, Supervisor, semantic-cache, Forge, and release checks remain regression
coverage.

Deferred: all real providers, context selection/scoring/graphs/optimization/caching,
persistent memory, external integrations, Supervisor and Forge integration, prompt
assembly changes, and every Atlas-originated LLM call.

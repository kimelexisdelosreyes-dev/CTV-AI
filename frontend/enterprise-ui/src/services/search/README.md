# Search Service

The UI-agnostic search boundary coordinates registered providers, deterministic ranking, deduplication, timeouts, cancellation, diagnostics, telemetry, and short-lived in-memory caching.

Providers implement `ISearchProvider`; callers use `SearchService`. This folder may depend on contracts and service-local utilities, but never React, Next.js, or concrete data sources. The current implementation is provider-neutral and ready for a demo provider or future integration.

```ts
const registry = new SearchRegistry();
registry.register(provider, 10);
const service = new SearchService(registry);
const response = await service.search({ text: "Interview", context: { module: "files" } });
```

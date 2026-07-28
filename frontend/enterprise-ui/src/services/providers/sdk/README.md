# Enterprise Provider SDK

The SDK standardizes provider metadata, health, lifecycle hooks, timeout and cancellation handling, retry policy, diagnostics, cache keys, and provider errors.

Providers extend `BaseProvider` and implement only `execute`. Retry is disabled by default. The SDK depends on contracts and service utilities, never React, Next.js, or UI components.

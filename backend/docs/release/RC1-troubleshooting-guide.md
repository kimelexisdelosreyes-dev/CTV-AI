# RC1 Troubleshooting Guide

## Capability workspace is not visible

Confirm the authenticated frontend deployment was built with `NEXT_PUBLIC_CTV_ONE_CAPABILITIES_ENABLED=true`. The navigation entry is intentionally absent when the flag is false.

## Discovery or execution is unavailable

Verify the existing backend capability framework, API, execution, and governance controls are enabled through the approved configuration process. When disabled, the service returns a controlled capability error; do not expose internal traces to users.

## Startup registration fails

Review the deterministic registry diagnostics. Every registered capability requires a matching manifest, handler, and governance record, with a valid unique identity and lifecycle/version metadata.

## Migration state is unexpected

Run the existing Alembic tooling from `backend` and confirm the expected head is `0011`. RC1 adds no migration; investigate environment drift rather than creating an RC1 schema change.

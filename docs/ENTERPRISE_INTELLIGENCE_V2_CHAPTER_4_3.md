# Enterprise Intelligence V2 Chapter 4.3

## Production Activation

Live activation enables Atlas Context for production requests when
`ctv_one_atlas_live_enabled` is true and higher-priority controls do not apply.
The policy order is emergency disable, Shadow Mode, Canary, Live, then standard
production.

## Prompt Integration

Live requests compile Atlas context, adapt it through Forge, and insert the
Atlas Context section through the Forge prompt builder. The target ordering is
System, Conversation, Company Brain, Atlas Context, Memory.

## Rollback

Turning off `ctv_one_atlas_live_enabled` immediately restores the production
prompt path. Emergency disable bypasses Atlas entirely, including orchestration,
compilation, adaptation, and prompt assembly.

## Metrics

Live diagnostics include live enabled state, live requests, Atlas injections,
Atlas failures, fallback count, average latency, average retained nodes, and
average dropped nodes. Diagnostics never include prompt text or provider
payloads.

## Trace

Atlas Trace records live activation, policy source, whether Atlas was injected,
fallback reason, and rollback state. Prompt text and user content remain absent.

## Performance

`backend/scripts/benchmark_live_activation.py` measures Atlas execution, Forge
adaptation, prompt assembly, and total request overhead.

## Operational Considerations

Shadow and Canary remain available and take priority over Live. Nexus remains
disconnected. Live activation uses the existing Atlas runtime and Forge adapter
without changing compiler, provider, package, or fingerprint contracts.

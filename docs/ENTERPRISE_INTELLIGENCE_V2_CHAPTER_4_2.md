# Enterprise Intelligence V2 Chapter 4.2

## Canary Architecture

Controlled Canary Rollout evaluates a deterministic `CanaryPolicy` before Atlas
prompt activation. Non-eligible users receive the production prompt. Eligible
users receive an Atlas-enhanced prompt built from the same Atlas runtime,
Forge adapter, and Forge prompt builder validated in Shadow Mode.

## Allowlist

`ctv_one_atlas_canary_users` contains explicit user identifiers separated by
commas, semicolons, or newlines. Matching is normalized to lowercase trimmed
identifiers. Raw identifiers are never stored in traces.

## Rollback

`ctv_one_atlas_canary_emergency_disabled` bypasses Atlas completely. It performs
no provider orchestration, no compilation, no adapter work, and no prompt change.
The flag is evaluated on every request and requires no restart.

## Feature Flags

`ctv_one_atlas_canary_enabled` defaults to false. `ctv_one_atlas_shadow_enabled`
remains supported. `ctv_one_atlas_live_enabled` is still reserved.
`ctv_one_atlas_canary_percentage` defaults to 0.

## Metrics

Canary diagnostics include eligible requests, production requests, Atlas
requests, fallback requests, policy decisions, average Atlas latency, average
prompt delta, average retained nodes, and average dropped nodes. Diagnostics do
not include prompt text, user content, or provider payloads.

## Trace Additions

Atlas Trace now includes policy decision, canary eligibility, feature source,
fallback reason, Atlas active state, and rollback state. User identifiers are
represented only by deterministic hashes in policy decisions and are not exposed
in trace summaries.

## Future Percentage Rollout

Percentage rollout uses deterministic hashing over the normalized user
identifier. With the default percentage of 0, percentage rollout is inactive.

## Limitations

The public chat schema remains unchanged. User identifiers are accepted only by
internal router calls today. Live Production rollout remains reserved.

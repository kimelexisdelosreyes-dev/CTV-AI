# Capability Production Rollout

Operational manifests add owner, support, maturity, visibility, lifecycle, rollout state, dependencies, and documentation independently of technical profiles. Registry startup validation deterministically rejects missing manifest, handler, or governance records. Visibility is operational metadata only and does not change execution. Rollout remains governed by the existing default-off API/framework/frontend feature gates.

## Workspace foundation

The feature-gated Capabilities workspace uses `CapabilityLayout -> CapabilityCatalog -> CapabilityDetail -> CapabilityInput -> CapabilityResult`, with loading and empty-state components. Its responsive CSS uses a desktop catalog/detail grid that stacks below tablet width. The authenticated shell shows the Capabilities navigation entry only when `NEXT_PUBLIC_CTV_ONE_CAPABILITIES_ENABLED=true`; chat remains the default path. Sprint 3.1B is reserved for richer business result presentation and UX refinement.

Validation for Sprint 3.1A: frontend lint, 114 frontend tests, and the production build (including TypeScript checking) pass; the focused capability API suite passes 6 tests; and `git diff --check -- frontend backend` reports no whitespace errors.

## Enterprise user experience

Sprint 3.1B refines the existing workspace components without changing capability APIs or execution. The detail panel presents only safe business metadata: category, lifecycle, version, availability, estimated latency, supported inputs and outputs, use cases, and support guidance. Result rendering is structured text only, with readable sections and lists; it never renders HTML or internal implementation details. Input states include examples, a character count, clear control, and an executing state.

The workspace now provides accessible status labels, live loading announcements, keyboard-visible focus states, safe retry guidance, and professional empty states. The desktop catalog/detail grid collapses for tablet and mobile layouts, and reduced-motion preferences disable the loading animation. Sprint 3.1C remains limited to production hardening and validation.

## RC1 architecture freeze and readiness audit

Phase 6.0 freezes the Enterprise Experience Platform architecture. No capability execution, API contract, runtime, routing, prompt, enterprise intelligence, or frontend architecture changes are part of RC1 preparation. Capability controls remain default-off: the backend capability API, framework, execution, and governance settings are false by default, and the authenticated shell only exposes the workspace when `NEXT_PUBLIC_CTV_ONE_CAPABILITIES_ENABLED=true`.

The registry rejects duplicate or missing capability identifiers. Its deterministic startup validation requires every registered capability to have a manifest, handler, and governance record; manifest identity is checked at operational registration and governance validation checks lifecycle/version metadata. Capability discovery, detail, and execution routes retain the existing authenticated-user dependency. Capability API responses remain safe and structured, while the frontend renders only text. Feature-gated error paths return controlled error identifiers rather than internal implementation detail.

RC1 validation evidence: frontend typecheck and lint passed; 115 frontend tests and the production build passed; focused capability API, governance, and manifest tests passed (8); the backend regression suite passed (701); Alembic reports `0011` as the single migration head; and `git diff --check -- frontend backend` has no whitespace errors.

## Baseline and RC1 scope

The local production build statically prerenders the capabilities route. The generated JavaScript and CSS artifacts total 10,427,319 bytes across 117 files. The workspace makes one discovery request when enabled and one execution request per submitted request; it does not poll. Browser navigation/load timing and real provider execution timing are not collected in this source-only, feature-off environment and are explicit controlled-environment acceptance measurements, not release claims.

RC1 scope is the frozen capability platform, authenticated feature-gated workspace, operational manifests/governance, and enterprise presentation layer. Phase 7.0 prerequisites are a controlled environment, approved flag rollout, authenticated browser timing, and provider-independent operational monitoring; they do not authorize architecture changes to RC1.

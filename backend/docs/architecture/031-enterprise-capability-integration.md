# Enterprise Capability Integration

The default-off capability framework gate enables a provider-neutral dispatcher boundary. Resolver reads an explicit capability ID from internal metadata, mapper creates CapabilityRequest, and dispatcher invokes existing router/executor only when enabled. Missing capability metadata returns not handled, preserving the current AIRouter flow without API changes. Production capability rollout requires explicit request metadata and separate authorization.

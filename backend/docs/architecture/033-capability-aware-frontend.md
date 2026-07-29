# Capability-Aware Frontend

The `/capabilities` frontend route is visible only when `NEXT_PUBLIC_CTV_ONE_CAPABILITIES_ENABLED=true`. It loads registry-driven metadata from the protected Capability API, sends an explicit selected ID and JSON-safe text input, and renders provider-neutral output without HTML injection. Chat remains unchanged; backend gates remain authoritative.

# Enterprise Intelligence v2.0 — Chapter 4.0

## Forge Atlas context adapter

Checkpoint F introduces Forge as the first optional consumer of immutable Atlas context packages. Dependency direction is permanently one-way: `app.forge` imports public Atlas contracts, while Atlas never imports Forge. The adapter does not compile context, execute providers, access manifests, call inference, or mutate packages.

## Package consumption and validation

`ForgeContextAdapter` accepts only `AtlasContextPackage`. It verifies the current package contract version, non-empty and recomputed package fingerprint, manifest reference digest consistency and version, canonical node order, package size, and node count. Failures use stable `ForgeContextErrorCategory` values without payloads or raw exceptions.

The adapter retains the package's existing node sequence. It does not rescore, reorder, merge, summarize, or paraphrase nodes. Each retained node becomes one immutable `ForgeContextBlock`; its label, evidence excerpt, classification, score, citations, and provenance are copied from immutable Atlas contracts.

## Forge context window and token budgeting

`ForgeContextWindow` is a frozen canonical contract containing immutable blocks, estimated token count, retained/dropped counts, package fingerprint, manifest reference, Atlas package version, and Forge context version. It contains no timestamps or runtime measurements.

Forge estimates tokens locally and deterministically as the UTF-8 byte length rounded up in groups of four. A bounded Forge-owned token budget retains the highest-ranked prefix of Atlas nodes. Once the next node exceeds the budget, that node and every lower-ranked node are dropped. Identical packages and budgets therefore produce identical canonical window bytes.

## Prompt integration and feature flags

`integrate_atlas_context` inserts a canonical `Atlas Context` section between `Company Brain` and `Memory`. It operates only when Atlas is enabled, the independent Forge adapter flag is enabled, and a valid context window is supplied. Every disabled or missing-window path returns the original prompt unchanged.

Configuration defaults are deliberately dormant:

- `ctv_one_forge_atlas_enabled = false`
- `ctv_one_forge_atlas_max_tokens = 4000`

No public endpoint or production request path was activated in this checkpoint.

## Deterministic and isolation guarantees

Focused tests verify immutable contracts, package/citation/provenance preservation, deterministic truncation, stable token estimation, byte-identical disabled prompts, enabled prompt placement, safe flag combinations, package validation, 100 repeated consumptions, package non-mutation, and the absence of Forge imports in Atlas. Forge does not invoke the Atlas compiler, provider orchestrator, providers, Nexus, databases, or inference.

## Benchmark

`backend/scripts/benchmark_forge_context_adapter.py` observes package validation, token estimation/context conversion, prompt integration, and total adapter time for 16-node and 64-node packages over 100 iterations. It uses only the standard library. Measured results are recorded in the Checkpoint F validation report.

The validation run observed median end-to-end adapter-plus-prompt time of 4.055 ms for 16 nodes and 18.624 ms for 64 nodes. These figures are observational and are not used by deterministic contracts.

## Remaining limitations

Atlas packages currently expose canonical node order but do not include a separate public rank object in the package. Forge therefore treats the immutable package node sequence as authoritative. Node content is sourced from the matching immutable evidence excerpt because the current package node contract has no dedicated content field. The adapter is not wired into a production request path, no Atlas collection is triggered by Forge, and no Nexus integration exists.

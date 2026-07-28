# AI Model Orchestrator Contracts

Phase 4.7A provides a deterministic, planning-only boundary between an immutable `AIContextPackage` and a future model runtime. It accepts an explicit task, registry snapshot, policy, and limits; it produces either a bounded immutable execution plan or a controlled outcome. It never constructs prompts, invokes models, accesses providers, searches enterprise state, or stores data.

The contract vocabulary covers tasks, input modalities, output types, execution modes, model identity, declared capabilities, languages, context windows, coarse latency/cost, location, and availability. Unknown support is never inferred from a model name or provider. Registry creation sorts descriptors by stable model ID, rejects duplicates, freezes the result, and creates a source fingerprint.

Policy defaults to local-only execution and denies cloud, external knowledge, tools, sensitive data, streaming, and batch. Context-package restrictions are merged with most-restrictive-wins semantics. Eligibility checks enabled/availability, model/provider blocks, allowlists, location, modality, output, mode, declared capabilities, citations, structured output, language, and long-context requirements.

Selection is deterministic: configured priority, explicit preferred model IDs, supported task, preferred capabilities, and local location contribute fixed scores; lexical model ID breaks ties. Reasoning is selected only for an explicit reasoning task/capability, never from request size. Fallback candidates are separately eligible and bounded; they are plans only, not runtime retries.

The current legacy router remains unchanged. Existing configured fast/knowledge/operations/balanced/default Qwen and reasoning DeepSeek mappings can be represented as registry policy tags, priority, and preferred IDs; these names are not embedded in generic contracts. Model runtime and adapters remain **PLANNED**.

## Production hardening (Phase 4.7A.1)

The registry rejects duplicate IDs, invalid priority, invalid location/provider/availability values, and unsupported controlled vocabulary members before it freezes and sorts the snapshot. Planning has no random input: candidates are scored from configured priority, explicit model preference, task support, preferred capabilities, and local location; equal scores use lexical model ID order. Registry input order cannot affect selection.

Eligibility is an all-required gate before scoring. It validates policy location/provider/model restrictions, availability, modality, output, mode, language, long context, citations, structured output, and explicitly required capabilities. Fallbacks are subsequent entries in this independently eligible, deterministic order and are bounded by both policy and limits.

Plans contain references and metadata only: IDs, fingerprint, effective policy, limits, diagnostics, statistics, selected IDs, output type, and mode. The request cancellation signal is inspected but never copied to an output. Contracts expose no credentials, endpoints, SDK clients, adapters, Maps, Sets, functions, prompts, or raw enterprise content. Dedicated source-governance tests verify that the planner does not couple to providers, search/context/graph/memory runtimes, UI, HTTP, prompts, or browser storage.

Phase 4.7B consumes the finalized plan beneath this boundary. It cannot call back into the planner, alter selection, or add fallback models.

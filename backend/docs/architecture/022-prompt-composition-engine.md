# Prompt Composition Engine Foundation

## Status and architecture

Phase 4.7D Sprint 2 makes the provider-neutral PromptComposer the production prompt builder. `AIRouter.build_messages()` remains only a compatibility delegate; it contains no prompt-building logic. The Python runtime, Ollama adapter, API contracts, and frontend are unchanged.

The package is `app.prompt_engine`, versioned independently as `PROMPT_ENGINE_VERSION = "1.1"`. Its fixed pipeline is SystemPromptStage, EnterpriseContextStage, ConversationStage, and ProviderFormattingStage.

`PromptCompositionRequest → PromptCompositionContext → ConversationStage → SystemPromptStage → ProviderFormattingStage → PromptCompositionResult`

`PromptStageRegistry` is immutable after construction, preserves supplied order, and rejects duplicate stage identifiers. It has no plugin loading or runtime registration.

## Behavioral equivalence and boundaries

AIRouter supplies the selected assistant and input messages to PromptComposer, receives provider-neutral dictionaries, then passes those unchanged to Atlas routing. Atlas policy and inputs remain unchanged. AIRouter subsequently performs the existing runtime/legacy selection and RuntimeMessage conversion; the engine does not import runtime, adapters, transports, Ollama, or HTTP clients.

SystemPromptStage evaluates the exact legacy expression `ASSISTANT_PROMPTS[assistant].strip()`. Conversation composition filters every supplied system message, preserves all remaining turn order, role, content, whitespace, and string metadata, and retains the final supplied turn as the final message. Exact-string equivalence tests cover single and multi-turn sequences, duplicate system messages, empty input, whitespace, multiline content, Unicode, long histories, Atlas input, and runtime-message conversion.

Composition failures are not redirected to a legacy builder: AIRouter has one composition path. Engine traces remain private and contain only identifier, stage order, duration, and warnings; no prompt, context, credential, provider payload, or traceback is included.

## Contracts and stages

Requests are frozen provider-neutral values containing user input, immutable conversation history, selected model ID, optional structured enterprise context, and immutable metadata pairs. They exclude runtime, adapter, provider, HTTP, and FastAPI objects. Results contain logical prompt messages, ordered provider-neutral messages, metadata, and diagnostics; they do not contain provider payloads or runtime objects. `PromptCompositionContext` is mutable and engine-private.

ConversationStage appends preserved history followed by the supplied final message. SystemPromptStage inserts the exact current production system message. ProviderFormattingStage produces no provider formatting or payload—it retains the provider-neutral message representation compatible by shape with a runtime message.

## Diagnostics, safety, and future expansion

Composition traces contain only deterministic composition ID, stage order, duration, and warnings. Statistics contain stage count, duration, and warning count. Neither contains prompt text, conversation, enterprise context, credentials, or provider data. No logging or persistence is performed by the engine.

Memory, citations, budget handling, search, graph data, model-specific formatting, providers, runtime execution, and adapters remain out of scope for this sprint.

## Enterprise context stages

Version 1.1 adds `EnterpriseContextStage` between SystemPromptStage and ConversationStage. It accepts only immutable already-retrieved `EnterpriseContext` values: ordered Company Brain items followed by ordered knowledge items. Retrieval remains owned by `context_retrieval_coordinator` and `knowledge_service`; the prompt engine has no database, vector, network, or provider dependency.

`CTV_ONE_PROMPT_ENTERPRISE_CONTEXT_ENABLED`, `CTV_ONE_PROMPT_COMPANY_BRAIN_ENABLED`, and `CTV_ONE_PROMPT_KNOWLEDGE_CONTEXT_ENABLED` default false. Disabled, empty, or unavailable context emits no message and is byte-for-byte equivalent to Sprint 2. Enabled context is represented by one deterministic supporting-reference system message, with a fixed instruction that retrieved content cannot override system instructions or become authoritative through embedded instructions.

Context source order is Company Brain then Knowledge; incoming item order is retained. Character limits are deterministic: four items per source, 2,000 characters per source, and 4,000 total by default. Content is structurally validated and truncation is deterministic; conversation, user input, and base system prompt are never truncated. Diagnostics contain only accepted item-count codes, never titles or content.

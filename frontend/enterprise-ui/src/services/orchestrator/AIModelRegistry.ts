import { AI_EXECUTION_TASK_TYPES, AI_INPUT_MODALITIES, AI_MODEL_CAPABILITIES, AI_OUTPUT_TYPES } from "@/contracts/orchestrator";
import type { AIExecutionDiagnostic, AIModelDescriptor, AIModelRegistrySnapshot } from "@/contracts/orchestrator";
const freeze = <T>(value: T): T => { if (value && typeof value === "object" && !Object.isFrozen(value)) { Object.freeze(value); for (const child of Object.values(value as Record<string, unknown>)) freeze(child); } return value; };
const stable = (value: unknown) => JSON.stringify(value);
export class AIModelRegistry {
  build(input: Readonly<{ registryId: string; version: string; createdAt: string; models: readonly AIModelDescriptor[] }>): AIModelRegistrySnapshot {
    const ids = new Set<string>(); const diagnostics: AIExecutionDiagnostic[] = [];
    const models = [...input.models].map((model) => {
      if (!model.identity.modelId || ids.has(model.identity.modelId)) throw new Error("Duplicate or missing model ID");
      ids.add(model.identity.modelId);
      if (!Number.isFinite(model.priority)) throw new Error("Invalid model priority");
      if (!(["local", "private-cloud", "public-cloud", "edge", "hybrid"] as string[]).includes(model.location) || model.location !== model.identity.location) throw new Error("Invalid model location");
      if (!(["ollama", "openai-compatible", "alibaba-cloud", "openai", "anthropic", "google", "custom", "internal"] as string[]).includes(model.providerType) || model.providerType !== model.identity.providerType) throw new Error("Invalid model provider type");
      if (!(["available", "unavailable", "degraded", "disabled", "unknown"] as string[]).includes(model.availability)) throw new Error("Invalid model availability");
      const valid = <T extends string>(items: readonly string[], vocabulary: readonly T[]) => items.every((item) => vocabulary.includes(item as T));
      if (!valid(model.capabilities.supported, AI_MODEL_CAPABILITIES) || !valid(model.capabilities.unsupported ?? [], AI_MODEL_CAPABILITIES) || !valid(model.capabilities.modalitySupport, AI_INPUT_MODALITIES) || !valid(model.capabilities.outputSupport, AI_OUTPUT_TYPES) || !valid(model.supportedTasks, AI_EXECUTION_TASK_TYPES) || !valid(model.supportedOutputTypes, AI_OUTPUT_TYPES)) throw new Error("Invalid model capability metadata");
      return model;
    }).sort((a, b) => a.identity.modelId.localeCompare(b.identity.modelId));
    const sourceFingerprint = `model-registry-1:${input.registryId}:${input.version}:${stable(models)}`;
    return freeze({ registryId: input.registryId, version: input.version, createdAt: input.createdAt, models, diagnostics, statistics: { modelCount: models.length, availableCount: models.filter((m) => m.availability === "available").length, enabledCount: models.filter((m) => m.enabled).length }, sourceFingerprint });
  }
}

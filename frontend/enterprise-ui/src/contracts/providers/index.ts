export type ProviderId = string;
export type ProviderCapability = "search" | "context" | "graph" | "memory" | "ai";
export type ProviderHealth = "healthy" | "degraded" | "offline" | "unknown";
export type ProviderDiagnostic = { providerId: ProviderId; health: ProviderHealth; message?: string };
export interface IEnterpriseProvider { readonly id: ProviderId; readonly name: string; readonly capabilities: readonly ProviderCapability[]; health(): Promise<ProviderHealth>; diagnose(): Promise<ProviderDiagnostic>; }

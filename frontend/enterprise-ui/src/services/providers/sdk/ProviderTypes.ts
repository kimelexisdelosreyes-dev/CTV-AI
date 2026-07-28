import type { SearchContext, SearchProviderResponse, SearchQuery } from "@/contracts/search";
import type { ITelemetryService } from "@/contracts/telemetry";
import type { ICacheService } from "@/contracts/cache";

export type ProviderHealth = "healthy" | "degraded" | "offline" | "unavailable" | "unauthorized" | "unknown";
export type ProviderLifecycle = "initialize" | "validate" | "execute" | "normalize" | "diagnostics" | "cleanup";
export type ProviderRetryPolicy = { attempts: number; baseDelayMs: number; backoff: "none" | "exponential" };
export type ProviderConfig = { timeoutMs?: number; retry?: ProviderRetryPolicy; cacheTtlMs?: number };
export type ProviderManifest = { id: string; version: string; priority: number; sourceMode: "local-demo" | "local" | "indexed" | "live"; capabilities: readonly string[]; supportedEntities: readonly string[]; supportedRelationships: readonly string[]; searchFields: readonly string[] };
export type ProviderContext = { search?: SearchContext; configuration?: ProviderConfig; signal: AbortSignal; telemetry?: ITelemetryService; cache?: ICacheService<SearchProviderResponse>; logger?: (message: string, details?: Record<string, unknown>) => void; clock?: () => number; environment?: string };
export type ProviderDiagnostics = { providerId: string; status: SearchProviderResponse["status"]; durationMs: number; resultCount: number; errors: string[]; warnings: string[]; retries: number; cache: "hit" | "miss" | "bypass" };

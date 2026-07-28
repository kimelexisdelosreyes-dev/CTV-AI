import type { ICacheService } from "@/contracts/cache";
import type { SearchProviderResponse } from "@/contracts/search";
export function providerCacheKey(providerId: string, query: string, context?: string) { return `provider:${providerId}:${query.trim().toLowerCase()}:${context ?? ""}`; }
export function providerCacheGet(cache: ICacheService<SearchProviderResponse> | undefined, key: string) { return cache?.get(key); }
export function providerCacheSet(cache: ICacheService<SearchProviderResponse> | undefined, key: string, response: SearchProviderResponse, ttlMs = 45_000, providerId = "") { cache?.set(key, response, { ttlMs, maxEntries: 100 }, [providerId]); }

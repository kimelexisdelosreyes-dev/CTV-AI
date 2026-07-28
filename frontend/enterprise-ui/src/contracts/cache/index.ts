export type CacheEntry<T> = { value: T; expiresAt: number; providerIds: string[] };
export type CachePolicy = { ttlMs: number; maxEntries: number };
export interface ICacheService<T> { get(key: string): T | undefined; set(key: string, value: T, policy?: CachePolicy, providerIds?: string[]): void; invalidate(key?: string): void; clear(): void; size(): number; }

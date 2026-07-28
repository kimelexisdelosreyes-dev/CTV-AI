import type { CachePolicy, ICacheService } from "@/contracts/cache";
type Stored<T> = { value: T; expiresAt: number; providerIds: string[] };
export class SearchCache<T> implements ICacheService<T> {
  private entries = new Map<string, Stored<T>>();
  constructor(private readonly now = () => Date.now(), private readonly defaultPolicy: CachePolicy = { ttlMs: 45_000, maxEntries: 100 }) {}
  get(key: string) { const entry = this.entries.get(key); if (!entry) return undefined; if (entry.expiresAt <= this.now()) { this.entries.delete(key); return undefined; } return entry.value; }
  set(key: string, value: T, policy = this.defaultPolicy, providerIds: string[] = []) { this.entries.delete(key); while (this.entries.size >= policy.maxEntries) this.entries.delete(this.entries.keys().next().value as string); this.entries.set(key, { value, expiresAt: this.now() + policy.ttlMs, providerIds }); }
  invalidate(key?: string) { if (key) this.entries.delete(key); else this.entries.clear(); }
  clear() { this.entries.clear(); }
  size() { return this.entries.size; }
}

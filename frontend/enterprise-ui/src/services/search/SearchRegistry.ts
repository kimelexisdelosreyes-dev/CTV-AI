import type { ISearchProvider, ISearchRegistry, SearchProviderCapability, SearchProviderStatus } from "@/contracts/search";
type Registered = { provider: ISearchProvider; priority: number; order: number };
export class SearchRegistry implements ISearchRegistry {
  private providers: Registered[] = [];
  register(provider: ISearchProvider, priority = 0) { if (this.providers.some((item) => item.provider.id === provider.id)) throw new Error(`Search provider already registered: ${provider.id}`); this.providers.push({ provider, priority, order: this.providers.length }); }
  unregister(id: string) { const before = this.providers.length; this.providers = this.providers.filter((item) => item.provider.id !== id); return before !== this.providers.length; }
  list() { return this.providers.slice().sort((a, b) => b.priority - a.priority || a.order - b.order).map((item) => item.provider); }
  discover(capability?: SearchProviderCapability) { return this.list().filter((provider) => !capability || provider.capabilities.includes(capability)); }
  health(id: string): SearchProviderStatus | undefined { return this.providers.find((item) => item.provider.id === id)?.provider.health(); }
}

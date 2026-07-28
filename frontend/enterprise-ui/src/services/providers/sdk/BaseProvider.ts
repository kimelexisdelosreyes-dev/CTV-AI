import type { ISearchProvider, SearchContext, SearchProviderCapability, SearchProviderResponse, SearchQuery } from "@/contracts/search";
import type { ProviderConfig, ProviderContext, ProviderDiagnostics, ProviderHealth } from "./ProviderTypes";
import { ProviderCancelledError, ProviderExecutionError, ProviderTimeoutError } from "./ProviderErrors";
import { withProviderTimeout } from "./ProviderTimeout";
import { withRetry, noRetry } from "./ProviderRetry";

export abstract class BaseProvider implements ISearchProvider {
  abstract readonly id: string;
  abstract readonly name: string;
  abstract readonly capabilities: readonly SearchProviderCapability[];
  protected readonly config: ProviderConfig;
  private currentHealth: ProviderHealth = "healthy";
  constructor(config: ProviderConfig = {}) { this.config = config; }
  supports(query: SearchQuery) { return query.text.trim().length > 0; }
  health() { return this.currentHealth === "healthy" ? "ready" : this.currentHealth === "offline" ? "offline" : this.currentHealth === "unauthorized" ? "unauthorized" : "unavailable"; }
  setHealth(health: ProviderHealth) { this.currentHealth = health; }
  async search(query: SearchQuery, context: SearchContext, signal: AbortSignal): Promise<SearchProviderResponse> { const started = Date.now(); const providerContext: ProviderContext = { search: context, configuration: this.config, signal }; try { await this.initialize(providerContext); await this.validate(query, providerContext); const response = await withRetry(() => withProviderTimeout(this.execute(query, providerContext), this.config.timeoutMs ?? 2_000, signal), this.config.retry ?? noRetry); const normalized = await this.normalize(response, providerContext); return this.diagnose(normalized, started, providerContext); } catch (error) { const status = error instanceof ProviderTimeoutError ? "timeout" : error instanceof ProviderCancelledError || signal.aborted || (error instanceof Error && error.message === "PROVIDER_CANCELLED") ? "cancelled" : "error"; return { status, results: [], durationMs: Date.now() - started, diagnostic: error instanceof Error ? error.message : "Provider error" }; } finally { await this.cleanup(providerContext); } }
  protected async initialize(_context: ProviderContext) {}
  protected async validate(_query: SearchQuery, _context: ProviderContext) {}
  protected abstract execute(query: SearchQuery, context: ProviderContext): Promise<SearchProviderResponse>;
  protected async normalize(response: SearchProviderResponse, _context: ProviderContext) { return response; }
  protected diagnose(response: SearchProviderResponse, started: number, _context: ProviderContext) { return { ...response, durationMs: response.durationMs || Date.now() - started }; }
  protected async cleanup(_context: ProviderContext) {}
}

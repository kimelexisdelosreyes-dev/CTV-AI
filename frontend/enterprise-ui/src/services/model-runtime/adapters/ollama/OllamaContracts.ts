export type OllamaGenerateResponse = Readonly<{ model?: string; response?: string; done?: boolean; done_reason?: string; prompt_eval_count?: number; eval_count?: number }>;
export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;
export type OllamaAdapterConfiguration = Readonly<{ baseUrl: string; supportedModelIds: readonly string[]; enabled?: boolean; fetch?: FetchLike }>;

export type AIModelRoute = { provider: string; model: string; capability: string };
export type AIRequest = { prompt: string; route?: AIModelRoute; context?: Record<string, string> };
export type AIResponse = { text: string; route: AIModelRoute; usage?: { input: number; output: number } };
export interface IAIModelRouter { route(request: AIRequest): AIModelRoute; }
export interface IAIOrchestrator { execute(request: AIRequest): Promise<AIResponse>; }

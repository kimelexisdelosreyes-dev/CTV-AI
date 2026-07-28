import type { AIRequest, AIResponse, IAIOrchestrator, IAIModelRouter } from "@/contracts/ai";
export class AIOrchestrator implements IAIOrchestrator { constructor(private readonly router: IAIModelRouter) {} async execute(request: AIRequest): Promise<AIResponse> { return { text: "AI execution requires a configured model provider.", route: this.router.route(request) }; } }

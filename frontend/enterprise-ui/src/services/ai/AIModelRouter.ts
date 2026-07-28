import type { AIModelRoute, AIRequest, IAIModelRouter } from "@/contracts/ai";
export class AIModelRouter implements IAIModelRouter { constructor(private readonly fallback: AIModelRoute = { provider: "unconfigured", model: "unconfigured", capability: "general" }) {} route(request: AIRequest) { return request.route ?? this.fallback; } }

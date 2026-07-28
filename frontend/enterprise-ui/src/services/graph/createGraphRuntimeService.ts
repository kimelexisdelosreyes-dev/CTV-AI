import type { IGraphRuntimeService } from "@/contracts/graph/runtime";
import { GraphRuntimeService } from "./runtime";
export function createGraphRuntimeService(): IGraphRuntimeService { return new GraphRuntimeService(); }

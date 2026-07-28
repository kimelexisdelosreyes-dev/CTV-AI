import type { GraphNeighborhood } from "@/contracts/graph";
import type { IGraphRuntimeService } from "@/contracts/graph/runtime";
import { resolveGraphIdentity, type GraphIdentityResolution } from "./GraphIdentityResolver";
export class GraphRuntimeQueryService { constructor(private readonly runtime: IGraphRuntimeService) {} selected(input: { id: string; providerId?: string; aliases?: string[] }): { resolution: GraphIdentityResolution; neighborhood?: GraphNeighborhood } { const session = this.runtime.current(); const resolution = resolveGraphIdentity(session?.graphSnapshot, input); return { resolution, neighborhood: resolution.node ? this.runtime.neighborhood(resolution.node.id, { depth: 1, maxNodes: 12, maxEdges: 16 }) : undefined }; } }

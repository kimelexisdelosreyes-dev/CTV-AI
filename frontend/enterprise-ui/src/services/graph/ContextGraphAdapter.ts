import type { ContextSnapshot } from "@/contracts/context";
import { GraphBuilder } from "./GraphBuilder";
export function graphFromContext(snapshot: ContextSnapshot) { return new GraphBuilder().fromContext(snapshot); }

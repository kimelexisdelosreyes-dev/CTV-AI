import type { ContextContribution, ContextRelationship, ContextSignal, EnterpriseContext } from "@/contracts/context";
export type ContextInput = { context: EnterpriseContext; signals?: ContextSignal[]; contributions?: ContextContribution[]; relationships?: ContextRelationship[] };

import type { GraphSourceAttribution } from "@/contracts/graph";
export type GraphIdentity = { canonicalId: string; aliases: string[]; provisional: boolean };
export type GraphEvidence = GraphSourceAttribution;
export type GraphProvenance = GraphSourceAttribution[];

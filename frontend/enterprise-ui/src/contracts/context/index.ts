export type ContextScope = "workspace" | "module" | "page" | "project" | "asset" | "search" | "provider" | "infrastructure";
export type ContextSource = "workspace" | "project" | "file" | "knowledge" | "memory" | "operations" | "search" | "infrastructure" | "runtime";
export type ContextConfidence = "low" | "medium" | "high";
export type EnterpriseContext = { module?: string; page?: string; projectId?: string; assetId?: string; selectedEntityId?: string; userId?: string; role?: string; department?: string; recentSearches?: string[] };
export type ContextSignal = { scope: ContextScope; source: ContextSource; key: string; value: string; weight?: number };
export type ContextContribution = { source: ContextSource; label: string; value: string; confidence?: number; entityId?: string; relationships?: ContextRelationship[]; temporalEvidence?: readonly TemporalEvidence[] };
export type ResolvedEntity = { id: string; type: string; label: string; sourceIds: string[]; confidence: ContextConfidence; metadata?: Record<string, string> };
export type ContextRelationship = { from: string; to: string; type: string; source: ContextSource; confidence?: number };
export type ContextSnapshot = Readonly<{ context: EnterpriseContext; entities: readonly ResolvedEntity[]; relationships: readonly ContextRelationship[]; signals: readonly ContextSignal[]; contributions: readonly ContextContribution[]; temporalEvidence: readonly TemporalEvidence[]; temporalStatistics: TemporalEvidenceStatistics; createdAt: string }>;
export interface IContextEngine { resolve(context: EnterpriseContext): Promise<ContextContribution[]>; snapshot(context: EnterpriseContext, contributions?: ContextContribution[]): Promise<ContextSnapshot>; }
export interface IContextResolver { canResolve(context: EnterpriseContext): boolean; resolve(context: EnterpriseContext): Promise<ContextContribution[]>; }
import type { TemporalEvidence, TemporalEvidenceStatistics } from "@/contracts/temporal";

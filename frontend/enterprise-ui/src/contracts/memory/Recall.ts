import type { MemoryRecord, MemoryStatistics } from "./Memory";
export type MemoryRecallScope = "entity" | "project" | "provider" | "timeline" | "relationship";
export type MemoryRecallFilter = Readonly<{ entityId?: string; projectId?: string; providerId?: string; relationshipType?: string; from?: string; to?: string }>;
export type MemoryRecallOrdering = "chronological" | "reverse_chronological" | "evidence";
export type MemoryRecallRequest = Readonly<{ scope: MemoryRecallScope; filter?: MemoryRecallFilter; ordering?: MemoryRecallOrdering; limit?: number }>;
export type MemoryRecallResult = Readonly<{ records: readonly MemoryRecord[]; statistics: MemoryStatistics; diagnostics: readonly string[] }>;
export type MemoryRecallStatistics = MemoryStatistics;
export type MemoryRecallDiagnostics = readonly string[];
export interface MemoryRecall { recall(request: MemoryRecallRequest): Promise<MemoryRecallResult>; }

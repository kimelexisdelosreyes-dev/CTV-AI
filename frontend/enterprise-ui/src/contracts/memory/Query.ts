import type { MemoryRecord, MemoryStatistics } from "./Memory";
import type { TimelineWindow } from "./Timeline";
export type MemoryQueryFilter = Readonly<{ entityId?: string; observationId?: string; eventId?: string; providerId?: string; relationshipType?: string; projectId?: string; from?: string; to?: string }>;
export type MemoryQueryOrdering = "chronological" | "reverse_chronological" | "evidence";
export type MemoryQueryWindow = TimelineWindow;
export type MemoryQuery = Readonly<{ filter?: MemoryQueryFilter; ordering?: MemoryQueryOrdering; window?: MemoryQueryWindow }>;
export type MemoryQueryResult = Readonly<{ records: readonly MemoryRecord[]; statistics: MemoryStatistics; diagnostics: readonly string[] }>;

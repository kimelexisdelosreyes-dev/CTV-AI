import type { MemoryDiagnostics, MemoryRecord, MemoryStatistics } from "./Memory";
import type { MemoryEvent } from "./MemoryEvent";
import type { Observation } from "./Observation";
import type { TimelineEntry } from "./Timeline";
export type MemorySnapshotMetadata = Readonly<{ version: string; createdAt: string; graphSessionId?: string; sourceContextSnapshotId?: string }>;
export type MemorySnapshotStatistics = MemoryStatistics;
export type MemorySnapshotDiagnostics = MemoryDiagnostics;
export type MemorySnapshot = Readonly<{ metadata: MemorySnapshotMetadata; observations: readonly Observation[]; events: readonly MemoryEvent[]; timeline: readonly TimelineEntry[]; records: readonly MemoryRecord[]; statistics: MemorySnapshotStatistics; diagnostics: MemorySnapshotDiagnostics }>;

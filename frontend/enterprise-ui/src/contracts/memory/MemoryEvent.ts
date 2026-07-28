import type { Observation, ObservationEvidence, ObservationParticipant, ObservationRelationship } from "./Observation";
export type MemoryEventType = "asset_lifecycle" | "project_change" | "render" | "publication" | "provider_sync" | "unknown";
export type MemoryEventEvidence = ObservationEvidence;
export type MemoryEventParticipant = ObservationParticipant;
export type MemoryEventReference = Readonly<{ observationId: string; entityId: string; graphNodeId?: string }>;
export type MemoryEventRelationship = ObservationRelationship;
export type MemoryEventStatistics = Readonly<{ observationCount: number; evidenceCount: number; relationshipCount: number }>;
export type MemoryEventDiagnostics = readonly string[];
export type MemoryEvent = Readonly<{ id: string; type: MemoryEventType; observations: readonly Observation[]; references: readonly MemoryEventReference[]; evidence: readonly MemoryEventEvidence[]; participants: readonly MemoryEventParticipant[]; relationships: readonly MemoryEventRelationship[]; statistics: MemoryEventStatistics; diagnostics: MemoryEventDiagnostics }>;

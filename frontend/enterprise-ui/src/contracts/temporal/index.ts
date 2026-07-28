export type TemporalEvidenceType = "created" | "modified";
export type TemporalTimestampCategory = "source-event" | "source-metadata" | "provider-observation" | "runtime-processing";
export type TemporalEvidencePrecision = "date" | "minute" | "second" | "millisecond" | "unknown";
export type TemporalEvidenceConfidence = "confirmed" | "supported" | "observed" | "imported" | "unknown";
export type TemporalEvidenceReference = Readonly<{ id: string; kind: "provider-record" | "source-metadata" }>;
export type TemporalEvidenceDiagnostics = Readonly<{ code: "timestamp-invalid" | "timestamp-missing" | "timezone-missing" | "temporal-evidence-preserved" | "temporal-evidence-dropped"; message: string }>;
export type TemporalEvidence = Readonly<{ id: string; entityId: string; sourceEntityId: string; providerId: string; type: TemporalEvidenceType; timestamp: string; timestampCategory: TemporalTimestampCategory; precision: TemporalEvidencePrecision; source: "provider" | "source"; reference: TemporalEvidenceReference; confidence: TemporalEvidenceConfidence; metadata?: Readonly<Record<string, string>>; diagnostics: readonly TemporalEvidenceDiagnostics[] }>;
export type TemporalEvidenceStatistics = Readonly<{ providerCount: number; evidenceCount: number; memoryEligibleCount: number; sourceEventCount: number; sourceMetadataCount: number; providerObservationCount: number; runtimeProcessingCount: number; entityCount: number; observationsCreated: number; readySessionCount: number; readyEmptySessionCount: number }>;

export type TimelineDirection = "forward" | "backward";
export type TimelineCursor = Readonly<{ value: string }>;
export type TimelineWindow = Readonly<{ limit: number; cursor?: TimelineCursor }>;
export type TimelineFilter = Readonly<{ entityId?: string; providerId?: string; projectId?: string; observationType?: string; eventType?: string; relationshipType?: string; from?: string; to?: string }>;
export type TimelineQuery = Readonly<{ filter?: TimelineFilter; direction?: TimelineDirection; window?: TimelineWindow }>;
export type TimelineEntry = Readonly<{ id: string; timestamp: string; entityId: string; graphNodeId?: string; observationId?: string; eventId?: string; order: number }>;
export type TimelineStatistics = Readonly<{ entryCount: number; earliest?: string; latest?: string }>;
export type TimelineDiagnostics = readonly string[];

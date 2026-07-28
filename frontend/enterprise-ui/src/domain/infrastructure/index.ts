export type InfrastructureStatus = "healthy" | "offline" | "unknown" | "unavailable";
export type StorageTier = "working" | "archive" | "cold" | "backup" | "scratch";
export type InfrastructureCapability = "inference" | "rendering" | "ocr" | "subtitles" | "storage" | "editing" | "indexing";
export type InfrastructureNode = { id: string; name: string; role: string; status: InfrastructureStatus; description: string; capabilities: InfrastructureCapability[]; relationships: Array<{ type: string; label: string }> };
export type StorageVolume = InfrastructureNode & { tier: StorageTier; location: string; capacityNote: string };
export type Workstation = InfrastructureNode & { owner?: string; department?: string; gpu?: string; cpu?: string; memory?: string; software?: string[] };
export type ComputeNode = InfrastructureNode & { models?: string[]; resources?: string[] };

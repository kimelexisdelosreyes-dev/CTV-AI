import type {
  InfrastructureServiceDetail,
  InfrastructureServiceStatus,
  InfrastructureStatus,
} from "@/lib/api";

export type InfrastructureStatusRow = {
  key: keyof InfrastructureStatus;
  label: string;
  status: string;
  category: string;
  model: string;
  isHealthy: boolean;
};

const SERVICES: Array<{
  key: keyof InfrastructureStatus;
  label: string;
}> = [
  { key: "postgresql", label: "PostgreSQL" },
  { key: "qdrant", label: "Qdrant" },
  { key: "embedding", label: "Embedding" },
];

const FALLBACK = "Unknown";

export function displayText(value: unknown, fallback = FALLBACK): string {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || fallback;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return fallback;
}

export function normalizeInfrastructureStatus(
  infrastructure: InfrastructureStatus | null,
): InfrastructureStatusRow[] {
  return SERVICES.map(({ key, label }) => {
    const value = infrastructure?.[key] ?? null;
    const detail = serviceDetail(value);
    const status = displayText(detail?.status ?? value);

    return {
      key,
      label,
      status,
      category: displayText(detail?.category),
      model: displayText(detail?.model),
      isHealthy: status.toLowerCase() === "healthy",
    };
  });
}

function serviceDetail(
  value: InfrastructureServiceStatus | undefined,
): InfrastructureServiceDetail | null {
  if (!value || typeof value !== "object") return null;
  return value;
}

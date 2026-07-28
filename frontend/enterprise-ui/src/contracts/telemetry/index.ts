export type TelemetryEvent = { name: string; timestamp: number; attributes?: Record<string, string | number | boolean> };
export type TelemetrySpan = { name: string; startedAt: number; endedAt?: number; attributes?: Record<string, string | number | boolean> };
export interface ITelemetryService { record(event: TelemetryEvent): void; startSpan(name: string, attributes?: TelemetrySpan["attributes"]): { end(attributes?: TelemetrySpan["attributes"]): void }; }

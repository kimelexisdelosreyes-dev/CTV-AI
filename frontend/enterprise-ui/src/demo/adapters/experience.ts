import { demoFileResults, demoMapConnections, demoMapNodes, demoNotifications, demoSearchResults, demoSourceActivity } from "../data/experience";
import { DemoFileResult, DemoMapConnection, DemoMapNode, DemoNotification, DemoScenario, DemoSearchResult, DemoSourceActivity } from "../types";

export function searchDemo(query: string, scenario: DemoScenario = "success"): DemoSearchResult[] {
  if (scenario === "error" || scenario === "offline") return [];
  const needle = query.trim().toLowerCase();
  if (!needle) return demoSearchResults.slice(0, 3);
  const terms = needle.split(/\s+/).filter(Boolean);
  return demoSearchResults.filter((result) => {
    const haystack = `${result.title} ${result.meta} ${result.category}`.toLowerCase();
    return haystack.includes(needle) || terms.some((term) => haystack.includes(term));
  });
}

export function sourceActivityForScenario(scenario: DemoScenario = "success"): DemoSourceActivity[] {
  if (scenario === "error") {
    return demoSourceActivity.map((source) => ({ ...source, status: "failed", message: "Demo source returned a recoverable error." }));
  }
  if (scenario === "offline") {
    return demoSourceActivity.map((source) => ({ ...source, status: "offline", connection: "offline", resultsFound: 0, message: "Source is unavailable in this demonstration state." }));
  }
  if (scenario === "partial") {
    return demoSourceActivity.map((source, index) => index > 2 ? { ...source, status: "warning", resultsFound: 0, message: "Source returned partial results." } : source);
  }
  return demoSourceActivity;
}

export function fileDiscoveryDemo(query: string, scenario: DemoScenario = "success"): DemoFileResult[] {
  if (scenario === "error" || scenario === "offline") return [];
  const needle = query.trim().toLowerCase();
  if (!needle) return [];
  const terms = needle.split(/\s+/).filter(Boolean);
  return demoFileResults.filter((result) => {
    const haystack = `${result.title} ${result.source} ${result.relatedProject} ${result.summary}`.toLowerCase();
    return haystack.includes(needle) || terms.some((term) => haystack.includes(term));
  });
}

export function enterpriseMapDemo(): { nodes: DemoMapNode[]; connections: DemoMapConnection[] } {
  return { nodes: demoMapNodes, connections: demoMapConnections };
}

export function ambientNotifications(): DemoNotification[] {
  return demoNotifications;
}

export function dedupeNotifications(items: DemoNotification[]): DemoNotification[] {
  return Array.from(new Map(items.map((item) => [item.id, item])).values());
}

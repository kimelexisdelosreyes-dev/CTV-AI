import { demoFileResults, demoSearchResults, demoSourceActivity } from "@/demo/data/experience";
import type { DemoSearchCategory, DemoSourceActivity } from "@/demo/types";
import type { RichSearchResult, SearchActionTarget, SearchSource, SearchSuggestion, SearchViewModel } from "./search-types";

const categoryTargets: Record<DemoSearchCategory, SearchActionTarget> = {
  Projects: "operations",
  Files: "files",
  Knowledge: "knowledge",
  People: "overview",
  Workstations: "infrastructure",
  "AI Jobs": "brain",
  Settings: "infrastructure",
};

const categoryOrder: DemoSearchCategory[] = ["Projects", "Files", "Knowledge", "People", "Workstations", "AI Jobs", "Settings"];

const suggestionsByContext: Record<SearchActionTarget, SearchSuggestion[]> = {
  overview: [
    { id: "continue", label: "Continue Working", context: "Workspace", query: "Caloocan Fire Documentary" },
    { id: "priorities", label: "Today's Priorities", context: "Workspace", query: "Storage Warning" },
    { id: "lee", label: "Lee Chin interview", context: "Executive demo", query: "Lee Chin interview" },
  ],
  files: [
    { id: "recent-assets", label: "Recent Assets", context: "Files", query: "Interview_Lee_1987" },
    { id: "missing-transcript", label: "Missing Transcript", context: "Files", query: "No transcript" },
    { id: "archive", label: "Archive", context: "Files", query: "Archive" },
  ],
  knowledge: [
    { id: "indexed", label: "Recently Indexed", context: "Knowledge", query: "Archive interview handling guide" },
    { id: "uploads", label: "Recent Uploads", context: "Knowledge", query: "Production" },
    { id: "summary", label: "AI Summary", context: "Knowledge", query: "AI Summary" },
  ],
  operations: [
    { id: "projects", label: "Recent Projects", context: "Projects", query: "Caloocan Fire Documentary" },
    { id: "sync", label: "Monday sync", context: "Projects", query: "Monday.com" },
    { id: "review", label: "Needs Review", context: "Projects", query: "In review" },
  ],
  brain: [
    { id: "ai-jobs", label: "AI Jobs", context: "My AI", query: "Interview summary prepared" },
    { id: "transcript", label: "Transcript summary", context: "My AI", query: "Transcript" },
    { id: "related", label: "Related interviews", context: "My AI", query: "Related interviews" },
  ],
  assistants: [
    { id: "assistant", label: "AI assistant", context: "My AI", query: "AI Summary" },
    { id: "knowledge", label: "Knowledge help", context: "Assistants", query: "Knowledge Center" },
    { id: "project", label: "Project help", context: "Assistants", query: "Caloocan" },
  ],
  infrastructure: [
    { id: "storage", label: "Storage Warning", context: "Infrastructure", query: "Storage Warning" },
    { id: "workstation", label: "Workstations", context: "Infrastructure", query: "EDIT-WS-02" },
    { id: "services", label: "Enterprise Services", context: "Infrastructure", query: "AI Core" },
  ],
};

const richResults: RichSearchResult[] = [
  {
    id: "project-fire-doc",
    title: "Caloocan Fire Documentary",
    category: "Projects",
    kind: "project",
    iconLabel: "Project",
    status: "In review",
    tone: "processing",
    metadata: ["84% complete", "Owner: Production Team", "Updated yesterday"],
    summary: "Archive restoration project connected to interview footage, OCR output, approved guidance, and AI summaries.",
    action: "Open related project",
    target: "operations",
    progress: 84,
    owner: "Production Team",
    updated: "Yesterday",
    relationships: [
      { label: "Files", value: "4 related assets", tone: "healthy" },
      { label: "Knowledge", value: "1 approved guide", tone: "healthy" },
      { label: "AI Summary", value: "Ready for review", tone: "processing" },
    ],
    preview: [
      { label: "Status", value: "Executive review" },
      { label: "Latest activity", value: "Transcript indexed yesterday" },
      { label: "Next action", value: "Review latest interview summary" },
    ],
  },
  {
    id: "file-lee-chin-interview",
    title: "Interview_Lee_1987.mov",
    category: "Files",
    kind: "file",
    iconLabel: "Master file",
    status: "Indexed offline",
    tone: "offline",
    metadata: ["Master", "CTV-NAS-01", "Related project: Caloocan Fire Documentary"],
    summary: "Long-form Lee Chin interview. Indexed metadata and transcript relationships remain available while the NAS source is offline.",
    action: "Open Enterprise File Discovery",
    target: "files",
    owner: "Production Archive",
    location: "NAS 03 / CTV-NAS-01",
    source: "Enterprise Assets",
    relationships: [
      { label: "Project", value: "Caloocan Fire Documentary", tone: "processing" },
      { label: "Transcript", value: "Available", tone: "healthy" },
      { label: "Storage", value: "Source offline", tone: "offline" },
    ],
    preview: [
      { label: "Owner", value: "Production Archive" },
      { label: "Location", value: "NAS 03 / CTV-NAS-01" },
      { label: "Transcript", value: "Available" },
      { label: "AI Summary", value: "Available" },
      { label: "Latest activity", value: "Indexed yesterday" },
    ],
  },
  {
    id: "knowledge-fire-policy",
    title: "Archive interview handling guide",
    category: "Knowledge",
    kind: "knowledge",
    iconLabel: "Knowledge",
    status: "Approved",
    tone: "healthy",
    metadata: ["Collection: Production", "Related project: Caloocan Fire Documentary", "AI summary available"],
    summary: "Approved source guidance for archive interview handling and restoration review.",
    action: "Open source reference",
    target: "knowledge",
    relationships: [
      { label: "Project", value: "Caloocan Fire Documentary", tone: "processing" },
      { label: "Files", value: "2 referenced assets", tone: "healthy" },
      { label: "People", value: "Production Team", tone: "neutral" },
    ],
    preview: [
      { label: "Collection", value: "Production" },
      { label: "AI summary", value: "Available" },
      { label: "Related project", value: "Caloocan Fire Documentary" },
    ],
  },
  {
    id: "person-mlee",
    title: "Mina Lee",
    category: "People",
    kind: "person",
    iconLabel: "Person",
    status: "Executive Producer",
    tone: "neutral",
    metadata: ["Department: Production", "Assigned project: Caloocan Fire Documentary", "Owner contact"],
    summary: "Executive producer connected to the documentary review and archive restoration decision path.",
    action: "Open profile",
    target: "overview",
    owner: "Production",
    relationships: [
      { label: "Project", value: "Caloocan Fire Documentary", tone: "processing" },
      { label: "AI Job", value: "Interview summary prepared", tone: "healthy" },
      { label: "Knowledge", value: "Handling guide", tone: "healthy" },
    ],
    preview: [
      { label: "Role", value: "Executive Producer" },
      { label: "Department", value: "Production" },
      { label: "Assigned project", value: "Caloocan Fire Documentary" },
    ],
  },
  {
    id: "job-subtitles",
    title: "Interview summary prepared",
    category: "AI Jobs",
    kind: "ai-job",
    iconLabel: "AI job",
    status: "Needs review",
    tone: "processing",
    metadata: ["Source-grounded", "Caloocan Fire Documentary", "Prepared today"],
    summary: "My AI prepared an interview summary from transcript, project context, and approved archive guidance.",
    action: "Review output",
    target: "brain",
    relationships: [
      { label: "File", value: "Interview_Lee_1987.mov", tone: "offline" },
      { label: "Knowledge", value: "Approved guide", tone: "healthy" },
      { label: "Owner", value: "Mina Lee", tone: "neutral" },
    ],
    preview: [
      { label: "Status", value: "Needs review" },
      { label: "Source type", value: "Transcript and Knowledge Center" },
      { label: "Latest activity", value: "Prepared today" },
    ],
  },
  {
    id: "workstation-edit",
    title: "EDIT-WS-02",
    category: "Workstations",
    kind: "workstation",
    iconLabel: "Workstation",
    status: "Offline",
    tone: "offline",
    metadata: ["Proxy cache available", "Last indexed yesterday", "Related file: Interview_Lee_1987_proxy.mp4"],
    summary: "Editing workstation is offline, but indexed proxy metadata remains searchable.",
    action: "Open Enterprise Control Center",
    target: "infrastructure",
    relationships: [
      { label: "File", value: "Interview proxy", tone: "healthy" },
      { label: "Storage", value: "CTV-NAS-01", tone: "offline" },
      { label: "Project", value: "Caloocan Fire Documentary", tone: "processing" },
    ],
    preview: [
      { label: "Health", value: "Offline" },
      { label: "Last sync", value: "Yesterday" },
      { label: "Availability", value: "Indexed metadata only" },
    ],
  },
  {
    id: "settings-search",
    title: "Enterprise Search settings",
    category: "Settings",
    kind: "setting",
    iconLabel: "Setting",
    status: "Current",
    tone: "healthy",
    metadata: ["Search sources", "Keyboard shortcuts", "Demo adapters"],
    summary: "Search configuration area for source visibility, shortcuts, and enterprise indexing preferences.",
    action: "Open settings",
    target: "infrastructure",
    relationships: [
      { label: "Sources", value: "Projects, Files, Knowledge", tone: "healthy" },
      { label: "Shortcut", value: "Ctrl/Cmd+K", tone: "processing" },
      { label: "Demo", value: "Adapters isolated", tone: "warning" },
    ],
    preview: [
      { label: "Status", value: "Current" },
      { label: "Shortcut", value: "Ctrl/Cmd+K" },
      { label: "Availability", value: "Settings destination pending" },
    ],
  },
];

export const defaultSearchHistory = ["Fire Documentary", "Lee Chin", "Drone Footage", "Archive", "Storage Warning", "AI Summary"];

export function searchHistoryFromStorage(value: string | null): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is string => typeof item === "string").slice(0, 8);
  } catch {
    return [];
  }
}

export function updateSearchHistory(history: string[], query: string): string[] {
  const trimmed = query.trim();
  if (!trimmed) return history;
  return [trimmed, ...history.filter((item) => item.toLowerCase() !== trimmed.toLowerCase())].slice(0, 8);
}

export function suggestionsForContext(context: SearchActionTarget): SearchSuggestion[] {
  return suggestionsByContext[context] ?? suggestionsByContext.overview;
}

export function sourceStatus(source: DemoSourceActivity): SearchSource {
  const tone = source.status === "completed" ? "healthy" : source.status === "running" ? "processing" : source.status === "failed" ? "critical" : source.status === "offline" ? "offline" : "warning";
  return {
    id: source.id,
    label: source.name.replace(/^(Searching|Checking)\s/, ""),
    status: source.status,
    tone,
    itemsFound: source.resultsFound,
    time: source.lastIndexed,
    availability: source.connection,
    message: source.message,
  };
}

export function buildSearchViewModel(query: string, context: SearchActionTarget = "overview"): SearchViewModel {
  const normalized = query.trim().toLowerCase();
  const terms = normalized.split(/\s+/).filter(Boolean);
  const seedIds = new Set(demoSearchResults.map((result) => result.id));
  const fileTerms = demoFileResults.map((file) => `${file.title} ${file.summary} ${file.source}`).join(" ").toLowerCase();
  const flatResults = richResults.filter((result) => {
    if (!normalized) return seedIds.has(result.id);
    const haystack = `${result.title} ${result.category} ${result.status} ${result.metadata.join(" ")} ${result.summary} ${result.relationships.map((relationship) => relationship.value).join(" ")} ${fileTerms}`.toLowerCase();
    return haystack.includes(normalized) || terms.some((term) => haystack.includes(term));
  });
  const state = !normalized ? "idle" : flatResults.length === 0 ? "no-results" : flatResults.some((result) => result.tone === "offline" || result.tone === "warning") ? "partial" : "completed";

  return {
    query,
    state,
    flatResults,
    groups: categoryOrder
      .map((category) => ({ category, results: flatResults.filter((result) => result.category === category) }))
      .filter((group) => group.results.length > 0),
    sources: demoSourceActivity.map(sourceStatus),
    suggestions: suggestionsForContext(context),
    announcement: `${flatResults.length} result${flatResults.length === 1 ? "" : "s"} across ${new Set(flatResults.map((result) => result.category)).size} source group${flatResults.length === 1 ? "" : "s"}.`,
  };
}

import type { StatusTone } from "@/design-system";
import type { DemoSearchCategory, DemoStatus } from "@/demo/types";

export type SearchState =
  | "idle"
  | "typing"
  | "searching"
  | "partial"
  | "completed"
  | "offline"
  | "permission-required"
  | "error"
  | "no-results"
  | "loading";

export type SearchResultKind =
  | "project"
  | "file"
  | "knowledge"
  | "person"
  | "workstation"
  | "storage"
  | "ai-job"
  | "service"
  | "setting";

export type SearchActionTarget =
  | "overview"
  | "assistants"
  | "brain"
  | "knowledge"
  | "operations"
  | "files"
  | "infrastructure";

export type SearchSource = {
  id: string;
  label: string;
  status: DemoStatus;
  tone: StatusTone;
  itemsFound: number;
  time: string;
  availability: string;
  message: string;
};

export type SearchRelationship = {
  label: string;
  value: string;
  tone: StatusTone;
};

export type RichSearchResult = {
  id: string;
  title: string;
  category: DemoSearchCategory;
  kind: SearchResultKind;
  iconLabel: string;
  status: string;
  tone: StatusTone;
  metadata: string[];
  summary: string;
  action: string;
  target: SearchActionTarget;
  progress?: number;
  owner?: string;
  updated?: string;
  location?: string;
  source?: string;
  relationships: SearchRelationship[];
  preview: Array<{ label: string; value: string }>;
};

export type SearchSuggestion = {
  id: string;
  label: string;
  context: string;
  query: string;
};

export type SearchViewModel = {
  query: string;
  state: SearchState;
  groups: Array<{ category: DemoSearchCategory; results: RichSearchResult[] }>;
  flatResults: RichSearchResult[];
  sources: SearchSource[];
  suggestions: SearchSuggestion[];
  announcement: string;
};

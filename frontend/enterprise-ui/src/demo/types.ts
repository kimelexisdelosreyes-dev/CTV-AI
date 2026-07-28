export type DemoScenario = "success" | "slow" | "partial" | "offline" | "error";

export type DemoStatus =
  | "idle"
  | "queued"
  | "starting"
  | "running"
  | "waiting"
  | "completed"
  | "warning"
  | "failed"
  | "cancelled"
  | "offline";

export type DemoSearchCategory =
  | "Projects"
  | "Files"
  | "Knowledge"
  | "People"
  | "Workstations"
  | "AI Jobs"
  | "Settings";

export type DemoSearchResult = {
  id: string;
  title: string;
  meta: string;
  category: DemoSearchCategory;
  action: string;
};

export type DemoSourceActivity = {
  id: string;
  name: string;
  status: DemoStatus;
  itemsChecked: number;
  resultsFound: number;
  connection: "online" | "offline" | "permission-limited" | "cloud-only";
  lastIndexed: string;
  message: string;
};

export type DemoFileResult = {
  id: string;
  title: string;
  source: string;
  owner: string;
  path: string;
  availability: "available now" | "indexed but source offline" | "permission required" | "archived" | "cloud-only" | "duplicate";
  version: string;
  copyState: "master" | "working" | "proxy" | "archive" | "duplicate";
  relatedProject: string;
  transcript: string;
  summary: string;
};

export type DemoMapNode = {
  id: string;
  label: string;
  type: "Core" | "Office" | "Workstation" | "Storage" | "Cloud" | "AI Service" | "Integration" | "Knowledge" | "Project" | "Team";
  status: DemoStatus;
  x: number;
  y: number;
  activity: string;
  dependencies: string[];
};

export type DemoMapConnection = {
  from: string;
  to: string;
  status: "connected" | "processing" | "degraded" | "offline" | "synchronization" | "data flow" | "dependency";
};

export type DemoNotification = {
  id: string;
  title: string;
  message: string;
  urgency: "normal" | "warning" | "critical";
};


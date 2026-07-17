const API_ROOT = "http://127.0.0.1:8000/api/v1";

export type User = {
  email: string;
  full_name: string;
  role: "admin" | "manager" | "employee";
  is_active: boolean;
};

export type KnowledgeDocument = {
  id: string;
  filename: string;
  content_type: string;
  category: string;
  uploaded_by: string;
  status: string;
  stage: string;
  progress_percent: number;
  page_count: number;
  pages_processed: number;
  ocr_pages: number;
  chunk_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeStats = {
  total_documents: number;
  ready_documents: number;
  failed_documents: number;
  processing_documents: number;
  total_chunks: number;
  categories: Record<string, number>;
};

export type KnowledgeSource = {
  document_id: string;
  filename: string;
  category: string;
  chunk_index: number;
  page_number: number | null;
  text: string;
  score: number;
};

export type Personalization = {
  applied: boolean;
  job_title: string | null;
  experience_level: string | null;
  preferred_language: string | null;
  response_style: string | null;
  detail_level: string | null;
  skills_used: string[];
  tools_used: string[];
  memories_used: number;
  operational_context_applied: boolean;
  operational_tasks_used: number;
  operational_boards_used: number;
  operational_summary: string | null;
  routed_intent: string;
  routing_confidence: number;
  routed_collections: string[];
  intelligence_sources: string[];
  context_degraded: boolean;
  unavailable_context_components: string[];
  required_context_failure: string | null;
};

export type KnowledgeAskResponse = {
  answer: string;
  sources: KnowledgeSource[];
  personalization: Personalization;
  conversation_id: string | null;
};

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type ConversationMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type ConversationListResponse = {
  conversations: Conversation[];
  limit: number;
  offset: number;
  has_more: boolean;
};

export type ConversationDetailResponse = {
  conversation: Conversation;
  messages: ConversationMessage[];
  limit: number;
  offset: number;
  has_more: boolean;
};

export type ConnectorHealth = {
  name: string;
  status: "healthy" | "degraded" | "unavailable" | "disabled";
  checked_at: string;
  latency_ms: number | null;
  detail: string | null;
};

export type ConnectorProject = {
  external_id: string;
  name: string;
  status: string | null;
  owner_ids: string[];
  start_at: string | null;
  due_at: string | null;
  url: string | null;
  metadata: Record<string, unknown>;
};

export type ConnectorTask = {
  external_id: string;
  title: string;
  status: string | null;
  priority: string | null;
  due_at: string | null;
  assignee_ids: string[];
  project_id: string | null;
  url: string | null;
  metadata: {
    board_name?: string;
    board_url?: string;
    group_id?: string;
    group_title?: string;
    created_at?: string;
    updated_at?: string;
    [key: string]: unknown;
  };
};

export type InfrastructureServiceDetail = {
  status: string;
  category?: string | null;
  model?: string | null;
};

export type InfrastructureServiceStatus =
  | string
  | InfrastructureServiceDetail
  | null;

export type InfrastructureStatus = {
  postgresql?: InfrastructureServiceStatus;
  qdrant?: InfrastructureServiceStatus;
  embedding?: InfrastructureServiceStatus;
};

export type DeveloperStatus = {
  enabled: boolean;
};

export type RoutedCollectionSearchMetric = {
  collection: string | null;
  duration_ms: number | null;
  retrieved_chunk_count: number | null;
};

export type PerformanceEvent = {
  timestamp: string | null;
  outcome: string | null;
  routed_intent: string | null;
  routing_confidence: number | null;
  total_endpoint_ms: number | null;
  intelligence_router_ms: number | null;
  employee_context_ms: number | null;
  monday_operational_context_ms: number | null;
  embedding_ms: number | null;
  qdrant_vector_search_ms: number | null;
  prompt_assembly_ms: number | null;
  ollama_request_ms: number | null;
  prompt_character_count: number | null;
  prompt_size: number | null;
  estimated_input_token_count: number | null;
  estimated_output_token_count: number | null;
  tokens_per_second: number | null;
  answer_character_count: number | null;
  collection_count: number | null;
  retrieved_chunk_count: number | null;
  operational_task_count: number | null;
  routed_collection_searches: RoutedCollectionSearchMetric[];
  model_name: string | null;
  gpu_utilization: number | null;
  cpu_utilization: number | null;
};

export type PerformanceSummary = {
  request_count: number;
  success_count: number;
  failure_count: number;
  average_total_duration_ms: number;
  median_total_duration_ms: number;
  p95_total_duration_ms: number;
  average_ollama_duration_ms: number;
  average_monday_duration_ms: number;
  average_employee_context_duration_ms: number;
  average_embedding_duration_ms: number;
  average_qdrant_duration_ms: number;
  average_estimated_input_tokens: number;
  average_tokens_per_second: number;
  slowest_stage: string | null;
  counts_by_routed_intent: Record<string, number>;
};

export type DeveloperModels = {
  default_model: string;
  available_models: string[];
};

export type ModelBenchmarkResult = {
  model_name: string;
  case_label: string;
  outcome: string;
  total_request_ms: number;
  ollama_request_ms: number;
  estimated_input_tokens: number;
  estimated_output_tokens: number;
  tokens_per_second: number | null;
  answer_character_count: number;
  routed_intent: string | null;
  skipped_no_evidence: boolean;
  error_category: string | null;
};

export type ModelBenchmarkResponse = {
  default_model: string;
  comparison_model: string;
  results: ModelBenchmarkResult[];
};

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("ctv_token") ?? "";
}

export function setToken(token: string): void {
  localStorage.setItem("ctv_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("ctv_token");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);

  if (token) headers.set("Authorization", `Bearer ${token}`);

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? `Request failed (${response.status})`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<void> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const response = await fetch(`${API_ROOT}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });

  if (!response.ok) throw new Error("Incorrect email or password.");

  const payload = await response.json();
  setToken(payload.access_token);
}

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

import type {
  ChatMessage,
  ConversationDetail,
  ConversationSummary,
  DocumentRecord,
  Health,
  QueryResponse,
  User,
} from "@/lib/types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      credentials: "include",
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Can't reach the RetrivAI backend. Make sure it is running on port 8000.", 0);
  }

  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((item) => item.msg).join(" ");
    } catch {
      // Keep the concise status message when the server did not return JSON.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  health: () => request<Health>("/health"),
  me: () => request<User>("/auth/me"),
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<User>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  listDocuments: async () => {
    const response = await request<{ documents: DocumentRecord[]; total: number }>("/documents");
    return response.documents;
  },
  uploadDocument: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<DocumentRecord>("/documents/upload", { method: "POST", body });
  },
  deleteDocument: (documentId: string) =>
    request<void>(`/documents/${encodeURIComponent(documentId)}`, { method: "DELETE" }),
  chat: (question: string, conversationId?: string | null) =>
    request<QueryResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ question, conversation_id: conversationId || null }),
    }),
  getConversations: () => request<ConversationSummary[]>("/chat/conversations"),
  getConversation: (id: string) =>
    request<ConversationDetail>(`/chat/conversations/${encodeURIComponent(id)}`),
  deleteConversation: (id: string) =>
    request<void>(`/chat/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }),
};

export type { ChatMessage };

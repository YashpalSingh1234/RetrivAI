export type User = {
  id: string;
  email: string;
  created_at: string;
};

export type DocumentRecord = {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: "processing" | "ready" | "failed";
  chunk_count: number;
  created_at: string;
  error_message?: string | null;
};

export type SourceCitation = {
  citation_id: string;
  document_id: string;
  document: string;
  page?: number | null;
  chunk_index?: number | null;
  text: string;
  relevance_score: number;
};

export type QueryResponse = {
  answer: string;
  sources: SourceCitation[];
  conversation_id?: string | null;
  generation_mode: "llm" | "extractive" | "insufficient_context";
  warning?: string | null;
  latency_ms: number;
  retrieved_count: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceCitation[];
  created_at: string;
};

export type ConversationSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
};

export type ConversationDetail = ConversationSummary & {
  messages: ChatMessage[];
};

export type Health = {
  status: "ok";
  service: string;
  llm_configured: boolean;
  embedding_model: string;
};

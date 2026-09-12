export interface Book {
  id: string;
  book_id?: string;
  title: string;
  author?: string;
  total_chunks: number;
  chunks_count?: number;
  total_tokens?: number;
  pages?: number;
  sha256?: string;
  file_path?: string;
}

export interface SourceCitation {
  book_title: string;
  chapter?: string;
  page?: number;
  score: number;
  tokens: number;
}

export interface QueryResult {
  query: string;
  response: string;
  sources: SourceCitation[];
  tokens_used: number;
  tokens_saved: number;
  reduction_percentage: number;
  llm_provider: string;
  timestamp?: string;
}

export interface ProjectAnalysisResult {
  project_summary: string;
  book_title: string;
  analysis: string;
  sources: SourceCitation[];
  tokens_used: number;
  tokens_saved: number;
  reduction_percentage: number;
}

export interface OllamaModelInfo {
  name: string;
  size: number;
  parameter_size: string;
  quantization: string;
  family: string;
}

export interface LoadedVRAMModel {
  name: string;
  size_vram: number;
  expires_at?: string;
}

export interface LLMRuntimeState {
  llm_enabled: boolean;
  active_provider: string;
  active_model: string;
  temperature: number;
  ollama_online: boolean;
  ollama_host: string;
  available_models: OllamaModelInfo[];
  loaded_models_vram: LoadedVRAMModel[];
  has_loaded_vram: boolean;
}

export interface SystemLogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'AUDIT' | 'REDUCTION';
  module: string;
  message: string;
  metadata?: Record<string, any>;
}

export interface QueryMetricHistory {
  id: string;
  timestamp: string;
  query: string;
  tokens_used: number;
  tokens_saved: number;
  reduction_percentage: number;
  sources_count: number;
  llm_provider: string;
  duration_ms: number;
}

export interface SystemMetrics {
  uptime_seconds: number;
  total_queries: number;
  total_tokens_used: number;
  total_tokens_saved: number;
  total_book_tokens_scanned: number;
  average_reduction_percentage: number;
  estimated_usd_saved: number;
  recent_queries: QueryMetricHistory[];
}

export interface MCPToolParameter {
  type: string;
  description?: string;
  default?: any;
}

export interface MCPToolDeclaration {
  name: string;
  description: string;
  parameters: {
    type: string;
    properties: Record<string, MCPToolParameter>;
    required?: string[];
  };
}

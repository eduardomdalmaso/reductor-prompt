import { 
  Book, 
  QueryResult, 
  ProjectAnalysisResult, 
  LLMRuntimeState, 
  SystemLogEntry, 
  SystemMetrics, 
  MCPToolDeclaration 
} from '../domain/entities';

const BASE_URL = ''; // Usa proxy configurado no Vite ou raiz relativa

export class ApiClient {
  private static async handleResponse<T>(res: Response): Promise<T> {
    if (!res.ok) {
      let errMsg = `HTTP ${res.status} ${res.statusText}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      } catch {}
      throw new Error(errMsg);
    }
    return res.json();
  }

  // Health
  static async checkHealth(): Promise<{ status: string; service: string }> {
    const res = await fetch(`${BASE_URL}/health`);
    return this.handleResponse(res);
  }

  // Livros
  static async getBooks(): Promise<{ books: Book[]; count: number }> {
    const res = await fetch(`${BASE_URL}/api/v1/books`);
    const data = await this.handleResponse<any>(res);
    const rawBooks = data.books || [];
    const normalizedBooks: Book[] = rawBooks.map((b: any, idx: number) => ({
      id: b.id || b.book_id || `book-${idx}`,
      book_id: b.book_id || b.id || `book-${idx}`,
      title: b.title || 'Livro Sem Título',
      author: b.author || 'N/A',
      total_chunks: b.total_chunks ?? b.chunks_count ?? 0,
      chunks_count: b.chunks_count ?? b.total_chunks ?? 0,
      total_tokens: b.total_tokens ?? ((b.total_chunks ?? b.chunks_count ?? 0) * 120),
      pages: b.pages,
      sha256: b.sha256,
      file_path: b.file_path
    }));
    return { books: normalizedBooks, count: normalizedBooks.length };
  }

  static async triggerIngest(force: boolean = false): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/ingest?force=${force}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return this.handleResponse(res);
  }

  static async fetchMaterials(urls: string, ingestAfter: boolean = false): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/fetch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls, ingest_after: ingestAfter })
    });
    return this.handleResponse(res);
  }

  // Consultas RAG
  static async executeQuery(params: {
    query: string;
    book_filter?: string;
    max_tokens?: number;
    only_context?: boolean;
    llm_provider?: string;
  }): Promise<QueryResult> {
    const res = await fetch(`${BASE_URL}/api/v1/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return this.handleResponse(res);
  }

  // Análise de Projetos
  static async analyzeProject(params: {
    project_description: string;
    book_filter?: string;
    focus_topic?: string;
    max_tokens?: number;
    llm_provider?: string;
  }): Promise<ProjectAnalysisResult> {
    const res = await fetch(`${BASE_URL}/api/v1/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    return this.handleResponse(res);
  }

  // Telemetria & Logs
  static async getMetrics(): Promise<SystemMetrics> {
    const res = await fetch(`${BASE_URL}/api/v1/metrics`);
    return this.handleResponse(res);
  }

  static async getLogs(limit: number = 100, level?: string): Promise<{ logs: SystemLogEntry[] }> {
    const url = new URL(`${window.location.origin}/api/v1/logs`);
    url.searchParams.set('limit', String(limit));
    if (level) url.searchParams.set('level', level);
    const res = await fetch(url.toString());
    return this.handleResponse(res);
  }

  // Gerenciamento de LLM & Ollama VRAM
  static async getLLMStatus(): Promise<LLMRuntimeState> {
    const res = await fetch(`${BASE_URL}/api/v1/llm/status`);
    return this.handleResponse(res);
  }

  static async toggleLLM(enabled: boolean): Promise<LLMRuntimeState> {
    const res = await fetch(`${BASE_URL}/api/v1/llm/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled })
    });
    return this.handleResponse(res);
  }

  static async updateLLMConfig(config: {
    provider?: string;
    model?: string;
    temperature?: number;
    enabled?: boolean;
  }): Promise<LLMRuntimeState> {
    const res = await fetch(`${BASE_URL}/api/v1/llm/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return this.handleResponse(res);
  }

  static async unloadVRAM(modelName?: string): Promise<{ success: boolean; message: string; status: LLMRuntimeState }> {
    const res = await fetch(`${BASE_URL}/api/v1/llm/unload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName })
    });
    return this.handleResponse(res);
  }

  // Hub MCP
  static async getMCPTools(): Promise<{ server_name: string; tools: MCPToolDeclaration[] }> {
    const res = await fetch(`${BASE_URL}/api/v1/mcp/tools`);
    return this.handleResponse(res);
  }

  static async callMCPTool(toolName: string, args: Record<string, any>): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/v1/mcp/call`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool_name: toolName, arguments: args })
    });
    return this.handleResponse(res);
  }
}

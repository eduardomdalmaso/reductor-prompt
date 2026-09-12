import { useState, useEffect, useCallback } from 'react';
import { ApiClient } from '../infrastructure/apiClient';
import { 
  Book, 
  QueryResult, 
  ProjectAnalysisResult, 
  LLMRuntimeState, 
  SystemLogEntry, 
  SystemMetrics, 
  MCPToolDeclaration 
} from '../domain/entities';

export type NavigationTab = 'query' | 'analyze' | 'llm' | 'mcp' | 'books' | 'metrics' | 'logs';

export function useReductorStore() {
  const [activeTab, setActiveTab] = useState<NavigationTab>('query');
  
  // LLM State
  const [llmState, setLlmState] = useState<LLMRuntimeState | null>(null);
  const [isTogglingLLM, setIsTogglingLLM] = useState(false);
  const [isUnloadingVRAM, setIsUnloadingVRAM] = useState(false);

  // Books
  const [books, setBooks] = useState<Book[]>([]);
  const [isLoadingBooks, setIsLoadingBooks] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);

  // Metrics & Logs
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [logs, setLogs] = useState<SystemLogEntry[]>([]);
  const [logFilter, setLogFilter] = useState<string>('');

  // MCP Tools
  const [mcpTools, setMcpTools] = useState<MCPToolDeclaration[]>([]);
  const [isLoadingMCP, setIsLoadingMCP] = useState(false);

  // Query Execution
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryResult[]>([]);

  // Analyze Execution
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<ProjectAnalysisResult | null>(null);

  // General Error / Notification
  const [alertMessage, setAlertMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  const showAlert = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setAlertMessage({ type, text });
    setTimeout(() => {
      setAlertMessage(null);
    }, 4500);
  };

  // Carrega status do LLM
  const fetchLLMStatus = useCallback(async () => {
    try {
      const state = await ApiClient.getLLMStatus();
      setLlmState(state);
    } catch (e: any) {
      console.error("Falha ao buscar status do LLM:", e);
    }
  }, []);

  // Alterna liga/desliga LLM
  const toggleLLM = async (enabled: boolean) => {
    setIsTogglingLLM(true);
    try {
      const updated = await ApiClient.toggleLLM(enabled);
      setLlmState(updated);
      showAlert(
        enabled ? "✨ LLM LIGADO (Inferência ativada com modelo selecionado)" : "⚡ LLM DESLIGADO (Modo Contexto Enxuto / Bypass ativado)",
        enabled ? "success" : "info"
      );
    } catch (e: any) {
      showAlert(`Erro ao alterar estado do LLM: ${e.message}`, 'error');
    } finally {
      setIsTogglingLLM(false);
    }
  };

  // Descarrega VRAM
  const unloadVRAM = async (modelName?: string) => {
    setIsUnloadingVRAM(true);
    try {
      const res = await ApiClient.unloadVRAM(modelName);
      if (res.success) {
        setLlmState(res.status);
        showAlert("🧹 VRAM liberada! Modelo descarregado da GPU.", "success");
      } else {
        showAlert(`Falha ao descarregar VRAM: ${res.message}`, "error");
      }
    } catch (e: any) {
      showAlert(`Erro: ${e.message}`, "error");
    } finally {
      setIsUnloadingVRAM(false);
    }
  };

  // Atualiza Configuração LLM
  const updateLLMConfig = async (config: { provider?: string; model?: string; temperature?: number; enabled?: boolean }) => {
    try {
      const updated = await ApiClient.updateLLMConfig(config);
      setLlmState(updated);
      showAlert("Configuração de LLM atualizada com sucesso!", "success");
    } catch (e: any) {
      showAlert(`Erro ao configurar LLM: ${e.message}`, "error");
    }
  };

  // Carrega Livros
  const fetchBooks = useCallback(async () => {
    setIsLoadingBooks(true);
    try {
      const data = await ApiClient.getBooks();
      setBooks(data.books || []);
    } catch (e: any) {
      console.error("Erro ao carregar livros:", e);
    } finally {
      setIsLoadingBooks(false);
    }
  }, []);

  // Dispara Ingestão
  const runIngest = async (force: boolean = false) => {
    setIsIngesting(true);
    try {
      const res = await ApiClient.triggerIngest(force);
      showAlert(res.message || "Varredura e indexação concluídas!", "success");
      fetchBooks();
      fetchMetrics();
    } catch (e: any) {
      showAlert(`Erro na ingestão: ${e.message}`, "error");
    } finally {
      setIsIngesting(false);
    }
  };

  // Carrega Métricas
  const fetchMetrics = useCallback(async () => {
    try {
      const data = await ApiClient.getMetrics();
      setMetrics(data);
    } catch (e: any) {
      console.error("Erro ao buscar métricas:", e);
    }
  }, []);

  // Carrega Logs
  const fetchLogs = useCallback(async () => {
    try {
      const data = await ApiClient.getLogs(100, logFilter || undefined);
      setLogs(data.logs || []);
    } catch (e: any) {
      console.error("Erro ao carregar logs:", e);
    }
  }, [logFilter]);

  // Carrega Ferramentas MCP
  const fetchMCPTools = useCallback(async () => {
    setIsLoadingMCP(true);
    try {
      const data = await ApiClient.getMCPTools();
      setMcpTools(data.tools || []);
    } catch (e: any) {
      console.error("Erro ao carregar ferramentas MCP:", e);
    } finally {
      setIsLoadingMCP(false);
    }
  }, []);

  // Executar Consulta RAG
  const executeQuery = async (params: {
    query: string;
    book_filter?: string;
    max_tokens?: number;
    only_context?: boolean;
    llm_provider?: string;
  }) => {
    setIsQuerying(true);
    try {
      const res = await ApiClient.executeQuery(params);
      const withTime = { ...res, timestamp: new Date().toLocaleTimeString() };
      setQueryResult(withTime);
      setQueryHistory(prev => [withTime, ...prev.slice(0, 19)]);
      fetchMetrics();
      fetchLogs();
      fetchLLMStatus();
      showAlert(`Consulta concluída! Redução de ${res.reduction_percentage}% de tokens.`, 'success');
      return withTime;
    } catch (e: any) {
      showAlert(`Erro na consulta: ${e.message}`, 'error');
      throw e;
    } finally {
      setIsQuerying(false);
    }
  };

  // Executar Análise de Projeto
  const analyzeProject = async (params: {
    project_description: string;
    book_filter?: string;
    focus_topic?: string;
    max_tokens?: number;
    llm_provider?: string;
  }) => {
    setIsAnalyzing(true);
    try {
      const res = await ApiClient.analyzeProject(params);
      setAnalysisResult(res);
      fetchMetrics();
      fetchLogs();
      showAlert(`Análise cruzada concluída com sucesso!`, 'success');
      return res;
    } catch (e: any) {
      showAlert(`Erro na análise do projeto: ${e.message}`, 'error');
      throw e;
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Efeito inicial e polling suave de telemetria
  useEffect(() => {
    fetchLLMStatus();
    fetchBooks();
    fetchMetrics();
    fetchLogs();
    fetchMCPTools();

    const interval = setInterval(() => {
      fetchLLMStatus();
      fetchMetrics();
      fetchLogs();
    }, 4000);

    return () => clearInterval(interval);
  }, [fetchLLMStatus, fetchBooks, fetchMetrics, fetchLogs, fetchMCPTools]);

  return {
    activeTab,
    setActiveTab,
    llmState,
    isTogglingLLM,
    isUnloadingVRAM,
    toggleLLM,
    unloadVRAM,
    updateLLMConfig,
    fetchLLMStatus,
    books,
    isLoadingBooks,
    isIngesting,
    fetchBooks,
    runIngest,
    metrics,
    fetchMetrics,
    logs,
    logFilter,
    setLogFilter,
    fetchLogs,
    mcpTools,
    isLoadingMCP,
    isQuerying,
    queryResult,
    queryHistory,
    executeQuery,
    isAnalyzing,
    analysisResult,
    analyzeProject,
    alertMessage,
    showAlert
  };
}

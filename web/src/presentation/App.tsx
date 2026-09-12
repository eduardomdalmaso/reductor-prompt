import React from 'react';
import { useReductorStore } from '../application/useReductorStore';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { QueryPlaygroundView } from './views/QueryPlaygroundView';
import { ProjectAnalyzerView } from './views/ProjectAnalyzerView';
import { LLMControllerView } from './views/LLMControllerView';
import { MCPHubView } from './views/MCPHubView';
import { BooksCatalogView } from './views/BooksCatalogView';
import { MetricsDashboardView } from './views/MetricsDashboardView';
import { LogsConsoleView } from './views/LogsConsoleView';
import { AlertCircle, CheckCircle, Info } from 'lucide-react';

export const App: React.FC = () => {
  const {
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
    executeQuery,
    isAnalyzing,
    analysisResult,
    analyzeProject,
    alertMessage,
    showAlert
  } = useReductorStore();

  const handleRefreshAll = () => {
    fetchLLMStatus();
    fetchBooks();
    fetchMetrics();
    fetchLogs();
    showAlert("Dados sincronizados com o servidor!", "info");
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Toast Alert Banner */}
      {alertMessage && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '24px',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '12px 18px',
          borderRadius: '12px',
          background: alertMessage.type === 'success' 
            ? 'rgba(16, 185, 129, 0.95)' 
            : alertMessage.type === 'error' 
              ? 'rgba(244, 63, 94, 0.95)' 
              : 'rgba(99, 102, 241, 0.95)',
          color: '#ffffff',
          fontWeight: 600,
          fontSize: '0.85rem',
          boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
          backdropFilter: 'blur(8px)',
          animation: 'pulseGlow 0.3s ease-out'
        }}>
          {alertMessage.type === 'success' && <CheckCircle size={18} />}
          {alertMessage.type === 'error' && <AlertCircle size={18} />}
          {alertMessage.type === 'info' && <Info size={18} />}
          <span>{alertMessage.text}</span>
        </div>
      )}

      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        llmState={llmState}
        isTogglingLLM={isTogglingLLM}
        onToggleLLM={toggleLLM}
        booksCount={books.length}
      />

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: '100vh' }}>
        <Navbar
          activeTab={activeTab}
          llmState={llmState}
          metrics={metrics}
          onRefresh={handleRefreshAll}
        />

        <main style={{ flex: 1, padding: '28px', maxWidth: '1440px', width: '100%', margin: '0 auto', boxSizing: 'border-box' }}>
          {activeTab === 'query' && (
            <QueryPlaygroundView
              books={books}
              llmState={llmState}
              onExecuteQuery={executeQuery}
              isQuerying={isQuerying}
              queryResult={queryResult}
            />
          )}

          {activeTab === 'analyze' && (
            <ProjectAnalyzerView
              books={books}
              llmState={llmState}
              onAnalyzeProject={analyzeProject}
              isAnalyzing={isAnalyzing}
              analysisResult={analysisResult}
            />
          )}

          {activeTab === 'llm' && (
            <LLMControllerView
              llmState={llmState}
              isTogglingLLM={isTogglingLLM}
              isUnloadingVRAM={isUnloadingVRAM}
              onToggleLLM={toggleLLM}
              onUnloadVRAM={unloadVRAM}
              onUpdateConfig={updateLLMConfig}
              onRefresh={fetchLLMStatus}
            />
          )}

          {activeTab === 'mcp' && (
            <MCPHubView
              tools={mcpTools}
              isLoading={isLoadingMCP}
            />
          )}

          {activeTab === 'books' && (
            <BooksCatalogView
              books={books}
              isLoading={isLoadingBooks}
              isIngesting={isIngesting}
              onRefresh={fetchBooks}
              onRunIngest={runIngest}
              onShowAlert={showAlert}
            />
          )}

          {activeTab === 'metrics' && (
            <MetricsDashboardView
              metrics={metrics}
            />
          )}

          {activeTab === 'logs' && (
            <LogsConsoleView
              logs={logs}
              logFilter={logFilter}
              setLogFilter={setLogFilter}
              onRefresh={fetchLogs}
            />
          )}
        </main>
      </div>
    </div>
  );
};

import React from 'react';
import { RefreshCw, Zap, ShieldCheck, Sparkles } from 'lucide-react';
import { NavigationTab } from '../../application/useReductorStore';
import { LLMRuntimeState, SystemMetrics } from '../../domain/entities';

interface NavbarProps {
  activeTab: NavigationTab;
  llmState: LLMRuntimeState | null;
  metrics: SystemMetrics | null;
  onRefresh: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  llmState,
  metrics,
  onRefresh
}) => {
  const getTabTitle = () => {
    switch (activeTab) {
      case 'query': return 'RAG Playground & Consultas Semânticas';
      case 'analyze': return 'Diagnóstico e Análise Cruzada de Projetos';
      case 'llm': return 'Controle de Hardware, LLM & Memória VRAM (Ollama)';
      case 'mcp': return 'Model Context Protocol (MCP) Hub & Ferramentas';
      case 'books': return 'Catálogo de Livros Técnicos & Ingestão Dinâmica';
      case 'metrics': return 'Dashboard de Economia de Tokens & Performance';
      case 'logs': return 'Terminal e Auditoria de Logs em Tempo Real';
      default: return 'ReductorPrompt';
    }
  };

  return (
    <header style={{
      height: '68px',
      padding: '0 28px',
      background: 'rgba(15, 20, 34, 0.75)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 10
    }}>
      {/* Title & Path */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff' }}>
          {getTabTitle()}
        </h2>
      </div>

      {/* Badges & Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Token Savings Quick Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          borderRadius: '20px',
          background: 'rgba(16, 185, 129, 0.12)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          color: 'var(--accent-emerald)',
          fontSize: '0.8rem',
          fontWeight: 700
        }}>
          <Sparkles size={14} />
          <span>Economia Média: {metrics?.average_reduction_percentage || 98.4}%</span>
        </div>

        {/* LLM Status Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          borderRadius: '20px',
          background: llmState?.llm_enabled ? 'rgba(99, 102, 241, 0.12)' : 'rgba(244, 63, 94, 0.12)',
          border: `1px solid ${llmState?.llm_enabled ? 'rgba(99, 102, 241, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
          color: llmState?.llm_enabled ? 'var(--text-accent)' : '#fb7185',
          fontSize: '0.8rem',
          fontWeight: 600
        }}>
          <Zap size={14} />
          <span>{llmState?.llm_enabled ? `LLM: ${llmState.active_model}` : 'LLM: BYPASS (Context Only)'}</span>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          className="btn btn-secondary"
          style={{ padding: '8px 12px' }}
          title="Atualizar dados do sistema"
        >
          <RefreshCw size={15} />
        </button>
      </div>
    </header>
  );
};

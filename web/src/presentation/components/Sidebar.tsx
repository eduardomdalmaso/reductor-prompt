import React from 'react';
import { 
  MessageSquare, 
  Cpu, 
  Boxes, 
  BookOpen, 
  BarChart3, 
  Terminal, 
  Compass, 
  Power, 
  Sparkles,
  Zap,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import { NavigationTab } from '../../application/useReductorStore';
import { LLMRuntimeState } from '../../domain/entities';

interface SidebarProps {
  activeTab: NavigationTab;
  setActiveTab: (tab: NavigationTab) => void;
  llmState: LLMRuntimeState | null;
  isTogglingLLM: boolean;
  onToggleLLM: (enabled: boolean) => void;
  booksCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  llmState,
  isTogglingLLM,
  onToggleLLM,
  booksCount
}) => {
  const navItems = [
    { id: 'query' as NavigationTab, label: 'RAG Playground', icon: MessageSquare, badge: 'RAG' },
    { id: 'analyze' as NavigationTab, label: 'Análise de Projetos', icon: Compass, badge: '5-DDD' },
    { id: 'llm' as NavigationTab, label: 'LLM & Hardware Engine', icon: Cpu, badge: llmState?.llm_enabled ? 'ON' : 'OFF' },
    { id: 'mcp' as NavigationTab, label: 'Hub MCP Tools', icon: Boxes, badge: '3 Tools' },
    { id: 'books' as NavigationTab, label: 'Catálogo de Livros', icon: BookOpen, badge: `${booksCount}` },
    { id: 'metrics' as NavigationTab, label: 'Economia de Tokens', icon: BarChart3, badge: '>98%' },
    { id: 'logs' as NavigationTab, label: 'Terminal de Logs', icon: Terminal, badge: 'Live' },
  ];

  return (
    <aside style={{
      width: '280px',
      minWidth: '280px',
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      position: 'sticky',
      top: 0,
      userSelect: 'none',
      zIndex: 20
    }}>
      {/* Brand Header */}
      <div style={{
        padding: '24px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '12px',
          background: 'var(--gradient-brand)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 16px rgba(99, 102, 241, 0.4)'
        }}>
          <Sparkles size={22} color="#ffffff" />
        </div>
        <div>
          <h1 style={{ fontSize: '1.1rem', fontWeight: 700, letterSpacing: '-0.02em', color: '#ffffff' }}>
            ReductorPrompt
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
            <span className="pulse-indicator pulse-green" />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              RAG DDD v2.0
            </span>
          </div>
        </div>
      </div>

      {/* Navigation List */}
      <nav style={{ flex: 1, padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '4px', overflowY: 'auto' }}>
        <div style={{ padding: '0 8px 8px', fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Menu Principal
        </div>
        {navItems.map(item => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                padding: '10px 14px',
                borderRadius: '10px',
                border: 'none',
                background: isActive ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.9rem',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                position: 'relative'
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = 'transparent';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Icon size={18} color={isActive ? 'var(--accent-primary)' : 'var(--text-muted)'} />
                <span>{item.label}</span>
              </div>
              <span style={{
                fontSize: '0.7rem',
                padding: '2px 7px',
                borderRadius: '6px',
                background: isActive ? 'var(--accent-primary)' : 'rgba(255, 255, 255, 0.06)',
                color: isActive ? '#ffffff' : 'var(--text-muted)',
                fontWeight: 600
              }}>
                {item.badge}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Quick LLM Power Switch Box */}
      <div style={{
        padding: '16px',
        margin: '12px',
        background: 'var(--bg-tertiary)',
        borderRadius: '14px',
        border: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={16} color={llmState?.llm_enabled ? 'var(--accent-amber)' : 'var(--text-muted)'} />
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              LLM Inference
            </span>
          </div>
          <span style={{
            fontSize: '0.7rem',
            padding: '2px 8px',
            borderRadius: '12px',
            fontWeight: 700,
            background: llmState?.llm_enabled ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.2)',
            color: llmState?.llm_enabled ? 'var(--accent-emerald)' : 'var(--text-muted)'
          }}>
            {llmState?.llm_enabled ? 'ATIVO' : 'BYPASS'}
          </span>
        </div>

        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
          {llmState?.llm_enabled 
            ? `Modelo: ${llmState.active_model}`
            : 'Economia total: retorna apenas contexto sem chamar LLM.'}
        </p>

        <button
          onClick={() => onToggleLLM(!llmState?.llm_enabled)}
          disabled={isTogglingLLM}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '8px 12px',
            borderRadius: '8px',
            border: 'none',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '0.8rem',
            transition: 'all 0.2s ease',
            background: llmState?.llm_enabled ? 'rgba(244, 63, 94, 0.2)' : 'var(--gradient-brand)',
            color: llmState?.llm_enabled ? '#fb7185' : '#ffffff'
          }}
        >
          <Power size={14} />
          {isTogglingLLM ? 'Alterando...' : (llmState?.llm_enabled ? 'Desligar LLM (Context-Only)' : 'Ligar LLM')}
        </button>

        {/* Health Indicators */}
        <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '4px', borderTop: '1px solid rgba(255,255,255,0.05)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle2 size={12} color="var(--accent-emerald)" /> ChromaDB: 8001
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {llmState?.ollama_online ? (
              <CheckCircle2 size={12} color="var(--accent-emerald)" />
            ) : (
              <XCircle size={12} color="var(--accent-rose)" />
            )}
            Ollama: 11434
          </span>
        </div>
      </div>
    </aside>
  );
};

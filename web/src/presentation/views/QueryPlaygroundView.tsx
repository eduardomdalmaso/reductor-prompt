import React, { useState } from 'react';
import { Send, Sparkles, Filter, Sliders, CheckCircle, Zap, ShieldAlert } from 'lucide-react';
import { Book, QueryResult, LLMRuntimeState } from '../../domain/entities';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

interface QueryPlaygroundViewProps {
  books: Book[];
  llmState: LLMRuntimeState | null;
  onExecuteQuery: (params: {
    query: string;
    book_filter?: string;
    max_tokens?: number;
    only_context?: boolean;
    llm_provider?: string;
  }) => Promise<QueryResult>;
  isQuerying: boolean;
  queryResult: QueryResult | null;
}

export const QueryPlaygroundView: React.FC<QueryPlaygroundViewProps> = ({
  books,
  llmState,
  onExecuteQuery,
  isQuerying,
  queryResult
}) => {
  const [query, setQuery] = useState('');
  const [selectedBook, setSelectedBook] = useState('');
  const [maxTokens, setMaxTokens] = useState(1500);
  const [queryMode, setQueryMode] = useState<'standard' | 'fast' | 'only_context'>('standard');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isQuerying) return;

    onExecuteQuery({
      query: query.trim(),
      book_filter: selectedBook || undefined,
      max_tokens: maxTokens,
      only_context: queryMode === 'only_context' || !llmState?.llm_enabled
    });
  };

  const sampleQueries = [
    "Qual o padrão de concorrência recomendado em Rust vs Go?",
    "Como mitigar gargalos de escrita e lock contention no PostgreSQL?",
    "Quais os princípios essenciais de Clean Architecture e Ports & Adapters?",
    "Como estruturar pipelines de NLP com tokenização e Transformers?"
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Query Input Box */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Pergunta ou Conceito Técnico a Consultar na Biblioteca:
            </label>
            <div style={{ position: 'relative' }}>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ex: Como evitar gargalos de IO no PostgreSQL quando há milhares de writes simultâneos?"
                rows={3}
                style={{ resize: 'vertical', minHeight: '80px', paddingRight: '120px' }}
              />
              <button
                type="submit"
                disabled={isQuerying || !query.trim()}
                className="btn btn-primary"
                style={{
                  position: 'absolute',
                  right: '12px',
                  bottom: '12px',
                  padding: '8px 18px'
                }}
              >
                {isQuerying ? (
                  <>
                    <span className="pulse-indicator pulse-amber" />
                    Buscando...
                  </>
                ) : (
                  <>
                    <Send size={15} />
                    Consultar
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Configuration Row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', alignItems: 'center' }}>
            {/* Book Filter */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                <Filter size={13} /> Filtrar por Livro (Opcional):
              </label>
              <select value={selectedBook} onChange={(e) => setSelectedBook(e.target.value)}>
                <option value="">Todos os Livros ({books.length})</option>
                {books.map((b, idx) => (
                  <option key={`${b.id || b.book_id || idx}-${b.title}`} value={b.title}>
                    {b.title.length > 40 ? b.title.substring(0, 40) + '...' : b.title}
                  </option>
                ))}
              </select>
            </div>

            {/* Mode Selector */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                <Zap size={13} /> Modo de Execução:
              </label>
              <select value={queryMode} onChange={(e: any) => setQueryMode(e.target.value)}>
                <option value="standard">Padrão (Multi-Query + Síntese LLM)</option>
                <option value="fast">Rápido (Busca Direta + LLM)</option>
                <option value="only_context">Apenas Contexto Enxuto (Zero LLM)</option>
              </select>
            </div>

            {/* Max Tokens Slider */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Sliders size={13} /> Token Budget:</span>
                <span style={{ color: 'var(--text-accent)' }}>{maxTokens} tokens</span>
              </div>
              <input
                type="range"
                min="500"
                max="4000"
                step="250"
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
                style={{ padding: 0, height: '6px' }}
              />
            </div>
          </div>

          {/* Quick Sample Queries */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center', paddingTop: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Sugestões rápidas:</span>
            {sampleQueries.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setQuery(q)}
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '16px',
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent-primary)';
                  e.currentTarget.style.color = '#ffffff';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </form>
      </div>

      {/* Result Panel */}
      {queryResult && (
        <div className="glass-panel" style={{ padding: '28px' }}>
          {/* Header Stats Bar */}
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingBottom: '16px',
            marginBottom: '20px',
            borderBottom: '1px solid var(--border-subtle)',
            gap: '12px'
          }}>
            <div>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Pergunta
              </span>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', marginTop: '2px' }}>
                "{queryResult.query}"
              </h3>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                padding: '6px 12px',
                borderRadius: '8px',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: 'var(--accent-emerald)',
                fontSize: '0.8rem',
                fontWeight: 700
              }}>
                ⚡ Economia: {queryResult.reduction_percentage}%
              </div>
              <div style={{
                padding: '6px 12px',
                borderRadius: '8px',
                background: 'rgba(99, 102, 241, 0.15)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                color: 'var(--text-accent)',
                fontSize: '0.8rem',
                fontWeight: 600
              }}>
                🔢 {queryResult.tokens_used} tokens enviados (vs {queryResult.tokens_saved.toLocaleString()} economizados)
              </div>
            </div>
          </div>

          {/* Render Response */}
          <MarkdownRenderer content={queryResult.response} sources={queryResult.sources} />
        </div>
      )}
    </div>
  );
};

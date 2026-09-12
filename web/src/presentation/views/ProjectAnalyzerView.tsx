import React, { useState } from 'react';
import { Compass, Sparkles, Send, BookOpen, Layers, CheckCircle2 } from 'lucide-react';
import { Book, ProjectAnalysisResult, LLMRuntimeState } from '../../domain/entities';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

interface ProjectAnalyzerViewProps {
  books: Book[];
  llmState: LLMRuntimeState | null;
  onAnalyzeProject: (params: {
    project_description: string;
    book_filter?: string;
    focus_topic?: string;
    max_tokens?: number;
    llm_provider?: string;
  }) => Promise<ProjectAnalysisResult>;
  isAnalyzing: boolean;
  analysisResult: ProjectAnalysisResult | null;
}

export const ProjectAnalyzerView: React.FC<ProjectAnalyzerViewProps> = ({
  books,
  llmState,
  onAnalyzeProject,
  isAnalyzing,
  analysisResult
}) => {
  const [projectDescription, setProjectDescription] = useState(
    "Temos um serviço de ingestão de eventos em FastAPI e Python que consome 50.000 mensagens por segundo do Apache Kafka e precisa persistir em lote no PostgreSQL garantindo idempotência e baixo overhead de CPU."
  );
  const [focusTopic, setFocusTopic] = useState("gargalos de escrita, particionamento e concorrência");
  const [selectedBook, setSelectedBook] = useState("");
  const [maxTokens, setMaxTokens] = useState(2500);

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectDescription.trim() || isAnalyzing) return;

    onAnalyzeProject({
      project_description: projectDescription.trim(),
      book_filter: selectedBook || undefined,
      focus_topic: focusTopic.trim() || undefined,
      max_tokens: maxTokens,
      llm_provider: llmState?.active_provider
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Intro Panel */}
      <div className="glass-panel" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(6, 182, 212, 0.04) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <Compass size={22} color="var(--accent-secondary)" />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff' }}>
            Diagnóstico Arquitetural e Alinhamento Teórico (5 Pilares DDD)
          </h3>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          Submeta a descrição do seu software, stack ou pipeline. O ReductorPrompt cruzará sua implementação com as melhores práticas extraídas dos livros técnicos de engenharia de software e banco de dados.
        </p>
      </div>

      {/* Input Form */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <form onSubmit={handleAnalyze} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Descrição da Arquitetura / Código / Pipeline do Projeto:
            </label>
            <textarea
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              rows={4}
              placeholder="Descreva seu projeto, banco de dados, gargalo atual ou arquitetura..."
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                Tópico ou Foco Específico (Opcional):
              </label>
              <input
                type="text"
                value={focusTopic}
                onChange={(e) => setFocusTopic(e.target.value)}
                placeholder="Ex: concorrência, latência, DDD, particionamento"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                Livro Específico de Referência (Opcional):
              </label>
              <select value={selectedBook} onChange={(e) => setSelectedBook(e.target.value)}>
                <option value="">Cruzar com todo o acervo ({books.length} livros)</option>
                {books.map((b, idx) => (
                  <option key={`${b.id || b.book_id || idx}-${b.title}`} value={b.title}>
                    {b.title.length > 40 ? b.title.substring(0, 40) + '...' : b.title}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '8px' }}>
            <button
              type="submit"
              disabled={isAnalyzing || !projectDescription.trim()}
              className="btn btn-primary"
              style={{ padding: '12px 24px', fontSize: '0.95rem' }}
            >
              {isAnalyzing ? (
                <>
                  <span className="pulse-indicator pulse-amber" />
                  Realizando Diagnóstico Cruzado...
                </>
              ) : (
                <>
                  <Compass size={18} />
                  Executar Análise de Projeto
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Analysis Output */}
      {analysisResult && (
        <div className="glass-panel" style={{ padding: '28px' }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingBottom: '16px',
            marginBottom: '20px',
            borderBottom: '1px solid var(--border-subtle)'
          }}>
            <div>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Relatório de Diagnóstico
              </span>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff', marginTop: '2px' }}>
                {analysisResult.book_title || 'Análise Multidisciplinar'}
              </h3>
            </div>

            <div style={{
              padding: '6px 12px',
              borderRadius: '8px',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: 'var(--accent-emerald)',
              fontSize: '0.8rem',
              fontWeight: 700
            }}>
              ⚡ {analysisResult.reduction_percentage}% tokens economizados
            </div>
          </div>

          <MarkdownRenderer content={analysisResult.analysis} sources={analysisResult.sources} />
        </div>
      )}
    </div>
  );
};

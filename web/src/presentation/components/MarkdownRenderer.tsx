import React, { useState } from 'react';
import { Copy, Check, BookOpen, Layers } from 'lucide-react';
import { SourceCitation } from '../../domain/entities';

interface MarkdownRendererProps {
  content: string;
  sources?: SourceCitation[];
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, sources }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Renderizador básico e limpo para markdown técnico
  const renderFormattedText = (text: string) => {
    const lines = text.split('\n');
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    const elements: React.ReactNode[] = [];

    lines.forEach((line, idx) => {
      if (line.startsWith('```')) {
        if (inCodeBlock) {
          elements.push(
            <pre key={`code-${idx}`} style={{
              background: '#070a10',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              padding: '14px',
              margin: '12px 0',
              overflowX: 'auto',
              color: '#38bdf8',
              fontSize: '0.85rem'
            }}>
              <code>{codeBlockContent.join('\n')}</code>
            </pre>
          );
          codeBlockContent = [];
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
        }
        return;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        return;
      }

      if (line.startsWith('### ')) {
        elements.push(
          <h4 key={idx} style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-accent)', margin: '14px 0 6px' }}>
            {line.replace('### ', '')}
          </h4>
        );
      } else if (line.startsWith('## ')) {
        elements.push(
          <h3 key={idx} style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff', margin: '18px 0 8px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '4px' }}>
            {line.replace('## ', '')}
          </h3>
        );
      } else if (line.startsWith('# ')) {
        elements.push(
          <h2 key={idx} style={{ fontSize: '1.35rem', fontWeight: 800, color: '#ffffff', margin: '20px 0 10px' }}>
            {line.replace('# ', '')}
          </h2>
        );
      } else if (line.startsWith('- ') || line.startsWith('* ') || line.startsWith('• ')) {
        elements.push(
          <li key={idx} style={{ marginLeft: '20px', marginBottom: '6px', color: 'var(--text-primary)', lineHeight: 1.6 }}>
            {line.substring(2)}
          </li>
        );
      } else if (line.trim() === '') {
        elements.push(<div key={idx} style={{ height: '8px' }} />);
      } else {
        elements.push(
          <p key={idx} style={{ color: 'var(--text-primary)', lineHeight: 1.65, marginBottom: '6px', fontSize: '0.92rem' }}>
            {line}
          </p>
        );
      }
    });

    return elements;
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Copy Button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
        <button
          onClick={handleCopy}
          className="btn btn-secondary"
          style={{ padding: '6px 12px', fontSize: '0.75rem' }}
        >
          {copied ? <Check size={13} color="var(--accent-emerald)" /> : <Copy size={13} />}
          {copied ? 'Copiado!' : 'Copiar Resposta'}
        </button>
      </div>

      {/* Main Text Content */}
      <div style={{ lineHeight: 1.65 }}>
        {renderFormattedText(content)}
      </div>

      {/* Sources Section */}
      {sources && sources.length > 0 && (
        <div style={{
          marginTop: '24px',
          paddingTop: '16px',
          borderTop: '1px solid var(--border-subtle)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <BookOpen size={16} color="var(--accent-secondary)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Fontes & Trechos Cirúrgicos Consultados ({sources.length})
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '10px' }}>
            {sources.map((s, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px',
                  background: 'rgba(15, 20, 34, 0.6)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#ffffff', lineHeight: 1.3 }}>
                    📖 {s.book_title}
                  </span>
                  <span style={{
                    fontSize: '0.7rem',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: 'rgba(99, 102, 241, 0.2)',
                    color: 'var(--text-accent)',
                    fontWeight: 700
                  }}>
                    Sim: {s.score}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '10px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {s.chapter && <span>📑 {s.chapter}</span>}
                  {s.page && <span>📄 Pág. {s.page}</span>}
                  <span>🔢 {s.tokens} tokens</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState } from 'react';
import { BookOpen, RefreshCw, Download, Search, HardDrive, FileText, CheckCircle2, Layers } from 'lucide-react';
import { Book } from '../../domain/entities';
import { ApiClient } from '../../infrastructure/apiClient';

interface BooksCatalogViewProps {
  books: Book[];
  isLoading: boolean;
  isIngesting: boolean;
  onRefresh: () => void;
  onRunIngest: (force?: boolean) => void;
  onShowAlert: (text: string, type?: 'success' | 'error' | 'info') => void;
}

export const BooksCatalogView: React.FC<BooksCatalogViewProps> = ({
  books,
  isLoading,
  isIngesting,
  onRefresh,
  onRunIngest,
  onShowAlert
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [fetchUrl, setFetchUrl] = useState('');
  const [autoIngestAfterFetch, setAutoIngestAfterFetch] = useState(true);
  const [isFetching, setIsFetching] = useState(false);

  const filteredBooks = books.filter(b =>
    b.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (b.author && b.author.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const totalChunks = books.reduce((acc, b) => acc + (b.total_chunks || 0), 0);
  const totalTokens = books.reduce((acc, b) => acc + (b.total_tokens || 0), 0);

  const handleFetch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fetchUrl.trim() || isFetching) return;

    setIsFetching(true);
    try {
      const res = await ApiClient.fetchMaterials(fetchUrl.trim(), autoIngestAfterFetch);
      onShowAlert(`Download concluído: ${res.downloaded || 0} arquivos processados!`, 'success');
      setFetchUrl('');
      onRefresh();
    } catch (e: any) {
      onShowAlert(`Erro no download: ${e.message}`, 'error');
    } finally {
      setIsFetching(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Overview & Actions */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BookOpen size={22} color="var(--accent-secondary)" />
            Acervo Técnico Indexado ({books.length} Livros / Documentos)
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {totalChunks.toLocaleString()} chunks vetoriais | ~{totalTokens.toLocaleString()} tokens de conhecimento indexados no ChromaDB.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => onRunIngest(false)}
            disabled={isIngesting}
            className="btn btn-primary"
          >
            <RefreshCw size={15} className={isIngesting ? 'pulse-indicator' : ''} />
            {isIngesting ? 'Indexando...' : 'Re-indexar Banco'}
          </button>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="btn btn-secondary"
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Dynamic Fetcher Section */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Download size={18} color="var(--accent-emerald)" /> Downloader Dinâmico de Livros / Papers (GitHub & URLs)
        </h3>
        <form onSubmit={handleFetch} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <input
            type="text"
            value={fetchUrl}
            onChange={(e) => setFetchUrl(e.target.value)}
            placeholder="Ex: https://arxiv.org/pdf/2401.05566.pdf ou pasta do GitHub"
            style={{ flex: 1, minWidth: '280px' }}
          />
          <button
            type="submit"
            disabled={isFetching || !fetchUrl.trim()}
            className="btn btn-primary"
          >
            {isFetching ? 'Baixando...' : 'Baixar e Indexar'}
          </button>
        </form>
      </div>

      {/* Search Filter */}
      <div style={{ position: 'relative' }}>
        <Search size={18} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--text-muted)' }} />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Buscar no acervo por título, assunto ou autor..."
          style={{ paddingLeft: '44px' }}
        />
      </div>

      {/* Books Card Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
        {filteredBooks.map((b, idx) => {
          const bookId = b.id || b.book_id || `book-${idx}`;
          const chunks = b.total_chunks ?? b.chunks_count ?? 0;
          return (
            <div
              key={bookId}
              className="glass-panel"
              style={{
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '14px'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <span style={{
                    fontSize: '0.75rem',
                    padding: '3px 9px',
                    borderRadius: '6px',
                    background: 'rgba(99, 102, 241, 0.18)',
                    color: 'var(--text-accent)',
                    fontWeight: 700
                  }}>
                    CHUNKS: {chunks}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {b.pages ? `${b.pages} págs` : 'PDF/Epub'}
                  </span>
                </div>

                <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', lineHeight: 1.4 }}>
                  {b.title}
                </h4>
              </div>

              <div style={{
                paddingTop: '12px',
                borderTop: '1px solid rgba(255,255,255,0.05)',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '0.75rem',
                color: 'var(--text-muted)'
              }}>
                <span>ID: {bookId.length > 8 ? bookId.substring(0, 8) + '...' : bookId}</span>
                <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>Vetorial OK</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

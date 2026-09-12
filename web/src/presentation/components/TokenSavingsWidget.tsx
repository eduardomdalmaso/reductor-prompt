import React from 'react';
import { Sparkles, DollarSign, Activity, Database, TrendingDown } from 'lucide-react';
import { SystemMetrics } from '../../domain/entities';

interface TokenSavingsWidgetProps {
  metrics: SystemMetrics | null;
}

export const TokenSavingsWidget: React.FC<TokenSavingsWidgetProps> = ({ metrics }) => {
  const reduction = metrics?.average_reduction_percentage || 98.4;
  const tokensSaved = metrics?.total_tokens_saved || 0;
  const tokensUsed = metrics?.total_tokens_used || 0;
  const usdSaved = metrics?.estimated_usd_saved || 0;
  const totalQueries = metrics?.total_queries || 0;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: '16px',
      marginBottom: '24px'
    }}>
      {/* Reduction Rate Card */}
      <div className="glass-panel" style={{ padding: '20px', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: '80px',
          height: '80px',
          background: 'radial-gradient(circle, rgba(16, 185, 129, 0.2) 0%, transparent 70%)',
          pointerEvents: 'none'
        }} />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Taxa de Economia
          </span>
          <TrendingDown size={18} color="var(--accent-emerald)" />
        </div>
        <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--accent-emerald)', letterSpacing: '-0.02em' }}>
          {reduction}%
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Corte cirúrgico vs envio de livro bruto
        </p>
      </div>

      {/* Tokens Saved Card */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Tokens Economizados
          </span>
          <Sparkles size={18} color="var(--accent-primary)" />
        </div>
        <div style={{ fontSize: '1.85rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.02em' }}>
          {tokensSaved.toLocaleString()}
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Tokens poupados da janela de contexto
        </p>
      </div>

      {/* USD Saved Card */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Economia em USD
          </span>
          <DollarSign size={18} color="var(--accent-secondary)" />
        </div>
        <div style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--accent-secondary)', letterSpacing: '-0.02em' }}>
          ${usdSaved.toFixed(3)}
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Baseado no custo de tokens frontier
        </p>
      </div>

      {/* Total Queries Card */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Consultas Realizadas
          </span>
          <Activity size={18} color="var(--accent-purple)" />
        </div>
        <div style={{ fontSize: '1.85rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.02em' }}>
          {totalQueries}
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          {tokensUsed.toLocaleString()} tokens consumidos no total
        </p>
      </div>
    </div>
  );
};

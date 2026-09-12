import React from 'react';
import { BarChart3, TrendingDown, DollarSign, Activity, Clock, ShieldCheck, Zap } from 'lucide-react';
import { SystemMetrics } from '../../domain/entities';
import { TokenSavingsWidget } from '../components/TokenSavingsWidget';

interface MetricsDashboardViewProps {
  metrics: SystemMetrics | null;
}

export const MetricsDashboardView: React.FC<MetricsDashboardViewProps> = ({ metrics }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Widgets */}
      <TokenSavingsWidget metrics={metrics} />

      {/* Reduction Ratio Comparison Card */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <TrendingDown size={20} color="var(--accent-emerald)" /> Eficiência de Compressão Semântica
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Janela Bruta de Livro (Sem ReductorPrompt)</span>
              <span style={{ fontWeight: 700, color: '#fb7185' }}>~100.000 a 500.000 tokens / consulta</span>
            </div>
            <div style={{ height: '10px', background: 'rgba(255,255,255,0.06)', borderRadius: '5px', overflow: 'hidden' }}>
              <div style={{ width: '100%', height: '100%', background: '#fb7185' }} />
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Extrato Cirúrgico Comprimido (Com ReductorPrompt)</span>
              <span style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>~800 a 2.000 tokens (&gt;98% economia)</span>
            </div>
            <div style={{ height: '10px', background: 'rgba(255,255,255,0.06)', borderRadius: '5px', overflow: 'hidden' }}>
              <div style={{ width: '2%', minWidth: '16px', height: '100%', background: 'var(--accent-emerald)', borderRadius: '5px' }} />
            </div>
          </div>
        </div>
      </div>

      {/* Query History Table */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock size={18} color="var(--accent-secondary)" /> Histórico Recente de Consultas e Reduções
        </h3>

        {metrics?.recent_queries && metrics.recent_queries.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px 12px' }}>Horário</th>
                  <th style={{ padding: '10px 12px' }}>Consulta / Tópico</th>
                  <th style={{ padding: '10px 12px' }}>Tokens Usados</th>
                  <th style={{ padding: '10px 12px' }}>Tokens Poupados</th>
                  <th style={{ padding: '10px 12px' }}>Corte (%)</th>
                  <th style={{ padding: '10px 12px' }}>Latência</th>
                  <th style={{ padding: '10px 12px' }}>Provedor</th>
                </tr>
              </thead>
              <tbody>
                {metrics.recent_queries.map((q, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{q.timestamp}</td>
                    <td style={{ padding: '12px', color: '#ffffff', fontWeight: 600, maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {q.query}
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-accent)' }}>{q.tokens_used}</td>
                    <td style={{ padding: '12px', color: 'var(--accent-emerald)', fontWeight: 600 }}>+{q.tokens_saved.toLocaleString()}</td>
                    <td style={{ padding: '12px', color: 'var(--accent-emerald)', fontWeight: 700 }}>{q.reduction_percentage}%</td>
                    <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{q.duration_ms}ms</td>
                    <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>{q.llm_provider}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Nenhuma consulta registrada ainda na sessão atual.
          </p>
        )}
      </div>
    </div>
  );
};

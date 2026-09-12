import React from 'react';
import { QueryMetricHistory } from '../../domain/entities';
import { TrendingUp, Clock } from 'lucide-react';

interface TokenChartProps {
  queries: QueryMetricHistory[];
}

export const TokenChart: React.FC<TokenChartProps> = ({ queries }) => {
  if (!queries || queries.length === 0) {
    return null;
  }

  // Pega até as últimas 15 consultas em ordem cronológica
  const data = [...queries].reverse().slice(-15);
  const maxTokensSaved = Math.max(...data.map(d => d.tokens_saved), 1000);
  const maxDuration = Math.max(...data.map(d => d.duration_ms), 50);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginBottom: '20px' }}>
      {/* Gráfico 1: Tokens Economizados por Consulta */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <TrendingUp size={15} color="var(--accent-emerald)" /> Tokens Economizados (Últimas Consultas)
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)', fontWeight: 700 }}>
            Pico: {maxTokensSaved.toLocaleString()}
          </span>
        </div>

        {/* Barras SVG */}
        <div style={{ display: 'flex', alignItems: 'flex-end', height: '120px', gap: '6px', paddingTop: '10px' }}>
          {data.map((item, idx) => {
            const heightPercent = Math.max((item.tokens_saved / maxTokensSaved) * 100, 8);
            return (
              <div
                key={idx}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  height: '100%',
                  justifyContent: 'flex-end',
                  position: 'relative'
                }}
                title={`${item.timestamp}: ${item.tokens_saved.toLocaleString()} tokens poupados (${item.reduction_percentage}%)`}
              >
                <div
                  style={{
                    width: '100%',
                    height: `${heightPercent}%`,
                    background: 'linear-gradient(180deg, var(--accent-emerald) 0%, rgba(16, 185, 129, 0.3) 100%)',
                    borderRadius: '4px 4px 2px 2px',
                    transition: 'all 0.3s ease'
                  }}
                />
                <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px', whiteSpace: 'nowrap' }}>
                  {item.timestamp.split(':')[1]}m
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Gráfico 2: Latência de Resposta (ms) */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Clock size={15} color="var(--accent-secondary)" /> Latência do Pipeline RAG (ms)
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--accent-secondary)', fontWeight: 700 }}>
            Máx: {maxDuration.toFixed(0)}ms
          </span>
        </div>

        {/* Barras SVG */}
        <div style={{ display: 'flex', alignItems: 'flex-end', height: '120px', gap: '6px', paddingTop: '10px' }}>
          {data.map((item, idx) => {
            const heightPercent = Math.max((item.duration_ms / maxDuration) * 100, 8);
            return (
              <div
                key={idx}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  height: '100%',
                  justifyContent: 'flex-end',
                  position: 'relative'
                }}
                title={`${item.timestamp}: ${item.duration_ms}ms (${item.llm_provider})`}
              >
                <div
                  style={{
                    width: '100%',
                    height: `${heightPercent}%`,
                    background: 'linear-gradient(180deg, var(--accent-secondary) 0%, rgba(6, 182, 212, 0.25) 100%)',
                    borderRadius: '4px 4px 2px 2px',
                    transition: 'all 0.3s ease'
                  }}
                />
                <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px', whiteSpace: 'nowrap' }}>
                  {item.timestamp.split(':')[1]}m
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

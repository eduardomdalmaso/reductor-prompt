import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Filter, RefreshCw, Trash2, ArrowDown } from 'lucide-react';
import { SystemLogEntry } from '../../domain/entities';

interface LogsConsoleViewProps {
  logs: SystemLogEntry[];
  logFilter: string;
  setLogFilter: (filter: string) => void;
  onRefresh: () => void;
}

export const LogsConsoleView: React.FC<LogsConsoleViewProps> = ({
  logs,
  logFilter,
  setLogFilter,
  onRefresh
}) => {
  const [autoScroll, setAutoScroll] = useState(true);
  const [searchLog, setSearchLog] = useState('');
  const logEndRef = useRef<HTMLDivElement>(null);

  const filteredLogs = logs.filter(l => {
    if (logFilter && l.level !== logFilter) return false;
    if (searchLog && !l.message.toLowerCase().includes(searchLog.toLowerCase()) && !l.module.toLowerCase().includes(searchLog.toLowerCase())) return false;
    return true;
  });

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'INFO': return '#38bdf8';
      case 'REDUCTION': return 'var(--accent-emerald)';
      case 'WARN': return 'var(--accent-amber)';
      case 'ERROR': return '#fb7185';
      case 'AUDIT': return 'var(--accent-purple)';
      default: return 'var(--text-secondary)';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Console Controls */}
      <div className="glass-panel" style={{ padding: '16px 20px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Terminal size={20} color="var(--accent-emerald)" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>
            Terminal de Telemetria & Logs ({filteredLogs.length})
          </h3>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Level Filter */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {['', 'INFO', 'REDUCTION', 'WARN', 'ERROR'].map(lvl => (
              <button
                key={lvl}
                onClick={() => setLogFilter(lvl)}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: logFilter === lvl ? 'var(--accent-primary)' : 'rgba(255,255,255,0.06)',
                  color: logFilter === lvl ? '#ffffff' : 'var(--text-secondary)'
                }}
              >
                {lvl || 'TODOS'}
              </button>
            ))}
          </div>

          <input
            type="text"
            value={searchLog}
            onChange={(e) => setSearchLog(e.target.value)}
            placeholder="Filtrar mensagem..."
            style={{ width: '160px', padding: '6px 10px', fontSize: '0.75rem' }}
          />

          <button
            onClick={onRefresh}
            className="btn btn-secondary"
            style={{ padding: '6px 10px', fontSize: '0.75rem' }}
            title="Recarregar logs"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* Terminal Display */}
      <div style={{
        background: '#070a10',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '14px',
        padding: '20px',
        height: 'calc(100vh - 260px)',
        minHeight: '400px',
        overflowY: 'auto',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.8rem',
        boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.6)'
      }}>
        {filteredLogs.length > 0 ? (
          filteredLogs.map(log => (
            <div
              key={log.id}
              style={{
                display: 'flex',
                gap: '12px',
                padding: '4px 0',
                lineHeight: 1.5,
                borderBottom: '1px solid rgba(255,255,255,0.02)'
              }}
            >
              <span style={{ color: 'var(--text-muted)', minWidth: '135px' }}>
                {log.timestamp}
              </span>
              <span style={{
                color: getLevelColor(log.level),
                fontWeight: 700,
                minWidth: '95px'
              }}>
                [{log.level}]
              </span>
              <span style={{ color: 'var(--text-accent)', minWidth: '120px' }}>
                {log.module}:
              </span>
              <span style={{ color: '#f8fafc', flex: 1 }}>
                {log.message}
              </span>
            </div>
          ))
        ) : (
          <div style={{ color: 'var(--text-muted)', padding: '20px', textAlign: 'center' }}>
            Nenhum registro de log encontrado para os filtros selecionados.
          </div>
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};

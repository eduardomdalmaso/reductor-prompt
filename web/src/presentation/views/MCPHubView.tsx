import React, { useState } from 'react';
import { Boxes, Play, Copy, Check, Terminal, Code2, Sparkles, CheckCircle2 } from 'lucide-react';
import { MCPToolDeclaration } from '../../domain/entities';
import { ApiClient } from '../../infrastructure/apiClient';

interface MCPHubViewProps {
  tools: MCPToolDeclaration[];
  isLoading: boolean;
}

export const MCPHubView: React.FC<MCPHubViewProps> = ({ tools, isLoading }) => {
  const [selectedTool, setSelectedTool] = useState<string>(tools[0]?.name || 'search_books');
  const [toolArgs, setToolArgs] = useState<string>('{\n  "query": "Como mitigar gargalos de escrita no PostgreSQL?",\n  "max_tokens": 1500\n}');
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [copiedConfig, setCopiedConfig] = useState(false);

  const mcpConfigJson = JSON.stringify({
    "mcpServers": {
      "reductor-books": {
        "command": "/home/hades/miniconda3/envs/reductor-prompt/bin/python",
        "args": ["/home/hades/Documents/ReductorPrompt/mcp_server.py"]
      }
    }
  }, null, 2);

  const handleCopyConfig = () => {
    navigator.clipboard.writeText(mcpConfigJson);
    setCopiedConfig(true);
    setTimeout(() => setCopiedConfig(false), 2000);
  };

  const handleToolSelect = (toolName: string) => {
    setSelectedTool(toolName);
    if (toolName === 'search_books') {
      setToolArgs('{\n  "query": "Como mitigar gargalos de escrita no PostgreSQL?",\n  "max_tokens": 1500\n}');
    } else if (toolName === 'analyze_project_with_books') {
      setToolArgs('{\n  "project_description": "API em FastAPI consumindo 50k eventos/s do Kafka com inserções no Postgres",\n  "topic": "gargalos de escrita e partições"\n}');
    } else if (toolName === 'list_indexed_books') {
      setToolArgs('{}');
    }
  };

  const handleExecute = async () => {
    setIsExecuting(true);
    setExecutionResult(null);
    try {
      const parsedArgs = toolArgs.trim() ? JSON.parse(toolArgs) : {};
      const res = await ApiClient.callMCPTool(selectedTool, parsedArgs);
      setExecutionResult(res);
    } catch (e: any) {
      setExecutionResult({ error: e.message });
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Banner */}
      <div className="glass-panel" style={{
        padding: '24px',
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(168, 85, 247, 0.05) 100%)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <Boxes size={24} color="var(--accent-primary)" />
          <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#ffffff' }}>
            Hub de Ferramentas MCP (Model Context Protocol)
          </h2>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          O ReductorPrompt expõe ferramentas cirúrgicas via protocolo MCP para IDEs (VSCode, Antigravity, Claude Desktop, Cursor), garantindo corte de mais de 98% de tokens nas consultas a livros.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        {/* Available MCP Tools List */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Code2 size={18} color="var(--accent-secondary)" /> Ferramentas Registradas ({tools.length})
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {tools.map((tool) => {
              const isSelected = selectedTool === tool.name;
              return (
                <div
                  key={tool.name}
                  onClick={() => handleToolSelect(tool.name)}
                  style={{
                    padding: '14px',
                    borderRadius: '12px',
                    border: isSelected ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                    background: isSelected ? 'rgba(99, 102, 241, 0.12)' : 'rgba(15, 20, 34, 0.6)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.9rem', fontWeight: 700, color: isSelected ? 'var(--text-accent)' : '#ffffff', fontFamily: 'var(--font-mono)' }}>
                      {tool.name}()
                    </span>
                    <span style={{
                      fontSize: '0.65rem',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: 'rgba(255,255,255,0.06)',
                      color: 'var(--text-muted)'
                    }}>
                      MCP Tool
                    </span>
                  </div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {tool.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* IDE Config Snippet */}
        <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={18} color="var(--accent-emerald)" /> Configuração IDE (mcpServers)
            </h3>
            <button
              onClick={handleCopyConfig}
              className="btn btn-secondary"
              style={{ padding: '6px 10px', fontSize: '0.75rem' }}
            >
              {copiedConfig ? <Check size={12} color="var(--accent-emerald)" /> : <Copy size={12} />}
              {copiedConfig ? 'Copiado!' : 'Copiar JSON'}
            </button>
          </div>

          <pre style={{
            background: '#070a10',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '10px',
            padding: '14px',
            fontSize: '0.75rem',
            color: '#38bdf8',
            flex: 1,
            overflowX: 'auto'
          }}>
            <code>{mcpConfigJson}</code>
          </pre>
        </div>
      </div>

      {/* Interactive MCP Runner */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', marginBottom: '14px' }}>
          Playground de Execução da Tool: <span style={{ color: 'var(--text-accent)', fontFamily: 'var(--font-mono)' }}>{selectedTool}</span>
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          {/* Input Arguments */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Argumentos da Ferramenta (JSON):
            </label>
            <textarea
              value={toolArgs}
              onChange={(e) => setToolArgs(e.target.value)}
              rows={8}
              style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}
            />
            <button
              onClick={handleExecute}
              disabled={isExecuting}
              className="btn btn-primary"
              style={{ marginTop: '12px', width: '100%' }}
            >
              {isExecuting ? (
                <>
                  <span className="pulse-indicator pulse-amber" />
                  Executando Tool MCP...
                </>
              ) : (
                <>
                  <Play size={15} />
                  Executar Chamada MCP
                </>
              )}
            </button>
          </div>

          {/* Result Box */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Retorno Estruturado:
            </label>
            <div style={{
              background: '#070a10',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '10px',
              padding: '14px',
              minHeight: '190px',
              maxHeight: '360px',
              overflowY: 'auto',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              color: '#f8fafc',
              whiteSpace: 'pre-wrap'
            }}>
              {executionResult ? (
                typeof executionResult.result === 'string' ? (
                  executionResult.result
                ) : (
                  JSON.stringify(executionResult, null, 2)
                )
              ) : (
                <span style={{ color: 'var(--text-muted)' }}>
                  Aguardando execução... Clique em 'Executar Chamada MCP' para testar.
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

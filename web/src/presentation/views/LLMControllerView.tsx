import React, { useState } from 'react';
import { 
  Cpu, 
  Power, 
  Trash2, 
  CheckCircle2, 
  AlertTriangle, 
  Zap, 
  Server, 
  HardDrive,
  RefreshCw,
  Layers,
  Thermometer
} from 'lucide-react';
import { LLMRuntimeState } from '../../domain/entities';

interface LLMControllerViewProps {
  llmState: LLMRuntimeState | null;
  isTogglingLLM: boolean;
  isUnloadingVRAM: boolean;
  onToggleLLM: (enabled: boolean) => void;
  onUnloadVRAM: (modelName?: string) => void;
  onUpdateConfig: (config: { provider?: string; model?: string; temperature?: number; enabled?: boolean }) => void;
  onRefresh: () => void;
}

export const LLMControllerView: React.FC<LLMControllerViewProps> = ({
  llmState,
  isTogglingLLM,
  isUnloadingVRAM,
  onToggleLLM,
  onUnloadVRAM,
  onUpdateConfig,
  onRefresh
}) => {
  const [selectedProvider, setSelectedProvider] = useState(llmState?.active_provider || 'ollama');
  const [selectedModel, setSelectedModel] = useState(llmState?.active_model || 'qwen2.5-coder:32b');
  const [temp, setTemp] = useState(llmState?.temperature || 0.2);

  const handleSaveConfig = () => {
    onUpdateConfig({
      provider: selectedProvider,
      model: selectedModel,
      temperature: temp,
      enabled: llmState?.llm_enabled
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Main Master Power Control Banner */}
      <div className="glass-panel" style={{
        padding: '32px',
        background: llmState?.llm_enabled 
          ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(6, 182, 212, 0.08) 100%)'
          : 'linear-gradient(135deg, rgba(244, 63, 94, 0.12) 0%, rgba(30, 39, 64, 0.4) 100%)',
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '20px',
            background: llmState?.llm_enabled ? 'var(--gradient-brand)' : 'rgba(244, 63, 94, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: llmState?.llm_enabled ? '0 8px 32px rgba(99, 102, 241, 0.45)' : 'none',
            border: llmState?.llm_enabled ? 'none' : '1px solid rgba(244, 63, 94, 0.4)'
          }}>
            <Power size={32} color={llmState?.llm_enabled ? '#ffffff' : '#fb7185'} />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff' }}>
                {llmState?.llm_enabled ? 'LLM INFERENCE LIGADO' : 'LLM INFERENCE DESLIGADO'}
              </h2>
              <span style={{
                padding: '3px 10px',
                borderRadius: '12px',
                fontSize: '0.75rem',
                fontWeight: 700,
                background: llmState?.llm_enabled ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                color: llmState?.llm_enabled ? 'var(--accent-emerald)' : '#fb7185'
              }}>
                {llmState?.llm_enabled ? 'Inferência Ativa' : 'Bypass / Contexto Enxuto'}
              </span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '6px', maxWidth: '600px', lineHeight: 1.4 }}>
              {llmState?.llm_enabled
                ? `O RAG busca o contexto reduzido cirúrgico nos livros e envia para a LLM (${llmState.active_model}) gerar a resposta final com síntese técnica.`
                : 'O RAG recupera apenas o extrato enxuto e estruturado dos livros sem acionar inferência de modelo (Zero uso de GPU/VRAM e Zero custo de API).'}
            </p>
          </div>
        </div>

        {/* Master Action Toggle */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={() => onToggleLLM(!llmState?.llm_enabled)}
            disabled={isTogglingLLM}
            className="btn"
            style={{
              padding: '14px 28px',
              fontSize: '1rem',
              fontWeight: 700,
              background: llmState?.llm_enabled ? 'rgba(244, 63, 94, 0.2)' : 'var(--gradient-brand)',
              color: llmState?.llm_enabled ? '#fb7185' : '#ffffff',
              border: llmState?.llm_enabled ? '1px solid rgba(244, 63, 94, 0.4)' : 'none',
              boxShadow: llmState?.llm_enabled ? 'none' : '0 4px 20px rgba(99, 102, 241, 0.4)'
            }}
          >
            <Power size={18} />
            {isTogglingLLM ? 'Alterando...' : (llmState?.llm_enabled ? 'Desligar LLM (Ativar Bypass)' : 'Ligar LLM')}
          </button>
        </div>
      </div>

      {/* Grid: Ollama VRAM Controller & Model Selection */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        {/* VRAM & Memory Management Card */}
        <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <HardDrive size={20} color="var(--accent-secondary)" />
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff' }}>
                Gerenciador de VRAM / GPU (Ollama)
              </h3>
            </div>
            <button onClick={onRefresh} className="btn btn-secondary" style={{ padding: '6px 10px' }}>
              <RefreshCw size={13} />
            </button>
          </div>

          <div style={{
            padding: '16px',
            background: 'rgba(15, 20, 34, 0.6)',
            borderRadius: '10px',
            border: '1px solid var(--border-subtle)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Status do Daemon Ollama:</span>
              <span style={{
                fontSize: '0.8rem',
                fontWeight: 700,
                color: llmState?.ollama_online ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                <span className={`pulse-indicator ${llmState?.ollama_online ? 'pulse-green' : 'pulse-rose'}`} />
                {llmState?.ollama_online ? 'Online (Porta 11434)' : 'Offline / Inacessível'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Modelos Carregados na VRAM:</span>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#ffffff' }}>
                {llmState?.loaded_models_vram?.length || 0} ativo(s)
              </span>
            </div>

            {llmState?.loaded_models_vram && llmState.loaded_models_vram.length > 0 ? (
              <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {llmState.loaded_models_vram.map((m, i) => (
                  <div key={i} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 12px',
                    background: 'rgba(99, 102, 241, 0.1)',
                    borderRadius: '8px',
                    border: '1px solid rgba(99, 102, 241, 0.2)'
                  }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#ffffff' }}>
                      🔥 {m.name}
                    </span>
                    <button
                      onClick={() => onUnloadVRAM(m.name)}
                      disabled={isUnloadingVRAM}
                      className="btn btn-danger"
                      style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                    >
                      <Trash2 size={12} /> Descarregar VRAM
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                Nenhum modelo consumindo VRAM no momento. A memória da GPU está 100% livre.
              </p>
            )}
          </div>

          <button
            onClick={() => onUnloadVRAM()}
            disabled={isUnloadingVRAM || !llmState?.ollama_online}
            className="btn btn-secondary"
            style={{ width: '100%' }}
          >
            <Trash2 size={14} />
            {isUnloadingVRAM ? 'Descarregando VRAM...' : 'Liberar Toda a VRAM (keep_alive: 0)'}
          </button>
        </div>

        {/* Runtime Configuration Card */}
        <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Server size={20} color="var(--accent-primary)" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff' }}>
              Configuração Ativa de Inferência
            </h3>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Provedor Principal:
            </label>
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
            >
              <option value="ollama">Ollama Local (Offline / RTX GPU)</option>
              <option value="gemini">Google Gemini API (Nuvem)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Modelo Selecionado:
            </label>
            {selectedProvider === 'ollama' ? (
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {llmState?.available_models && llmState.available_models.length > 0 ? (
                  llmState.available_models.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.name} ({m.parameter_size} - {m.quantization})
                    </option>
                  ))
                ) : (
                  <option value="qwen2.5-coder:32b">qwen2.5-coder:32b</option>
                )}
              </select>
            ) : (
              <input
                type="text"
                value="gemini-2.5-flash"
                disabled
              />
            )}
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Thermometer size={14} /> Temperatura de Raciocínio:
              </span>
              <span style={{ color: 'var(--text-accent)' }}>{temp}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={temp}
              onChange={(e) => setTemp(Number(e.target.value))}
              style={{ padding: 0, height: '6px' }}
            />
          </div>

          <button
            onClick={handleSaveConfig}
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 'auto' }}
          >
            Salvar e Aplicar Configuração
          </button>
        </div>
      </div>

      {/* Installed Models Catalog in Ollama */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={18} color="var(--accent-primary)" /> Modelos Instalados no Host Local ({llmState?.available_models?.length || 0})
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
          {llmState?.available_models && llmState.available_models.length > 0 ? (
            llmState.available_models.map((m, idx) => (
              <div
                key={idx}
                style={{
                  padding: '14px',
                  background: 'rgba(15, 20, 34, 0.6)',
                  borderRadius: '12px',
                  border: m.name === llmState.active_model ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff' }}>
                    {m.name}
                  </span>
                  {m.name === llmState.active_model && (
                    <span style={{
                      fontSize: '0.65rem',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: 'var(--accent-primary)',
                      color: '#ffffff',
                      fontWeight: 700
                    }}>
                      ATIVO
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>Parâmetros: {m.parameter_size}</span>
                  <span>•</span>
                  <span>Quant: {m.quantization}</span>
                  <span>•</span>
                  <span>Tam: {(m.size / (1024 * 1024 * 1024)).toFixed(2)} GB</span>
                </div>
              </div>
            ))
          ) : (
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Nenhum modelo retornado pelo Ollama.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

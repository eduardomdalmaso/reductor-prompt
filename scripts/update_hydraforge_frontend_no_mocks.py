import os
from pathlib import Path

FORGE_DIR = Path(r"C:\Users\hades\Documents\HydraForge")
SRC_DIR = FORGE_DIR / "web" / "src"

# 1. API Client (src/api/client.ts)
api_client_ts = """const API_BASE = 'http://localhost:8088/api';

export interface CameraItem {
  id: string;
  name: string;
  type: string;
  url: string;
  resolution: string;
  fps: number;
  status: 'online' | 'offline';
  analytics: string[];
}

export interface DatasetMetrics {
  total_images: number;
  total_labels: number;
  missing_labels: number;
  orphan_labels: number;
  corrupt_images: number;
  format: string;
  split_train: number;
  split_val: number;
  class_distribution: { class_id: string; count: number }[];
}

export interface ModelBenchmarkItem {
  name: string;
  family: string;
  params: string;
  flops: string;
  mAP50: number;
  mAP50_95: number;
  fps: number;
  latency_ms: number;
  isCustom: boolean;
}

export const api = {
  // Cameras
  async getCameras(): Promise<CameraItem[]> {
    try {
      const res = await fetch(`${API_BASE}/cameras`);
      return res.ok ? await res.json() : [];
    } catch {
      return [];
    }
  },
  async addCamera(cam: { name: string; type: string; url: string }): Promise<CameraItem | null> {
    try {
      const res = await fetch(`${API_BASE}/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cam),
      });
      return res.ok ? await res.json() : null;
    } catch {
      return null;
    }
  },
  async deleteCamera(id: string): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE}/cameras/${id}`, { method: 'DELETE' });
      return res.ok;
    } catch {
      return false;
    }
  },
  async getWebcams(): Promise<{ id: string; name: string; url: string }[]> {
    try {
      const res = await fetch(`${API_BASE}/cameras/webcams`);
      return res.ok ? await res.json() : [];
    } catch {
      return [];
    }
  },
  async getOnvifCameras(): Promise<{ name: string; url: string; ip: string }[]> {
    try {
      const res = await fetch(`${API_BASE}/cameras/onvif-scan`);
      return res.ok ? await res.json() : [];
    } catch {
      return [];
    }
  },

  // Datasets
  async validateDatasetPath(folder_path: string): Promise<{ valid: boolean; error?: string; metrics: DatasetMetrics | null }> {
    try {
      const res = await fetch(`${API_BASE}/datasets/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path }),
      });
      return res.ok ? await res.json() : { valid: false, error: 'Falha ao conectar na API', metrics: null };
    } catch {
      return { valid: false, error: 'Erro de rede', metrics: null };
    }
  },

  // Models
  async getBenchmarks(): Promise<ModelBenchmarkItem[]> {
    try {
      const res = await fetch(`${API_BASE}/models/benchmarks`);
      return res.ok ? await res.json() : [];
    } catch {
      return [];
    }
  },
  async runLiveBenchmark(model_name: string) {
    try {
      const res = await fetch(`${API_BASE}/models/benchmark-run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name }),
      });
      return res.ok ? await res.json() : null;
    } catch {
      return null;
    }
  },

  // Export
  async getExportableModels(): Promise<string[]> {
    try {
      const res = await fetch(`${API_BASE}/export/models`);
      return res.ok ? await res.json() : [];
    } catch {
      return [];
    }
  },
  async startExport(payload: { model_name: string; format: string; precision: string; imgsz: number }) {
    try {
      const res = await fetch(`${API_BASE}/export/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      return res.ok ? await res.json() : null;
    } catch {
      return null;
    }
  }
};
"""

# 2. CamerasPage.tsx
cameras_page_ts = """import React, { useState, useEffect } from 'react';
import { api, CameraItem } from '../api/client';
import { AddCameraModal } from '../components/cameras/AddCameraModal';
import { LiveAnalyticsViewer } from '../components/cameras/LiveAnalyticsViewer';

export const CamerasPage: React.FC = () => {
  const [cameras, setCameras] = useState<CameraItem[]>([]);
  const [selectedCam, setSelectedCam] = useState<CameraItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const loadCameras = async () => {
    setIsLoading(true);
    const data = await api.getCameras();
    setCameras(data);
    if (data.length > 0 && !selectedCam) {
      setSelectedCam(data[0]);
    } else if (data.length === 0) {
      setSelectedCam(null);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    loadCameras();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Deseja realmente remover esta câmera?')) {
      await api.deleteCamera(id);
      loadCameras();
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: 0 }}>
            Gerenciador de <span style={{ color: 'var(--color-cyber-cyan)' }}>Câmeras & Streams</span>
          </h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '13px', margin: '4px 0 0 0' }}>
            Processamento de vídeo em tempo real com overlay de bounding box integrado (Zero-Delay).
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          style={{
            background: 'var(--color-cyber-cyan)',
            color: '#000',
            border: 'none',
            padding: '10px 18px',
            borderRadius: 'var(--radius-sm)',
            fontFamily: 'var(--font-display)',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          + Adicionar Câmera
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '14px', fontWeight: 600, color: 'var(--color-text-muted)' }}>
            CÂMERAS CADASTRADAS ({cameras.length})
          </div>

          {isLoading ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-muted)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)' }}>
              Carregando dispositivos...
            </div>
          ) : cameras.length === 0 ? (
            <div style={{ padding: '32px 20px', textAlign: 'center', background: 'rgba(255,255,255,0.02)', border: '1px dashed var(--color-border)', borderRadius: 'var(--radius-md)' }}>
              <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', margin: 0 }}>Nenhuma câmera cadastrada.</p>
              <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginTop: '6px' }}>Clique no botão acima para adicionar RTSP ou Webcam.</p>
            </div>
          ) : (
            cameras.map((cam) => (
              <div
                key={cam.id}
                onClick={() => setSelectedCam(cam)}
                style={{
                  background: selectedCam?.id === cam.id ? 'rgba(0, 240, 255, 0.08)' : 'rgba(18, 24, 38, 0.6)',
                  border: `1px solid ${selectedCam?.id === cam.id ? 'var(--color-cyber-cyan)' : 'var(--color-border)'}`,
                  padding: '14px',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, color: '#fff', fontSize: '14px' }}>{cam.name}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '10px', background: 'rgba(0, 240, 255, 0.1)', color: 'var(--color-cyber-cyan)', padding: '2px 6px', borderRadius: '4px' }}>
                      {cam.type}
                    </span>
                    <button onClick={(e) => handleDelete(cam.id, e)} style={{ background: 'transparent', border: 'none', color: '#ff4444', cursor: 'pointer', fontSize: '12px' }}>✕</button>
                  </div>
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {cam.url}
                </div>
              </div>
            ))
          )}
        </div>

        <div>
          {selectedCam ? (
            <LiveAnalyticsViewer camera={selectedCam} />
          ) : (
            <div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(18, 24, 38, 0.4)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
              <span style={{ color: 'var(--color-text-muted)', fontSize: '14px' }}>Selecione ou adicione uma câmera para visualizar o analítico</span>
            </div>
          )}
        </div>
      </div>

      {isModalOpen && (
        <AddCameraModal
          onClose={() => setIsModalOpen(false)}
          onAdded={() => {
            setIsModalOpen(false);
            loadCameras();
          }}
        />
      )}
    </div>
  );
};
"""

# 3. AddCameraModal.tsx
add_cam_modal_ts = """import React, { useState } from 'react';
import { api } from '../../api/client';

interface Props {
  onClose: () => void;
  onAdded: () => void;
}

export const AddCameraModal: React.FC<Props> = ({ onClose, onAdded }) => {
  const [name, setName] = useState('');
  const [type, setType] = useState('RTSP');
  const [url, setUrl] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [devices, setDevices] = useState<{ name: string; url: string }[]>([]);

  const handleScanWebcams = async () => {
    setIsScanning(true);
    const cams = await api.getWebcams();
    setDevices(cams.map((c) => ({ name: c.name, url: c.url })));
    setIsScanning(false);
  };

  const handleScanOnvif = async () => {
    setIsScanning(true);
    const cams = await api.getOnvifCameras();
    setDevices(cams.map((c) => ({ name: c.name, url: c.url })));
    setIsScanning(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !url) return;
    await api.addCamera({ name, type, url });
    onAdded();
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ background: '#121826', border: '1px solid var(--color-cyber-cyan)', borderRadius: 'var(--radius-md)', width: '480px', padding: '24px' }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', margin: '0 0 16px 0', color: '#fff' }}>Cadastrar Nova Câmera</h2>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Nome Identificador</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex: Câmera Portaria Principal"
              style={{ width: '100%', padding: '8px 12px', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: '4px', color: '#fff' }}
              required
            />
          </div>

          <div>
            <label style={{ fontSize: '12px', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Tipo de Conexão</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: '4px', color: '#fff' }}
            >
              <option value="RTSP">Stream RTSP (H.264 / H.265)</option>
              <option value="ONVIF">Câmera IP ONVIF</option>
              <option value="Webcam">Webcam Local / USB</option>
            </select>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>URL do Stream ou Dispositivo</label>
              <div style={{ display: 'flex', gap: '6px' }}>
                {type === 'Webcam' && (
                  <button type="button" onClick={handleScanWebcams} style={{ fontSize: '11px', background: 'rgba(0,240,255,0.1)', color: 'var(--color-cyber-cyan)', border: 'none', padding: '2px 6px', borderRadius: '4px', cursor: 'pointer' }}>
                    {isScanning ? 'Buscando...' : '🔍 Detectar Webcams'}
                  </button>
                )}
                {type === 'ONVIF' && (
                  <button type="button" onClick={handleScanOnvif} style={{ fontSize: '11px', background: 'rgba(0,240,255,0.1)', color: 'var(--color-cyber-cyan)', border: 'none', padding: '2px 6px', borderRadius: '4px', cursor: 'pointer' }}>
                    {isScanning ? 'Escaneando...' : '📡 Scan ONVIF'}
                  </button>
                )}
              </div>
            </div>

            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={type === 'Webcam' ? '0' : 'rtsp://usuario:senha@192.168.1.100:554/live'}
              style={{ width: '100%', padding: '8px 12px', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: '4px', color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '12px' }}
              required
            />

            {devices.length > 0 && (
              <div style={{ marginTop: '8px', background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '4px' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Dispositivos Encontrados:</div>
                {devices.map((d, i) => (
                  <div
                    key={i}
                    onClick={() => { setUrl(d.url); setName(d.name); }}
                    style={{ fontSize: '11px', color: 'var(--color-cyber-cyan)', cursor: 'pointer', padding: '2px 0' }}
                  >
                    • {d.name} ({d.url})
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
            <button type="button" onClick={onClose} style={{ background: 'transparent', border: '1px solid var(--color-border)', color: '#fff', padding: '8px 14px', borderRadius: '4px', cursor: 'pointer' }}>
              Cancelar
            </button>
            <button type="submit" style={{ background: 'var(--color-cyber-cyan)', border: 'none', color: '#000', fontWeight: 700, padding: '8px 16px', borderRadius: '4px', cursor: 'pointer' }}>
              Salvar Câmera
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
"""

# 4. LiveAnalyticsViewer.tsx
live_viewer_ts = """import React, { useState } from 'react';
import { CameraItem } from '../../api/client';

interface Props {
  camera: CameraItem;
}

export const LiveAnalyticsViewer: React.FC<Props> = ({ camera }) => {
  const [selectedModel, setSelectedModel] = useState('cctv_person_custom_v1.pt');
  const [confThreshold, setConfThreshold] = useState(0.45);

  return (
    <div style={{ background: 'rgba(18, 24, 38, 0.7)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--color-success)', boxShadow: '0 0 8px var(--color-success)' }} />
          <strong style={{ fontFamily: 'var(--font-display)', fontSize: '15px' }}>{camera.name}</strong>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-text-muted)' }}>[{camera.resolution} @ {camera.fps}fps]</span>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{ background: '#0a0e17', border: '1px solid var(--color-border)', color: 'var(--color-cyber-cyan)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px' }}
          >
            <option value="cctv_person_custom_v1.pt">Modelo: Pessoa Custom (TRT FP16)</option>
            <option value="yolo11n.pt">Modelo: YOLO11-Nano (COCO)</option>
          </select>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
            <span>Conf: {Math.round(confThreshold * 100)}%</span>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={confThreshold}
              onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
              style={{ width: '80px', accentColor: 'var(--color-cyber-cyan)' }}
            />
          </div>
        </div>
      </div>

      <div style={{ position: 'relative', width: '100%', height: '480px', background: '#000', borderRadius: 'var(--radius-sm)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <img
          src={`http://localhost:8088/api/cameras/${camera.id}/stream`}
          alt="Stream Zero-Delay"
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          onError={(e) => {
            (e.target as HTMLElement).style.display = 'none';
          }}
        />
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
          <div style={{ padding: '8px 16px', background: 'rgba(0,0,0,0.7)', borderRadius: '4px', border: '1px solid rgba(0, 240, 255, 0.3)', color: 'var(--color-cyber-cyan)', fontSize: '13px', fontFamily: 'var(--font-mono)' }}>
            ⚡ OpenCV Zero-Delay Burn-In Ativo | Feed: {camera.url}
          </div>
        </div>
      </div>
    </div>
  );
};
"""

# 5. DatasetsPage.tsx
datasets_page_ts = """import React, { useState } from 'react';
import { api, DatasetMetrics } from '../api/client';
import { DatasetValidationHUD } from '../components/datasets/DatasetValidationHUD';
import { DatasetClassDistribution } from '../components/datasets/DatasetClassDistribution';

export const DatasetsPage: React.FC = () => {
  const [folderPath, setFolderPath] = useState('');
  const [metrics, setMetrics] = useState<DatasetMetrics | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleValidate = async () => {
    if (!folderPath) return;
    setIsValidating(true);
    setErrorMsg(null);
    const res = await api.validateDatasetPath(folderPath);
    if (res.valid && res.metrics) {
      setMetrics(res.metrics);
    } else {
      setMetrics(null);
      setErrorMsg(res.error || 'Diretório inválido ou sem arquivos de imagem/label.');
    }
    setIsValidating(false);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: 0 }}>
          Validação & Ingestão de <span style={{ color: 'var(--color-cyber-cyan)' }}>Datasets</span>
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '13px', margin: '4px 0 0 0' }}>
          Inspeção automatizada de coordenadas normatizadas, imagens corrompidas e balanceamento de classes.
        </p>
      </div>

      <div style={{ background: 'rgba(18, 24, 38, 0.6)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '12px' }}>
          <input
            type="text"
            value={folderPath}
            onChange={(e) => setFolderPath(e.target.value)}
            placeholder="Informe o caminho local do dataset (Ex: C:\datasets\cctv_person_yolo)"
            style={{ flex: 1, padding: '10px 14px', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '13px' }}
          />
          <button
            onClick={handleValidate}
            disabled={isValidating}
            style={{ background: 'var(--color-cyber-cyan)', color: '#000', border: 'none', padding: '10px 20px', borderRadius: 'var(--radius-sm)', fontWeight: 700, cursor: 'pointer' }}
          >
            {isValidating ? 'Validando...' : '🔍 Validar Dataset'}
          </button>
        </div>

        {errorMsg && (
          <div style={{ marginTop: '12px', color: '#ff4444', fontSize: '13px' }}>
            ⚠️ {errorMsg}
          </div>
        )}
      </div>

      {metrics ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <DatasetValidationHUD metrics={metrics} />
          <DatasetClassDistribution classes={metrics.class_distribution} totalLabels={metrics.total_labels} />
        </div>
      ) : (
        <div style={{ padding: '48px 24px', textAlign: 'center', background: 'rgba(18, 24, 38, 0.3)', border: '1px dashed var(--color-border)', borderRadius: 'var(--radius-md)' }}>
          <span style={{ fontSize: '32px' }}>📁</span>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '14px', marginTop: '12px' }}>
            Nenhum dataset selecionado. Informe o caminho da pasta acima para escanear anotações e imagens.
          </p>
        </div>
      )}
    </div>
  );
};
"""

# 6. DatasetValidationHUD.tsx
dataset_hud_ts = """import React from 'react';
import { DatasetMetrics } from '../../api/client';

interface Props {
  metrics: DatasetMetrics;
}

export const DatasetValidationHUD: React.FC<Props> = ({ metrics }) => {
  const cards = [
    { label: 'Total de Imagens', value: metrics.total_images, color: 'var(--color-cyber-cyan)' },
    { label: 'Total de Anotações', value: metrics.total_labels, color: 'var(--color-forge-amber)' },
    { label: 'Imagens Sem Label', value: metrics.missing_labels, color: metrics.missing_labels > 0 ? '#ffaa00' : 'var(--color-success)' },
    { label: 'Labels Órfãos', value: metrics.orphan_labels, color: metrics.orphan_labels > 0 ? '#ff4444' : 'var(--color-success)' },
    { label: 'Imagens Corrompidas', value: metrics.corrupt_images, color: metrics.corrupt_images > 0 ? '#ff4444' : 'var(--color-success)' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
      {cards.map((c, i) => (
        <div key={i} style={{ background: 'rgba(18, 24, 38, 0.6)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '6px' }}>{c.label}</div>
          <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: c.color }}>{c.value}</div>
        </div>
      ))}
    </div>
  );
};
"""

# 7. DatasetClassDistribution.tsx
dataset_dist_ts = """import React from 'react';

interface Props {
  classes: { class_id: string; count: number }[];
  totalLabels: number;
}

export const DatasetClassDistribution: React.FC<Props> = ({ classes, totalLabels }) => {
  return (
    <div style={{ background: 'rgba(18, 24, 38, 0.6)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: '20px' }}>
      <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '15px', margin: '0 0 16px 0', color: '#fff' }}>
        Distribuição Real de Classes
      </h3>

      {classes.length === 0 ? (
        <div style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>Nenhuma anotação de classe encontrada.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {classes.map((cls, idx) => {
            const pct = totalLabels > 0 ? Math.round((cls.count / totalLabels) * 100) : 0;
            return (
              <div key={idx}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                  <span>Classe ID #{cls.class_id}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-cyber-cyan)' }}>{cls.count} instâncias ({pct}%)</span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: 'var(--color-cyber-cyan)', borderRadius: '4px' }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
"""

# 8. ModelComparisonPage.tsx
model_comp_ts = """import React, { useState, useEffect } from 'react';
import { api, ModelBenchmarkItem } from '../api/client';

export const ModelComparisonPage: React.FC = () => {
  const [models, setModels] = useState<ModelBenchmarkItem[]>([]);
  const [familyFilter, setFamilyFilter] = useState('ALL');
  const [liveResult, setLiveResult] = useState<any>(null);
  const [isRunningBench, setIsRunningBench] = useState(false);

  useEffect(() => {
    api.getBenchmarks().then(setModels);
  }, []);

  const filtered = familyFilter === 'ALL' ? models : models.filter((m) => m.family.includes(familyFilter) || (familyFilter === 'Custom' && m.isCustom));

  const handleRunLive = async (name: string) => {
    setIsRunningBench(true);
    const res = await api.runLiveBenchmark(name);
    setLiveResult(res);
    setIsRunningBench(false);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: 0 }}>
            Comparador de Modelos & <span style={{ color: 'var(--color-cyber-cyan)' }}>Benchmarks</span>
          </h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '13px', margin: '4px 0 0 0' }}>
            Validação de métricas contra famílias oficiais YOLO (v8, v10, 11 e 26) na NVIDIA RTX 5090.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {['ALL', 'Custom', 'YOLO26', 'YOLO11', 'YOLOv10', 'YOLOv8'].map((fam) => (
            <button
              key={fam}
              onClick={() => setFamilyFilter(fam)}
              style={{
                background: familyFilter === fam ? 'var(--color-cyber-cyan)' : 'rgba(255,255,255,0.05)',
                color: familyFilter === fam ? '#000' : 'var(--color-text)',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {fam}
            </button>
          ))}
        </div>
      </div>

      <div style={{ background: 'rgba(18, 24, 38, 0.6)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }}>
              <th style={{ padding: '12px 16px' }}>Modelo</th>
              <th style={{ padding: '12px 16px' }}>Família</th>
              <th style={{ padding: '12px 16px' }}>Parâmetros</th>
              <th style={{ padding: '12px 16px' }}>FLOPs</th>
              <th style={{ padding: '12px 16px' }}>mAP @ 50</th>
              <th style={{ padding: '12px 16px' }}>mAP @ 50-95</th>
              <th style={{ padding: '12px 16px' }}>RTX 5090 FPS</th>
              <th style={{ padding: '12px 16px' }}>Ação</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((m, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: m.isCustom ? 'rgba(0, 240, 255, 0.04)' : 'transparent' }}>
                <td style={{ padding: '12px 16px', fontWeight: 600, color: m.isCustom ? 'var(--color-cyber-cyan)' : '#fff' }}>{m.name}</td>
                <td style={{ padding: '12px 16px', color: 'var(--color-forge-amber)' }}>{m.family}</td>
                <td style={{ padding: '12px 16px' }}>{m.params}</td>
                <td style={{ padding: '12px 16px' }}>{m.flops}</td>
                <td style={{ padding: '12px 16px', color: 'var(--color-success)' }}>{m.mAP50}%</td>
                <td style={{ padding: '12px 16px', color: 'var(--color-cyber-cyan)', fontWeight: 700 }}>{m.mAP50_95}%</td>
                <td style={{ padding: '12px 16px', color: '#38bdf8' }}>{m.fps} FPS</td>
                <td style={{ padding: '12px 16px' }}>
                  <button
                    onClick={() => handleRunLive(m.name)}
                    disabled={isRunningBench}
                    style={{ background: 'rgba(0,240,255,0.1)', color: 'var(--color-cyber-cyan)', border: '1px solid var(--color-cyber-cyan)', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
                  >
                    Benchmark
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {liveResult && (
        <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(0, 240, 255, 0.05)', border: '1px solid var(--color-cyber-cyan)', borderRadius: 'var(--radius-md)' }}>
          <h4 style={{ margin: '0 0 8px 0', color: 'var(--color-cyber-cyan)' }}>Resultado Live Benchmark: {liveResult.model}</h4>
          <div style={{ display: 'flex', gap: '24px', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
            <div>Dispositivo: <strong>{liveResult.device}</strong></div>
            <div>Latência Média: <strong style={{ color: 'var(--color-cyber-cyan)' }}>{liveResult.latency_mean_ms} ms</strong></div>
            <div>Throughput: <strong style={{ color: 'var(--color-forge-amber)' }}>{liveResult.fps_throughput} FPS</strong></div>
          </div>
        </div>
      )}
    </div>
  );
};
"""

# 9. ModelExportPage.tsx
model_export_ts = """import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export const ModelExportPage: React.FC = () => {
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [exportFormat, setExportFormat] = useState('engine');
  const [precision, setPrecision] = useState('fp16');
  const [isCompiling, setIsCompiling] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [resultFile, setResultFile] = useState<string | null>(null);

  useEffect(() => {
    api.getExportableModels().then((data) => {
      setModels(data);
      if (data.length > 0) setSelectedModel(data[0]);
    });
  }, []);

  const handleStartExport = async () => {
    if (!selectedModel) return;
    setIsCompiling(true);
    setLogs(['Iniciando pipeline de compilação...']);
    setResultFile(null);
    const res = await api.startExport({ model_name: selectedModel, format: exportFormat, precision, imgsz: 640 });
    if (res) {
      setLogs(res.logs);
      setResultFile(res.result_file);
    }
    setIsCompiling(false);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', margin: 0 }}>
          Exportador & Compilador <span style={{ color: 'var(--color-cyber-cyan)' }}>TensorRT</span>
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '13px', margin: '4px 0 0 0' }}>
          Otimização e serialização de modelos PyTorch (.pt) para engines de ultra performance (.engine).
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '400px 1fr', gap: '20px' }}>
        <div style={{ background: 'rgba(18, 24, 38, 0.6)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: '20px' }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '15px', margin: '0 0 16px 0', color: '#fff' }}>Configurações de Exportação</h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Pesos de Origem (.pt)</label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: '4px', color: '#fff' }}
              >
                {models.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Formato Alvo</label>
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: '4px', color: '#fff' }}
              >
                <option value="engine">TensorRT (.engine - Recomendado RTX 5090)</option>
                <option value="onnx">ONNX (.onnx)</option>
                <option value="openvino">OpenVINO (.xml / .bin)</option>
                <option value="ncnn">NCNN (Edge & Mobile)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Precisão Numérica</label>
              <select
                value={precision}
                onChange={(e) => setPrecision(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: '4px', color: '#fff' }}
              >
                <option value="fp16">FP16 (Half Precision - 3x Velocidade)</option>
                <option value="int8">INT8 (Quantização Calibrada)</option>
                <option value="fp32">FP32 (Full Precision)</option>
              </select>
            </div>

            <button
              onClick={handleStartExport}
              disabled={isCompiling || !selectedModel}
              style={{
                marginTop: '12px',
                background: 'var(--color-cyber-cyan)',
                color: '#000',
                border: 'none',
                padding: '12px',
                borderRadius: '4px',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {isCompiling ? '⚡ Compilando Engine...' : '🚀 Iniciar Compilação TensorRT'}
            </button>
          </div>
        </div>

        <div style={{ background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: '16px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>LOGS DE EXECUÇÃO</span>
            {resultFile && (
              <span style={{ fontSize: '11px', color: 'var(--color-success)', background: 'rgba(0,255,136,0.1)', padding: '2px 8px', borderRadius: '4px' }}>
                ✓ Gerado: {resultFile}
              </span>
            )}
          </div>

          <div style={{ flex: 1, minHeight: '300px', background: '#05070a', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '4px', padding: '12px', fontFamily: 'var(--font-mono)', fontSize: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {logs.length === 0 ? (
              <span style={{ color: 'var(--color-text-muted)' }}>Aguardando início do job de compilação...</span>
            ) : (
              logs.map((log, i) => (
                <div key={i} style={{ color: log.includes('SUCCESS') ? 'var(--color-success)' : log.includes('WARN') ? 'var(--color-forge-amber)' : 'var(--color-text)' }}>
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
"""

def main():
    (SRC_DIR / "api").mkdir(parents=True, exist_ok=True)
    (SRC_DIR / "api" / "client.ts").write_text(api_client_ts.strip() + "\n", encoding="utf-8")
    (SRC_DIR / "pages" / "CamerasPage.tsx").write_text(cameras_page_ts.strip() + "\n", encoding="utf-8")
    (SRC_DIR / "components" / "cameras" / "AddCameraModal.tsx").write_text(add_cam_modal_ts.strip() + "\n", encoding="utf-8")
    (SRC_DIR / "components" / "cameras" / "LiveAnalyticsViewer.tsx").write_text(live_viewer_ts.strip() + "\n", encoding="utf-8")
    (SRC_DIR / "pages" / "DatasetsPage.tsx").write_text(datasets_page_ts.strip() + "\n", encoding="utf-8")
    (SRC_DIR / "components" / "datasets" / "DatasetValidationHUD.tsx").write_text(dataset_hud_ts.strip() + "\n", encoding="utf-8")
    (SRC_DIR / "components" / "datasets" / "DatasetClassDistribution.tsx").write_text(dataset_dist_ts.strip() + "\n", encoding="utf-8")
    (SRC_DIR / "pages" / "ModelComparisonPage.tsx").write_text(model_comp_ts.strip() + "\n", encoding="utf-8")
    (SRC_DIR / "pages" / "ModelExportPage.tsx").write_text(model_export_ts.strip() + "\n", encoding="utf-8")
    print("Frontend de HydraForge atualizado com sucesso sem mocks!")

if __name__ == "__main__":
    main()

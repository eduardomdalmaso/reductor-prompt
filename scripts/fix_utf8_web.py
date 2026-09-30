#!/usr/bin/env python3
"""
Script de correção de codificação UTF-8 pura para o HydraForge Web.
"""
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

WEB_DIR = Path(r"C:\Users\hades\Documents\HydraForge\web")

FILES = {}

# 1. index.html
FILES[WEB_DIR / "index.html"] = """<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>⚡ HydraForge — AI Training Studio & Live Analytics</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

# 2. theme.css
FILES[WEB_DIR / "src" / "styles" / "theme.css"] = """@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --font-display: 'Space Grotesk', -apple-system, sans-serif;
  --font-body: 'Outfit', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  --color-cyber-cyan: #00f0ff;
  --color-forge-amber: #ff9900;
  --color-obsidian: #0a0e17;

  --color-surface: #121826;
  --color-surface-hover: #1b2336;
  --color-border: rgba(0, 240, 255, 0.15);
  --color-border-glow: rgba(0, 240, 255, 0.4);
  --color-text: #f8fafc;
  --color-text-muted: #94a3b8;
  --color-success: #10b981;
  --color-danger: #ef4444;

  --glass-bg: rgba(18, 24, 38, 0.75);
  --glass-blur: blur(12px);
  --glow-cyan: 0 0 20px rgba(0, 240, 255, 0.25);
  --glow-amber: 0 0 20px rgba(255, 153, 0, 0.25);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-body);
  background-color: var(--color-obsidian);
  color: var(--color-text);
  min-height: 100vh;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
"""

# 3. App.tsx
FILES[WEB_DIR / "src" / "App.tsx"] = """import React, { useState } from 'react';
import './styles/theme.css';
import { DatasetsPage } from './pages/DatasetsPage';
import { CamerasPage } from './pages/CamerasPage';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'datasets' | 'cameras'>('cameras');

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-obsidian)', color: 'var(--color-text)' }}>
      <nav style={{ background: 'rgba(18, 24, 38, 0.85)', backdropFilter: 'blur(12px)', borderBottom: '1px solid var(--color-border)', padding: '0 24px', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '24px' }}>⚡</span>
            <span style={{ fontFamily: 'var(--font-display)', fontSize: '20px', fontWeight: 700, letterSpacing: '-0.5px' }}>
              HYDRA<span style={{ color: 'var(--color-cyber-cyan)' }}>FORGE</span>
            </span>
          </div>

          <div style={{ display: 'flex', gap: '8px', marginLeft: '24px' }}>
            <button
              onClick={() => setActiveTab('cameras')}
              style={{
                background: activeTab === 'cameras' ? 'rgba(0, 240, 255, 0.15)' : 'transparent',
                color: activeTab === 'cameras' ? 'var(--color-cyber-cyan)' : 'var(--color-text-muted)',
                border: `1px solid ${activeTab === 'cameras' ? 'var(--color-cyber-cyan)' : 'transparent'}`,
                padding: '8px 16px',
                borderRadius: 'var(--radius-sm)',
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              📹 Câmeras & Analíticos
            </button>

            <button
              onClick={() => setActiveTab('datasets')}
              style={{
                background: activeTab === 'datasets' ? 'rgba(0, 240, 255, 0.15)' : 'transparent',
                color: activeTab === 'datasets' ? 'var(--color-cyber-cyan)' : 'var(--color-text-muted)',
                border: `1px solid ${activeTab === 'datasets' ? 'var(--color-cyber-cyan)' : 'transparent'}`,
                padding: '8px 16px',
                borderRadius: 'var(--radius-sm)',
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              📦 Datasets & Ingestão
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-success)', boxShadow: '0 0 8px var(--color-success)' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-text-muted)' }}>
            GPU Engine: <strong style={{ color: 'var(--color-forge-amber)' }}>RTX 5090</strong>
          </span>
        </div>
      </nav>

      <main>
        {activeTab === 'cameras' && <CamerasPage />}
        {activeTab === 'datasets' && <DatasetsPage />}
      </main>
    </div>
  );
};
export default App;
"""

# 4. DatasetsPage.tsx
FILES[WEB_DIR / "src" / "pages" / "DatasetsPage.tsx"] = """import React, { useState } from 'react';
import { DatasetUploader } from '../components/datasets/DatasetUploader';
import { DatasetValidationHUD } from '../components/datasets/DatasetValidationHUD';
import { DatasetClassDistribution } from '../components/datasets/DatasetClassDistribution';

export const DatasetsPage: React.FC = () => {
  const [activeDataset, setActiveDataset] = useState<any>({
    name: 'cctv_industrial_safety_v1',
    totalImages: 1240,
    totalLabels: 1180,
    backgroundImages: 60,
    classes: ['person', 'helmet', 'vest'],
    healthScore: 94,
  });

  const handleSendToTraining = () => {
    alert(`🚀 Dataset "${activeDataset?.name}" validado e carregado no Cockpit de Treino!`);
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 20px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', borderBottom: '1px solid var(--color-border)', paddingBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '28px' }}>⚡</span>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '26px', fontWeight: 700, color: 'var(--color-text)' }}>
              HYDRA<span style={{ color: 'var(--color-cyber-cyan)' }}>FORGE</span> <span style={{ color: 'var(--color-forge-amber)', fontSize: '16px', fontWeight: 500 }}>DATASETS</span>
            </h1>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Ingestão inteligente, auditoria com "Regra do Espelho" e auto-preparação de datasets para YOLOv8/11/26.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '8px 16px', textAlign: 'center' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-text-muted)' }}>DATASETS PRONTOS</span>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px', fontWeight: 700, color: 'var(--color-cyber-cyan)' }}>4 Ativos</div>
          </div>
          <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '8px 16px', textAlign: 'center' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-text-muted)' }}>GPU STATUS</span>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px', fontWeight: 700, color: 'var(--color-forge-amber)' }}>RTX 5090 (32GB)</div>
          </div>
        </div>
      </header>

      <DatasetUploader onDatasetReady={setActiveDataset} />
      <DatasetValidationHUD dataset={activeDataset} onSendToTraining={handleSendToTraining} />
      <DatasetClassDistribution classes={activeDataset?.classes || []} />
    </div>
  );
};
"""

# 5. DatasetUploader.tsx
FILES[WEB_DIR / "src" / "components" / "datasets" / "DatasetUploader.tsx"] = """import React, { useState } from 'react';

interface DatasetUploaderProps {
  onDatasetReady: (datasetInfo: any) => void;
}

export const DatasetUploader: React.FC<DatasetUploaderProps> = ({ onDatasetReady }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [datasetName, setDatasetName] = useState('');
  const [autoSplit, setAutoSplit] = useState(true);
  const [autoDeduplicate, setAutoDeduplicate] = useState(true);
  const [autoLabelZeroShot, setAutoLabelZeroShot] = useState(false);
  const [targetClasses, setTargetClasses] = useState('person, helmet, vest');

  const acceptedFormats = [
    { ext: '.ZIP / .TAR', label: 'Pacotes YOLO / COCO' },
    { ext: '.JPG / .PNG / .WEBP', label: 'Imagens Brutas' },
    { ext: '.MP4 / .AVI / .MOV', label: 'Vídeos com Auto-Frame' },
    { ext: 'data.yaml', label: 'Manifest Canônico' },
  ];

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    onDatasetReady({
      name: datasetName || 'dataset-industrial-cctv',
      totalImages: 1240,
      totalLabels: 1180,
      backgroundImages: 60,
      classes: targetClasses.split(',').map((c) => c.trim()),
      healthScore: 94,
      autoSplit,
      autoDeduplicate,
      autoLabelZeroShot,
    });
  };

  return (
    <div style={{ background: 'var(--glass-bg)', backdropFilter: 'var(--glass-blur)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', padding: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', color: 'var(--color-cyber-cyan)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📦</span> Upload & Ingestão de Datasets
          </h2>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '13px', marginTop: '4px' }}>
            Arraste pastas com imagens, vídeos ou arquivos compactados para validação automática.
          </p>
        </div>
        <input
          type="text"
          placeholder="Nome do Dataset..."
          value={datasetName}
          onChange={(e) => setDatasetName(e.target.value)}
          style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '8px 14px', color: 'var(--color-text)', fontFamily: 'var(--font-body)', fontSize: '13px', outline: 'none', width: '220px' }}
        />
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        style={{
          border: `2px dashed ${isDragging ? 'var(--color-cyber-cyan)' : 'rgba(0, 240, 255, 0.3)'}`,
          borderRadius: 'var(--radius-md)',
          padding: '36px 20px',
          textAlign: 'center',
          background: isDragging ? 'rgba(0, 240, 255, 0.05)' : 'rgba(18, 24, 38, 0.4)',
          transition: 'all 0.2s ease',
          cursor: 'pointer',
        }}
      >
        <div style={{ fontSize: '40px', marginBottom: '12px' }}>📂</div>
        <p style={{ fontFamily: 'var(--font-display)', fontSize: '16px', fontWeight: 600 }}>
          Arraste arquivos aqui ou <span style={{ color: 'var(--color-cyber-cyan)', textDecoration: 'underline' }}>clique para navegar</span>
        </p>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginTop: '6px' }}>
          Suporte nativo à "Regra do Espelho" (Images ↔ Labels) e conversão automática de COCO/VOC.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '16px' }}>
          {acceptedFormats.map((f, i) => (
            <span key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', background: 'rgba(0, 240, 255, 0.1)', color: 'var(--color-cyber-cyan)', border: '1px solid rgba(0, 240, 255, 0.2)', padding: '4px 10px', borderRadius: '4px' }}>
              {f.ext} <span style={{ color: 'var(--color-text-muted)' }}>({f.label})</span>
            </span>
          ))}
        </div>
      </div>

      <div style={{ marginTop: '20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', background: 'rgba(10, 14, 23, 0.6)', padding: '16px', borderRadius: 'var(--radius-md)' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
          <input type="checkbox" checked={autoSplit} onChange={(e) => setAutoSplit(e.target.checked)} style={{ accentColor: 'var(--color-cyber-cyan)' }} />
          <span>✂️ <strong>Auto-Split Seguro</strong> (80/10/10 sem leak)</span>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
          <input type="checkbox" checked={autoDeduplicate} onChange={(e) => setAutoDeduplicate(e.target.checked)} style={{ accentColor: 'var(--color-cyber-cyan)' }} />
          <span>🧹 <strong>Deduplicador pHash</strong> (Filtro estático)</span>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
          <input type="checkbox" checked={autoLabelZeroShot} onChange={(e) => setAutoLabelZeroShot(e.target.checked)} style={{ accentColor: 'var(--color-forge-amber)' }} />
          <span>🤖 <strong>Auto-Anotação SAM 2</strong> (Zero-Shot)</span>
        </label>
      </div>
    </div>
  );
};
"""

# 6. DatasetValidationHUD.tsx
FILES[WEB_DIR / "src" / "components" / "datasets" / "DatasetValidationHUD.tsx"] = """import React from 'react';

interface DatasetValidationHUDProps {
  dataset: any;
  onSendToTraining: () => void;
}

export const DatasetValidationHUD: React.FC<DatasetValidationHUDProps> = ({ dataset, onSendToTraining }) => {
  if (!dataset) return null;

  const checks = [
    { name: 'Regra do Espelho (Images ↔ Labels)', status: 'PASS', detail: `${dataset.totalLabels} rótulos pareados com ${dataset.totalImages} imagens` },
    { name: 'Background Images (Imagens de Fundo)', status: 'PASS', detail: `${dataset.backgroundImages} imagens (4.8% do total — ideal para reduzir falso positivo)` },
    { name: 'Integridade de Arquivos (Corrupção)', status: 'PASS', detail: '0 imagens corrompidas ou truncadas detectadas' },
    { name: 'Prevenção de Data Leakage (Vídeo Splits)', status: 'PASS', detail: 'Sequências de mesma câmera isoladas no mesmo split' },
    { name: 'Resolução Recomendada de Treino', status: 'INFO', detail: 'imgsz=640 (78% das caixas são Medium/Large)' },
  ];

  return (
    <div style={{ background: 'var(--glass-bg)', backdropFilter: 'var(--glass-blur)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-forge-amber)', textTransform: 'uppercase', letterSpacing: '1px' }}>Auditoria em Tempo Real</span>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '22px', color: 'var(--color-text)', marginTop: '2px' }}>
            {dataset.name} <span style={{ fontSize: '13px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>({dataset.totalImages} frames)</span>
          </h3>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-text-muted)' }}>HEALTH SCORE</span>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '24px', fontWeight: 700, color: 'var(--color-cyber-cyan)' }}>
              {dataset.healthScore}%
            </div>
          </div>

          <button
            onClick={onSendToTraining}
            style={{
              background: 'linear-gradient(135deg, var(--color-cyber-cyan), #00a8b3)',
              color: 'var(--color-obsidian)',
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: '14px',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 24px',
              cursor: 'pointer',
              boxShadow: 'var(--glow-cyan)',
              transition: 'transform 0.15s ease',
            }}
          >
            ⚡ Iniciar Treino com este Dataset
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
        {checks.map((c, i) => (
          <div
            key={i}
            style={{
              background: 'rgba(18, 24, 38, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              borderRadius: 'var(--radius-sm)',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text)' }}>{c.name}</span>
              <span
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: c.status === 'PASS' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(0, 240, 255, 0.15)',
                  color: c.status === 'PASS' ? 'var(--color-success)' : 'var(--color-cyber-cyan)',
                }}
              >
                {c.status}
              </span>
            </div>
            <p style={{ color: 'var(--color-text-muted)', fontSize: '12px', fontFamily: 'var(--font-body)' }}>{c.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
"""

# 7. DatasetClassDistribution.tsx
FILES[WEB_DIR / "src" / "components" / "datasets" / "DatasetClassDistribution.tsx"] = """import React from 'react';

interface DatasetClassDistributionProps {
  classes: string[];
}

export const DatasetClassDistribution: React.FC<DatasetClassDistributionProps> = ({ classes }) => {
  const mockClassData = [
    { name: 'person', count: 850, pct: 45, color: 'var(--color-cyber-cyan)' },
    { name: 'helmet', count: 620, pct: 33, color: 'var(--color-forge-amber)' },
    { name: 'vest', count: 410, pct: 22, color: '#38bdf8' },
  ];

  const generatedYaml = `path: /datasets/cctv_safety
train: images/train
val: images/val
test: images/test
names:
  0: person
  1: helmet
  2: vest`;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
      <div style={{ background: 'var(--glass-bg)', backdropFilter: 'var(--glass-blur)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', padding: '24px' }}>
        <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '16px', color: 'var(--color-text)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>📊</span> Distribuição de Classes & Balanceamento
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {mockClassData.map((cls, idx) => (
            <div key={idx}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', color: cls.color, fontWeight: 600 }}>
                  [{idx}] {cls.name}
                </span>
                <span style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                  {cls.count} instâncias ({cls.pct}%)
                </span>
              </div>
              <div style={{ height: '8px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${cls.pct}%`, background: cls.color, borderRadius: '4px' }} />
              </div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(0, 240, 255, 0.04)', border: '1px solid rgba(0, 240, 255, 0.15)', borderRadius: 'var(--radius-sm)', fontSize: '12px', color: 'var(--color-text-muted)' }}>
          💡 <strong>Diagnóstico de Treino:</strong> Classes bem balanceadas. Nenhuma classe rara (&lt;5%) detectada.
        </div>
      </div>

      <div style={{ background: 'var(--glass-bg)', backdropFilter: 'var(--glass-blur)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '16px', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📄</span> Manifest Canônico <code>data.yaml</code>
          </h4>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-success)', background: 'rgba(16, 185, 129, 0.1)', padding: '2px 8px', borderRadius: '4px' }}>
            Gerado Auto
          </span>
        </div>

        <pre style={{ background: '#070a0f', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-sm)', padding: '14px', fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#38bdf8', overflowX: 'auto', lineHeight: '1.6' }}>
          {generatedYaml}
        </pre>
      </div>
    </div>
  );
};
"""

# 8. CamerasPage.tsx
FILES[WEB_DIR / "src" / "pages" / "CamerasPage.tsx"] = """import React, { useState } from 'react';
import { AddCameraModal, CameraConfig } from '../components/cameras/AddCameraModal';
import { LiveAnalyticsViewer } from '../components/cameras/LiveAnalyticsViewer';

export const CamerasPage: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeCamera, setActiveCamera] = useState<CameraConfig | null>(null);

  const [cameras, setCameras] = useState<CameraConfig[]>([
    {
      id: 'cam_01',
      name: 'Portaria Principal (RTSP)',
      sourceType: 'rtsp',
      sourceUrl: 'rtsp://admin:pass@192.168.1.50:554/stream1',
      model: 'yolo11m_best.pt',
      confidence: 0.45,
    },
    {
      id: 'cam_02',
      name: 'Webcam Local (Bancada)',
      sourceType: 'webcam',
      sourceUrl: 'webcam:0',
      model: 'cctv_safety_v1.engine',
      confidence: 0.5,
    },
  ]);

  const handleAddCamera = (newCam: CameraConfig) => {
    setCameras([...cameras, newCam]);
    setActiveCamera(newCam);
  };

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '32px 20px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', borderBottom: '1px solid var(--color-border)', paddingBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '28px' }}>📹</span>
            <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '26px', fontWeight: 700, color: 'var(--color-text)' }}>
              HYDRA<span style={{ color: 'var(--color-cyber-cyan)' }}>FORGE</span> <span style={{ color: 'var(--color-forge-amber)', fontSize: '16px', fontWeight: 500 }}>ANALYTICS & CÂMERAS</span>
            </h1>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '14px', marginTop: '4px' }}>
            Cadastro de fontes RTSP, ONVIF e Webcams locais com inferência YOLO e visualização OpenCV Zero-Delay.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          style={{
            background: 'var(--color-cyber-cyan)',
            color: 'var(--color-obsidian)',
            fontFamily: 'var(--font-display)',
            fontWeight: 700,
            fontSize: '14px',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            padding: '12px 20px',
            cursor: 'pointer',
            boxShadow: 'var(--glow-cyan)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span>➕</span> Nova Câmera
        </button>
      </header>

      {activeCamera && (
        <LiveAnalyticsViewer camera={activeCamera} onClose={() => setActiveCamera(null)} />
      )}

      <div>
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--color-text)', marginBottom: '16px' }}>
          Fontes de Vídeo Conectadas ({cameras.length})
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
          {cameras.map((cam) => (
            <div
              key={cam.id}
              onClick={() => setActiveCamera(cam)}
              style={{
                background: activeCamera?.id === cam.id ? 'rgba(0, 240, 255, 0.08)' : 'var(--glass-bg)',
                backdropFilter: 'var(--glass-blur)',
                border: `1px solid ${activeCamera?.id === cam.id ? 'var(--color-cyber-cyan)' : 'var(--color-border)'}`,
                borderRadius: 'var(--radius-md)',
                padding: '20px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '16px', color: 'var(--color-text)' }}>{cam.name}</h4>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--color-success)', background: 'rgba(16, 185, 129, 0.15)', padding: '2px 8px', borderRadius: '4px' }}>
                  ONLINE
                </span>
              </div>

              <p style={{ color: 'var(--color-text-muted)', fontSize: '12px', fontFamily: 'var(--font-mono)', marginBottom: '14px', wordBreak: 'break-all' }}>
                {cam.sourceUrl}
              </p>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '10px' }}>
                <span style={{ color: 'var(--color-forge-amber)', fontFamily: 'var(--font-mono)' }}>{cam.model}</span>
                <span style={{ color: 'var(--color-cyber-cyan)', fontWeight: 600 }}>Visualizar Feed ➔</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <AddCameraModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSave={handleAddCamera} />
    </div>
  );
};
"""

# 9. AddCameraModal.tsx
FILES[WEB_DIR / "src" / "components" / "cameras" / "AddCameraModal.tsx"] = """import React, { useState } from 'react';

export interface CameraConfig {
  id: string;
  name: string;
  sourceType: 'rtsp' | 'onvif' | 'webcam';
  sourceUrl: string;
  model: string;
  confidence: number;
}

interface AddCameraModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (camera: CameraConfig) => void;
}

export const AddCameraModal: React.FC<AddCameraModalProps> = ({ isOpen, onClose, onSave }) => {
  const [sourceType, setSourceType] = useState<'rtsp' | 'onvif' | 'webcam'>('rtsp');
  const [name, setName] = useState('Câmera Entrada');
  const [rtspUrl, setRtspUrl] = useState('rtsp://admin:pass@192.168.1.100:554/stream1');
  const [webcamIndex, setWebcamIndex] = useState('0');
  const [onvifIp, setOnvifIp] = useState('192.168.1.50');
  const [onvifUser, setOnvifUser] = useState('admin');
  const [onvifPass, setOnvifPass] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [discoveredDevices, setDiscoveredDevices] = useState<string[]>([]);
  const [model, setModel] = useState('yolo11m_best.pt');
  const [confidence, setConfidence] = useState(0.45);

  if (!isOpen) return null;

  const handleScanOnvif = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
      setDiscoveredDevices(['192.168.1.50:80 (Hikvision IPC)', '192.168.1.64:80 (Intelbras VIP)', '192.168.1.105:8080 (Dahua IPC)']);
    }, 1200);
  };

  const handleSave = () => {
    let finalUrl = rtspUrl;
    if (sourceType === 'webcam') finalUrl = `webcam:${webcamIndex}`;
    if (sourceType === 'onvif') finalUrl = `onvif://${onvifUser}:${onvifPass}@${onvifIp}:554/live`;

    onSave({
      id: `cam_${Date.now()}`,
      name,
      sourceType,
      sourceUrl: finalUrl,
      model,
      confidence,
    });
    onClose();
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(10, 14, 23, 0.85)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' }}>
      <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '540px', padding: '28px', boxShadow: '0 20px 50px rgba(0,0,0,0.6)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📹</span> Cadastrar Fonte de Vídeo
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', fontSize: '20px', cursor: 'pointer' }}>✕</button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '20px', background: 'rgba(0,0,0,0.3)', padding: '4px', borderRadius: 'var(--radius-sm)' }}>
          {(['rtsp', 'onvif', 'webcam'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setSourceType(type)}
              style={{
                background: sourceType === type ? 'var(--color-cyber-cyan)' : 'transparent',
                color: sourceType === type ? 'var(--color-obsidian)' : 'var(--color-text-muted)',
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: '12px',
                padding: '8px',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                textTransform: 'uppercase',
                transition: 'all 0.15s ease',
              }}
            >
              {type === 'rtsp' ? '🔗 URL RTSP' : type === 'onvif' ? '🔍 ONVIF Rede' : '💻 Webcam Local'}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Nome da Câmera / Ponto</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} style={{ width: '100%', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--color-text)', outline: 'none' }} />
          </div>

          {sourceType === 'rtsp' && (
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>URL do Stream RTSP</label>
              <input type="text" value={rtspUrl} onChange={(e) => setRtspUrl(e.target.value)} placeholder="rtsp://usuario:senha@ip:554/stream" style={{ width: '100%', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: '#38bdf8', fontFamily: 'var(--font-mono)', fontSize: '12px' }} />
            </div>
          )}

          {sourceType === 'onvif' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input type="text" value={onvifIp} onChange={(e) => setOnvifIp(e.target.value)} placeholder="IP ou Sub-rede" style={{ flex: 1, background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--color-text)' }} />
                <button onClick={handleScanOnvif} disabled={isScanning} style={{ background: 'rgba(0, 240, 255, 0.15)', border: '1px solid var(--color-cyber-cyan)', color: 'var(--color-cyber-cyan)', padding: '8px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontFamily: 'var(--font-display)', fontSize: '12px', fontWeight: 600 }}>
                  {isScanning ? 'Varrendo...' : '🔍 Scan ONVIF'}
                </button>
              </div>
              {discoveredDevices.length > 0 && (
                <div style={{ background: '#070a0f', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 'var(--radius-sm)', padding: '8px', fontSize: '12px' }}>
                  <span style={{ color: 'var(--color-forge-amber)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>Câmeras Encontradas:</span>
                  {discoveredDevices.map((dev, i) => (
                    <div key={i} onClick={() => setOnvifIp(dev.split(' ')[0])} style={{ padding: '4px 6px', cursor: 'pointer', color: '#94a3b8' }}>• {dev}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {sourceType === 'webcam' && (
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Dispositivo de Vídeo (Device Index)</label>
              <select value={webcamIndex} onChange={(e) => setWebcamIndex(e.target.value)} style={{ width: '100%', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--color-text)' }}>
                <option value="0">Dispositivo 0 (Webcam Integrada / USB Principal)</option>
                <option value="1">Dispositivo 1 (Webcam Secundária / Placa de Captura)</option>
                <option value="2">Dispositivo 2 (OBS Virtual Camera)</option>
              </select>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Modelo de Analítico</label>
              <select value={model} onChange={(e) => setModel(e.target.value)} style={{ width: '100%', background: '#0a0e17', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', padding: '8px', color: 'var(--color-cyber-cyan)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                <option value="yolo11m_best.pt">yolo11m_best.pt (Geral)</option>
                <option value="cctv_safety_v1.engine">cctv_safety_v1.engine (TensorRT)</option>
                <option value="ppe_detection.pt">ppe_detection.pt (EPIs)</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>Confiança ({Math.round(confidence * 100)}%)</label>
              <input type="range" min="0.1" max="0.9" step="0.05" value={confidence} onChange={(e) => setConfidence(parseFloat(e.target.value))} style={{ width: '100%', accentColor: 'var(--color-cyber-cyan)', marginTop: '8px' }} />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
          <button onClick={onClose} style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--color-text-muted)', padding: '10px 18px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>Cancelar</button>
          <button onClick={handleSave} style={{ background: 'var(--color-cyber-cyan)', color: 'var(--color-obsidian)', border: 'none', padding: '10px 22px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-display)', fontWeight: 700, cursor: 'pointer' }}>Salvar & Conectar</button>
        </div>
      </div>
    </div>
  );
};
"""

# 10. LiveAnalyticsViewer.tsx
FILES[WEB_DIR / "src" / "components" / "cameras" / "LiveAnalyticsViewer.tsx"] = """import React, { useState } from 'react';
import { CameraConfig } from './AddCameraModal';

interface LiveAnalyticsViewerProps {
  camera: CameraConfig;
  onClose: () => void;
}

export const LiveAnalyticsViewer: React.FC<LiveAnalyticsViewerProps> = ({ camera, onClose }) => {
  const [isPlaying, setIsPlaying] = useState(true);
  const [confidence, setConfidence] = useState(camera.confidence);

  return (
    <div style={{ background: 'var(--glass-bg)', backdropFilter: 'var(--glass-blur)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: isPlaying ? 'var(--color-success)' : 'var(--color-danger)', boxShadow: isPlaying ? '0 0 8px var(--color-success)' : 'none' }} />
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--color-text)' }}>{camera.name}</h3>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-cyber-cyan)', background: 'rgba(0, 240, 255, 0.1)', padding: '2px 8px', borderRadius: '4px' }}>
              {camera.sourceType.toUpperCase()}
            </span>
          </div>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '12px', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
            {camera.sourceUrl}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ background: 'rgba(10, 14, 23, 0.6)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', gap: '16px', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
            <span>⚡ FPS: <strong style={{ color: 'var(--color-cyber-cyan)' }}>29.8</strong></span>
            <span>⏱️ Latência: <strong style={{ color: 'var(--color-success)' }}>7.2ms</strong></span>
            <span>🎯 Objetos: <strong style={{ color: 'var(--color-forge-amber)' }}>4</strong></span>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--color-text-muted)', padding: '6px 12px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>✕ Fechar</button>
        </div>
      </div>

      <div style={{ position: 'relative', width: '100%', height: '480px', background: '#05070a', borderRadius: 'var(--radius-md)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
        {isPlaying ? (
          <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'radial-gradient(circle, rgba(18,24,38,0.8) 0%, rgba(5,7,10,1) 100%)' }}>
            <div style={{ position: 'relative', width: '85%', height: '80%', border: '1px dashed rgba(0, 240, 255, 0.4)', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ position: 'absolute', top: '10px', left: '10px', background: 'rgba(0, 240, 255, 0.85)', color: '#000', fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, padding: '2px 6px', borderRadius: '2px' }}>
                person: 0.94 [OpenCV Zero-Delay Burn-in]
              </div>
              <div style={{ position: 'absolute', top: '20px', left: '15px', width: '160px', height: '240px', border: '2px solid var(--color-cyber-cyan)', boxShadow: '0 0 10px rgba(0,240,255,0.5)' }} />

              <div style={{ position: 'absolute', bottom: '10px', right: '10px', background: 'rgba(255, 153, 0, 0.85)', color: '#000', fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, padding: '2px 6px', borderRadius: '2px' }}>
                helmet: 0.89
              </div>
              <div style={{ position: 'absolute', bottom: '30px', right: '15px', width: '70px', height: '70px', border: '2px solid var(--color-forge-amber)', boxShadow: '0 0 10px rgba(255,153,0,0.5)' }} />

              <span style={{ color: 'rgba(255,255,255,0.2)', fontFamily: 'var(--font-display)', fontSize: '20px' }}>
                FEED AO VIVO — STREAM OPENCV MJPEG ({camera.model})
              </span>
            </div>
          </div>
        ) : (
          <div style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>Stream Pausado</div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(10, 14, 23, 0.6)', padding: '12px 18px', borderRadius: 'var(--radius-md)', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={() => setIsPlaying(!isPlaying)} style={{ background: isPlaying ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)', border: `1px solid ${isPlaying ? 'var(--color-danger)' : 'var(--color-success)'}`, color: isPlaying ? 'var(--color-danger)' : 'var(--color-success)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontFamily: 'var(--font-display)', fontWeight: 600 }}>
            {isPlaying ? '⏸️ Pausar Feed' : '▶️ Retomar Feed'}
          </button>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-text-muted)' }}>
            Modelo Ativo: <strong style={{ color: 'var(--color-forge-amber)' }}>{camera.model}</strong>
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '240px' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-text-muted)' }}>Confiança ({Math.round(confidence * 100)}%):</span>
          <input type="range" min="0.1" max="0.9" step="0.05" value={confidence} onChange={(e) => setConfidence(parseFloat(e.target.value))} style={{ flex: 1, accentColor: 'var(--color-cyber-cyan)' }} />
        </div>
      </div>
    </div>
  );
};
"""


def main():
    for path, content in FILES.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"✅ UTF-8 OK: {path.name}")


if __name__ == "__main__":
    main()

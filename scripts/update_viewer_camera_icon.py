from pathlib import Path

file_path = Path(r"C:\Users\hades\Documents\HydraForge\web\src\components\cameras\LiveAnalyticsViewer.tsx")

content = """import React, { useState } from 'react';
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', background: 'rgba(0,0,0,0.75)', borderRadius: '4px', border: '1px solid rgba(0, 240, 255, 0.3)', color: 'var(--color-cyber-cyan)', fontSize: '13px', fontFamily: 'var(--font-mono)' }}>
            <span style={{ fontSize: '16px' }}>📹</span>
            <span>OpenCV Zero-Delay Burn-In Ativo | Feed: {camera.url}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
"""

file_path.write_text(content.strip() + "\n", encoding="utf-8")
print("LiveAnalyticsViewer updated with camera icon!")

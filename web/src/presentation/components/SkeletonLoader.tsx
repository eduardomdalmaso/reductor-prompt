import React from 'react';

export const SkeletonLoader: React.FC = () => {
  return (
    <div className="glass-panel" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Title skeleton */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="skeleton-box" style={{ width: '40%', height: '24px' }} />
        <div className="skeleton-box" style={{ width: '20%', height: '28px', borderRadius: '8px' }} />
      </div>

      {/* Paragraph lines skeleton */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px' }}>
        <div className="skeleton-box" style={{ width: '100%', height: '14px' }} />
        <div className="skeleton-box" style={{ width: '92%', height: '14px' }} />
        <div className="skeleton-box" style={{ width: '96%', height: '14px' }} />
        <div className="skeleton-box" style={{ width: '70%', height: '14px' }} />
      </div>

      {/* Code block skeleton */}
      <div className="skeleton-box" style={{ width: '100%', height: '100px', borderRadius: '10px', margin: '10px 0' }} />

      {/* Sources skeleton */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '10px', marginTop: '10px' }}>
        <div className="skeleton-box" style={{ height: '60px', borderRadius: '8px' }} />
        <div className="skeleton-box" style={{ height: '60px', borderRadius: '8px' }} />
      </div>
    </div>
  );
};

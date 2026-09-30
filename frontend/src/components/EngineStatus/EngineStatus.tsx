import React from 'react';

export const EngineStatus: React.FC = () => {
  return (
    <div className="engine-status-card">
      <div className="engine-card-header">
        <div className="engine-title-wrap">
          <span className="engine-pulse-dot" aria-hidden="true" />
          <span className="engine-title">DIAGNOSTIC ENGINE</span>
        </div>
        <span className="engine-online-badge">ONLINE</span>
      </div>

      <p className="engine-desc">
        Deterministic multi-tier inference engine with zero-click Settings deep linking and automated validation.
      </p>

      <div className="engine-capabilities-grid">
        <div className="capability-pill">
          <span className="cap-icon">⚡</span>
          <span className="cap-text">Fast-Path Retrieval (&lt;1ms)</span>
        </div>
        <div className="capability-pill">
          <span className="cap-icon">🛡️</span>
          <span className="cap-text">Semantic Domain Validator</span>
        </div>
        <div className="capability-pill">
          <span className="cap-icon">🔀</span>
          <span className="cap-text">Adaptive Guided Branching</span>
        </div>
        <div className="capability-pill">
          <span className="cap-icon">📱</span>
          <span className="cap-text">578 Bixby DeepLink Catalog</span>
        </div>
      </div>
    </div>
  );
};

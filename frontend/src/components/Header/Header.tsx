import React from 'react';

interface HeaderProps {
  onReset?: () => void;
  isSessionActive: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onReset, isSessionActive }) => {
  return (
    <header className="samsung-global-header">
      <div className="header-inner">
        {/* Left: Galaxy Branding */}
        <div className="header-left">
          <div className="samsung-pill-logo">
            <span className="logo-brand">SAMSUNG</span>
            <span className="logo-product">GALAXY</span>
          </div>
          <div className="header-divider" aria-hidden="true" />
          <div className="header-titles">
            <span className="header-main-title">Smart Guided Diagnostic Engine</span>
            <span className="header-sub-title">Theme 02 · One-Tap DeepLink Resolution</span>
          </div>
        </div>

        {/* Right: Engine Status & Actions */}
        <div className="header-right">
          {isSessionActive && (
            <button
              type="button"
              className="btn-header-end-session"
              onClick={onReset}
              title="Cancel and start a new diagnostic session"
            >
              <span>✕ End Session</span>
            </button>
          )}

          <div className="engine-status-pill" title="Engine initialized with sub-300ms fast-path cache response">
            <span className="status-live-dot" aria-hidden="true" />
            <div className="status-text-stack">
              <span className="status-primary">ENGINE ONLINE</span>
              <span className="status-secondary">CACHE &lt;300ms</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

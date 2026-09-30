import React, { useState } from 'react';
import { DiagnosticStep, SessionProgress } from '../../types/troubleshooting';

interface TroubleshootingStepProps {
  step: DiagnosticStep;
  progress?: SessionProgress;
  onFeedback: (result: 'passed' | 'failed' | 'skipped', details?: Record<string, any>) => void;
  loading: boolean;
}

function formatTargetSettingPath(step: DiagnosticStep): string {
  const desc = (step.actionable_deeplink?.description || '').trim();
  const act = (step.action_name || '').toLowerCase();
  const dl = (step.actionable_deeplink?.deeplink || '').toLowerCase();

  if (act.includes('wifi') || act.includes('wi-fi') || desc.toLowerCase().includes('wi-fi') || dl.includes('wifi')) {
    return 'Settings → Connections → Wi-Fi';
  }
  if (act.includes('bluetooth') || desc.toLowerCase().includes('bluetooth') || dl.includes('bluetooth')) {
    return 'Settings → Connections → Bluetooth';
  }
  if (act.includes('battery') || act.includes('power saving') || act.includes('charging') || desc.toLowerCase().includes('battery') || dl.includes('battery')) {
    return 'Settings → Battery and device care → Battery';
  }
  if (act.includes('navigation') || act.includes('gesture') || desc.toLowerCase().includes('navigation')) {
    return 'Settings → Display → Navigation bar';
  }
  if (act.includes('screen') || act.includes('display') || desc.toLowerCase().includes('display') || dl.includes('display')) {
    return 'Settings → Display';
  }
  if (act.includes('sound') || act.includes('volume') || act.includes('speaker') || act.includes('audio') || desc.toLowerCase().includes('sound')) {
    return 'Settings → Sounds and vibration';
  }
  if (act.includes('camera') || desc.toLowerCase().includes('camera')) {
    return 'Settings → Apps → Camera';
  }
  if (act.includes('reset network') || act.includes('reset')) {
    return 'Settings → General management → Reset → Reset network settings';
  }
  if (act.includes('email') || act.includes('account')) {
    return 'Settings → Accounts and backup → Manage accounts';
  }
  if (desc) {
    if (desc.includes('>') || desc.includes('→')) {
      return desc.replace(/>/g, '→');
    }
    return `Settings → ${desc}`;
  }
  return 'Settings → Connections';
}

export const TroubleshootingStep: React.FC<TroubleshootingStepProps> = ({
  step,
  progress,
  onFeedback,
  loading,
}) => {
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const stepNumber = progress?.current || 1;
  const totalSteps = progress?.total || 4;
  const targetPath = formatTargetSettingPath(step);

  const handleLaunchDeeplink = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!step.actionable_deeplink) return;
    setToastMessage(`🚀 Opening ${targetPath} via Samsung Settings Deeplink`);
    setTimeout(() => setToastMessage(null), 4000);
  };

  return (
    <div className={`troubleshooting-step-card ${step.is_remedial ? 'is-remedial-branch' : ''}`}>
      {/* Step Header */}
      <div className="step-card-header">
        <div className="step-count-badge">
          <span className="step-kicker">GUIDED CHECK</span>
          <span className="step-fraction">STEP {stepNumber} OF {totalSteps}</span>
        </div>

        <div className="step-badges-right">
          <span className={`step-type-pill ${step.category}`}>
            {step.category.toUpperCase()} ACTION
          </span>
          {step.is_remedial && (
            <span className="remedial-branch-pill">
              ⚡ REMEDIAL BRANCH ACTIVE
            </span>
          )}
        </div>
      </div>

      {/* Main Action Title & Instruction */}
      <h3 className="step-action-name">{step.action_name}</h3>
      <div className="step-instruction-container">
        <div className="instruction-icon">📋</div>
        <p className="instruction-body">{step.instruction}</p>
      </div>

      {/* Why & Expected Result Two-Column Grid */}
      <div className="step-rationales-grid">
        <div className="rationale-box why-box">
          <span className="rationale-label">WHY THIS STEP?</span>
          <p className="rationale-content">{step.why_this_step}</p>
        </div>
        <div className="rationale-box expected-box">
          <span className="rationale-label">EXPECTED RESULT</span>
          <p className="rationale-content">{step.expected_result}</p>
        </div>
      </div>

      {/* Deeplink Action Button */}
      {step.actionable_deeplink && (
        <div className="deeplink-interactive-panel">
          <div className="deeplink-header-block">
            <div className="deeplink-target-group">
              <span className="target-setting-label">Target Setting</span>
              <span className="target-setting-path">{targetPath}</span>
            </div>
            <button
              type="button"
              className="btn-launch-settings"
              onClick={handleLaunchDeeplink}
              title={`Open ${targetPath}`}
            >
              <span>OPEN SETTINGS</span>
              <span className="btn-arrow" aria-hidden="true">→</span>
            </button>
          </div>
          <div className="deeplink-footer-meta">
            <span className="verified-deeplink-badge">
              ✓ Verified Samsung Settings Deep Link
            </span>
          </div>
        </div>
      )}

      {toastMessage && (
        <div className="deeplink-toast-alert" role="alert">
          <span className="toast-icon">🚀</span>
          <span className="toast-text">{toastMessage}</span>
        </div>
      )}

      {/* Feedback Section */}
      <div className="step-feedback-zone">
        <div className="feedback-prompt-header">
          <h4 className="feedback-prompt-title">Did this solve the problem?</h4>
          <span className="feedback-prompt-sub">
            Your response dynamically determines if next verification is needed or a remedial branch should execute.
          </span>
        </div>

        <div className="feedback-actions-row">
          <button
            type="button"
            className="btn-feedback-resolved"
            disabled={loading}
            onClick={() => onFeedback('passed', { resolved: true, fixed: true })}
          >
            <span className="btn-check-icon">✓</span>
            <span className="btn-label-primary">YES, FIXED</span>
          </button>

          <button
            type="button"
            className="btn-feedback-continue"
            disabled={loading}
            onClick={() => onFeedback('failed', { resolved: false, continue: true })}
          >
            <span className="btn-continue-icon">→</span>
            <span className="btn-label-primary">NO, CONTINUE</span>
          </button>

          <button
            type="button"
            className="btn-feedback-skip-step"
            disabled={loading}
            onClick={() => onFeedback('skipped')}
          >
            <span>⏭ Skip</span>
          </button>
        </div>
      </div>
    </div>
  );
};

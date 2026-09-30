import React from 'react';
import { IntentState } from '../../types/troubleshooting';
import './IntentTabBar.css';

interface IntentTabBarProps {
  intents: IntentState[];
  activeIntentId?: string;
  onSwitchIntent: (intentId: string) => void;
  disabled?: boolean;
}

const DOMAIN_ICONS: Record<string, string> = {
  NETWORK: '📶',
  BLUETOOTH: '🎧',
  BATTERY: '🔋',
  DISPLAY: '📱',
  AUDIO: '🔊',
  CAMERA: '📷',
  EMAIL: '✉️',
  SYSTEM: '⚙️',
};

export const IntentTabBar: React.FC<IntentTabBarProps> = ({
  intents,
  activeIntentId,
  onSwitchIntent,
  disabled = false,
}) => {
  if (!intents || intents.length <= 1) {
    return null;
  }

  const resolvedCount = intents.filter((i) => i.resolved || i.status === 'RESOLVED').length;

  return (
    <div className="intent-tab-bar-container" role="region" aria-label="Troubleshooting Issue Selector">
      <div className="intent-tab-bar-header">
        <div className="intent-header-title-wrap">
          <span className="intent-multi-badge">MULTI-ISSUE DIAGNOSTIC</span>
          <span className="intent-count-text">
            {resolvedCount} of {intents.length} issues resolved
          </span>
        </div>
        <span className="intent-instruction-hint">Select an issue tab to troubleshoot:</span>
      </div>

      <div className="intent-tab-list" role="tablist">
        {intents.map((intent) => {
          const isActive = intent.id === activeIntentId;
          const isResolved = intent.resolved || intent.status === 'RESOLVED';
          const isEscalated = intent.escalated || intent.status === 'ESCALATED';
          const icon = DOMAIN_ICONS[intent.domain.toUpperCase()] || '🔧';

          let statusBadgeClass = 'intent-badge-pending';
          let statusBadgeText = 'Pending';

          if (isResolved) {
            statusBadgeClass = 'intent-badge-resolved';
            statusBadgeText = '✓ Resolved';
          } else if (isEscalated) {
            statusBadgeClass = 'intent-badge-escalated';
            statusBadgeText = '⚠️ Escalated';
          } else if (isActive) {
            statusBadgeClass = 'intent-badge-active';
            statusBadgeText = `Step ${intent.progress.current}/${intent.progress.total}`;
          } else if (intent.status === 'ACTIVE') {
            statusBadgeClass = 'intent-badge-in-progress';
            statusBadgeText = `Step ${intent.progress.current}/${intent.progress.total}`;
          }

          return (
            <button
              key={intent.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`intent-tab-btn ${isActive ? 'intent-tab-active' : ''} ${
                isResolved ? 'intent-tab-resolved' : ''
              }`}
              onClick={() => onSwitchIntent(intent.id)}
              disabled={disabled}
            >
              <div className="intent-tab-icon-wrap">
                <span className="intent-icon">{icon}</span>
              </div>
              <div className="intent-tab-info">
                <span className="intent-tab-domain">{intent.domain}</span>
                <span className="intent-tab-issue" title={intent.issue}>
                  {intent.issue}
                </span>
              </div>
              <span className={`intent-status-badge ${statusBadgeClass}`}>
                {statusBadgeText}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

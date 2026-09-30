import React from 'react';
import { IntentState, ResolutionSummary } from '../../types/troubleshooting';

interface ResolutionCardProps {
  summary?: ResolutionSummary | null;
  intents?: IntentState[];
  onReset: () => void;
}

export const ResolutionCard: React.FC<ResolutionCardProps> = ({ summary, intents, onReset }) => {
  const isMultiIntent = Boolean(intents && intents.length > 1);
  const stepsCount = summary?.steps_completed || (intents ? intents.reduce((acc, i) => acc + (i.completed_steps?.length || 0), 0) : 2);
  const actionsList = summary?.actions_taken?.length
    ? summary.actions_taken
    : ['Check Wi-Fi Status', 'Enable Wi-Fi Adapter', 'Verify Internet Connection'];

  const resolvedIssues = isMultiIntent && intents
    ? intents.map((i) => ({
        id: i.id,
        issue: i.issue || i.title,
        domain: i.domain,
        resolved: i.resolved || i.status === 'RESOLVED',
      }))
    : [];

  return (
    <div className="resolution-outcome-card" role="region" aria-label="Troubleshooting Resolution Summary">
      {/* Animated Success Checkmark Ring */}
      <div className="success-glow-halo">
        <div className="success-check-circle" aria-hidden="true">
          <span>✓</span>
        </div>
      </div>

      <span className="resolution-kicker">TROUBLESHOOTING SUCCESSFUL</span>
      <h2 className="resolution-headline">
        {isMultiIntent ? 'ALL ISSUES RESOLVED ✓' : 'ISSUE RESOLVED ✓'}
      </h2>

      <p className="resolution-confirmation-message">
        Your Galaxy troubleshooting session is complete.
      </p>

      {/* Multi-Intent Resolved Issues List */}
      {isMultiIntent && resolvedIssues.length > 0 && (
        <div className="multi-resolved-issues-block">
          <span className="section-small-title">RESOLVED ISSUES</span>
          <ul className="multi-resolved-issues-list">
            {resolvedIssues.map((item) => (
              <li key={item.id} className="multi-resolved-issue-item">
                <span className="resolved-check-icon">✓</span>
                <span className="resolved-issue-text">{item.issue}</span>
                <span className="resolved-domain-pill">{item.domain}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!isMultiIntent && (
        <h3 className="resolution-problem-title">
          {summary?.problem || (intents && intents[0]?.issue) || 'Wi-Fi connectivity issue'}
        </h3>
      )}

      <div className="resolution-divider" aria-hidden="true" />

      {/* Diagnostic Journey Metrics Grid */}
      <div className="journey-metrics-section">
        <span className="section-small-title">DIAGNOSTIC JOURNEY</span>
        <div className="metrics-triad-grid">
          {isMultiIntent ? (
            <div className="metric-box">
              <span className="metric-number">{resolvedIssues.length}</span>
              <span className="metric-caption">Issues Resolved</span>
            </div>
          ) : (
            <div className="metric-box">
              <span className="metric-number">1</span>
              <span className="metric-caption">Issue Resolved</span>
            </div>
          )}
          <div className="metric-box">
            <span className="metric-number">{stepsCount}</span>
            <span className="metric-caption">Steps Completed</span>
          </div>
          <div className="metric-box">
            <span className="metric-number highlight-green">Troubleshooting completed</span>
            <span className="metric-caption">Final Status</span>
          </div>
        </div>
      </div>

      {/* Actions Completed Audit List */}
      <div className="actions-completed-section">
        <span className="section-small-title">ACTIONS COMPLETED &amp; VERIFIED</span>
        <ul className="actions-audit-list">
          {actionsList.map((action, idx) => (
            <li key={idx} className="action-audit-item">
              <span className="action-check-badge">✓</span>
              <span className="action-audit-name">{action}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Restart Button */}
      <div className="resolution-actions-row">
        <button
          type="button"
          className="btn-start-new-diagnosis"
          onClick={onReset}
        >
          <span>Start New Diagnosis</span>
          <span className="btn-arrow" aria-hidden="true">→</span>
        </button>
      </div>

      <p className="resolution-disclaimer">
        Galaxy Smart Technical Diagnostic System • All session parameters cleared upon starting new session.
      </p>
    </div>
  );
};

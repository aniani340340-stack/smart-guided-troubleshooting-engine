import React from 'react';
import { EscalationSummary } from '../../types/troubleshooting';

interface EscalationCardProps {
  summary?: EscalationSummary | null;
  onReset: () => void;
}

export const EscalationCard: React.FC<EscalationCardProps> = ({ summary, onReset }) => {
  return (
    <div className="escalation-outcome-card">
      <div className="escalation-glow-halo">
        <div className="escalation-alert-circle" aria-hidden="true">
          <span>⚠️</span>
        </div>
      </div>

      <span className="escalation-kicker">ADDITIONAL ASSISTANCE REQUIRED</span>
      <h2 className="escalation-headline">FURTHER ASSISTANCE MAY BE REQUIRED</h2>
      <p className="escalation-lead-message">
        The available guided software troubleshooting steps did not resolve the reported issue.
      </p>

      <div className="escalation-recommendation-box">
        <div className="rec-badge-row">
          <span className="rec-badge">RECOMMENDED NEXT STEP</span>
        </div>
        <p className="rec-instruction">
          {summary?.recommended_action ||
            'Contact Samsung Support or visit an authorized Samsung Service Center for hardware diagnostics and technician inspection.'}
        </p>
      </div>

      {summary?.diagnostic_report && (
        <div className="technician-triage-report">
          <span className="triage-title">📋 Technician Triage Handover Report (Diagnostics Log):</span>
          <pre className="triage-json">
            {JSON.stringify(summary.diagnostic_report, null, 2)}
          </pre>
        </div>
      )}

      <div className="escalation-actions-row">
        <button
          type="button"
          className="btn-start-new-diagnosis"
          onClick={onReset}
        >
          <span>Start New Diagnosis</span>
          <span className="btn-arrow" aria-hidden="true">→</span>
        </button>
      </div>

      <p className="escalation-disclaimer">
        Software diagnostics completed. Hardware integrity has not been definitively determined without physical test bench evaluation.
      </p>
    </div>
  );
};

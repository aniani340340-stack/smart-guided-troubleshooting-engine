import React from 'react';
import { TroubleshootingSessionState } from '../../types/troubleshooting';

interface EventTimelineProps {
  session: TroubleshootingSessionState;
}

export const EventTimeline: React.FC<EventTimelineProps> = ({ session }) => {
  const completed = session.completed_steps || [];
  const failed = session.failed_steps || [];
  const currentStep = session.current_step;

  return (
    <div className="adaptive-event-timeline-card">
      <div className="timeline-header-bar">
        <div className="timeline-title-group">
          <span className="timeline-icon">🧭</span>
          <span className="timeline-heading">ADAPTIVE DIAGNOSTIC TRACE</span>
        </div>
        <span className="live-engine-tag">LIVE ENGINE</span>
      </div>

      <p className="timeline-explainer">
        Real-time execution log verifying multi-turn intent understanding, symptom classification, and adaptive graph branching.
      </p>

      <ol className="adaptive-trace-list">
        {/* Step 1: Complaint Understood */}
        <li className="trace-item completed">
          <div className="trace-marker">✓</div>
          <div className="trace-body">
            <span className="trace-title">Complaint Understood</span>
            <span className="trace-subtitle">Extracted canonical technical symptoms</span>
          </div>
        </li>

        {/* Step 2: Device Context Identified */}
        <li className="trace-item completed">
          <div className="trace-marker">✓</div>
          <div className="trace-body">
            <span className="trace-title">Device Context Identified</span>
            <span className="trace-subtitle">
              {session.device_context?.device_model || 'Galaxy Device'} ({session.device_context?.os_version || 'One UI 6.1'})
            </span>
          </div>
        </li>

        {/* Step 3: Diagnosis Generated */}
        <li className="trace-item completed">
          <div className="trace-marker">✓</div>
          <div className="trace-body">
            <span className="trace-title">Diagnosis Generated</span>
            <span className="trace-subtitle">
              {session.diagnosis?.title || 'Condition classified'}
            </span>
          </div>
        </li>

        {/* Failed Steps & Remedial Branches */}
        {failed.map((s, idx) => (
          <React.Fragment key={`failed_${s.step_id}_${idx}`}>
            <li className="trace-item failed">
              <div className="trace-marker">✕</div>
              <div className="trace-body">
                <span className="trace-title">{s.action_name} — Unresolved</span>
                <span className="trace-subtitle">User reported step did not fix problem</span>
              </div>
            </li>
            <li className="trace-item remedial-branch">
              <div className="trace-marker">⚡</div>
              <div className="trace-body">
                <span className="trace-title">Remedial Branch Activated</span>
                <span className="trace-subtitle">Dynamic fallback injected by diagnostic graph</span>
              </div>
            </li>
          </React.Fragment>
        ))}

        {/* Completed Intermediate Steps */}
        {completed.map((s, idx) => (
          <li key={`comp_${s.step_id}_${idx}`} className="trace-item completed">
            <div className="trace-marker">✓</div>
            <div className="trace-body">
              <span className="trace-title">{s.action_name} Completed</span>
              <span className="trace-subtitle">Step verified successfully</span>
            </div>
          </li>
        ))}

        {/* Current Active Step */}
        {currentStep && (
          <li className={`trace-item active ${currentStep.is_remedial ? 'remedial-node' : ''}`}>
            <div className="trace-marker pulse">→</div>
            <div className="trace-body">
              <div className="active-title-row">
                <span className="trace-title">{currentStep.action_name}</span>
                {currentStep.is_remedial && (
                  <span className="trace-remedial-badge">REMEDIAL</span>
                )}
              </div>
              <span className="trace-subtitle">Awaiting user confirmation or settings verification</span>
            </div>
          </li>
        )}

        {/* Resolved State */}
        {(session.status === 'RESOLVED' || session.resolved) && (
          <li className="trace-item resolved">
            <div className="trace-marker">★</div>
            <div className="trace-body">
              <span className="trace-title">Problem Confirmed Resolved</span>
              <span className="trace-subtitle">All targeted diagnostic criteria satisfied</span>
            </div>
          </li>
        )}

        {/* Escalated State */}
        {(session.status === 'ESCALATED' || session.escalated) && (
          <li className="trace-item escalated">
            <div className="trace-marker">⚠️</div>
            <div className="trace-body">
              <span className="trace-title">Samsung Support Handover</span>
              <span className="trace-subtitle">Safe software remedies completed; triage report prepared</span>
            </div>
          </li>
        )}
      </ol>
    </div>
  );
};

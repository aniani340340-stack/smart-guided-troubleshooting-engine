import React from 'react';
import { SessionProgress } from '../../types/troubleshooting';

interface ProgressTimelineProps {
  progress?: SessionProgress;
}

interface MilestoneStage {
  label: string;
  stageStep: number;
}

const STAGES: MilestoneStage[] = [
  { label: 'Understand', stageStep: 1 },
  { label: 'Diagnose', stageStep: 2 },
  { label: 'Check', stageStep: 3 },
  { label: 'Verify', stageStep: 4 },
  { label: 'Resolve', stageStep: 5 },
];

export const ProgressTimeline: React.FC<ProgressTimelineProps> = ({ progress }) => {
  const currentStep = progress?.current || 1;
  const total = Math.max(progress?.total || 4, 4);

  // Map 1..total to the 5 milestones
  const activeMilestoneIndex = Math.min(
    Math.floor(((currentStep - 1) / Math.max(total, 1)) * STAGES.length),
    STAGES.length - 1
  );

  return (
    <div className="progress-timeline-card">
      <div className="progress-card-header">
        <span className="progress-title">DIAGNOSTIC PROGRESS</span>
        <span className="step-tracker-pill">
          STEP {currentStep} OF {total}
        </span>
      </div>

      <div className="milestone-steps-track">
        {STAGES.map((stage, idx) => {
          const isDone = idx < activeMilestoneIndex;
          const isActive = idx === activeMilestoneIndex;

          let statusClass = 'upcoming';
          if (isDone) statusClass = 'completed';
          else if (isActive) statusClass = 'active';

          return (
            <React.Fragment key={stage.label}>
              <div className={`milestone-node ${statusClass}`}>
                <div className="milestone-badge">
                  {isDone ? (
                    <span>✓</span>
                  ) : isActive ? (
                    <span className="active-dot" />
                  ) : (
                    <span className="upcoming-dot" />
                  )}
                </div>
                <span className="milestone-label">{stage.label}</span>
              </div>
              {idx < STAGES.length - 1 && (
                <div className={`milestone-connector ${idx < activeMilestoneIndex ? 'done' : ''}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

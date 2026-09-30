import React from 'react';
import { DiagnosticStep, ValidationResult } from '../../types/troubleshooting';

interface VerificationPanelProps {
  step: DiagnosticStep;
  validationResult: ValidationResult | null;
  loading: boolean;
  onValidate: () => void;
}

export const VerificationPanel: React.FC<VerificationPanelProps> = ({
  step,
  validationResult,
  loading,
  onValidate,
}) => {
  const hasValidation = Boolean(step.validation_deeplink);

  return (
    <div className="telemetry-verification-card">
      <div className="verif-card-header">
        <div className="verif-title-group">
          <span className="verif-icon">⚡</span>
          <div className="verif-title-stack">
            <span className="verif-title">AUTOMATED VERIFICATION</span>
            <span className="verif-tag">SIMULATED TELEMETRY BINDING</span>
          </div>
        </div>

        <button
          type="button"
          className="btn-trigger-verification"
          disabled={loading}
          onClick={onValidate}
        >
          {loading ? (
            <span>Checking Telemetry...</span>
          ) : (
            <>
              <span>Run Automated Check</span>
              <span className="btn-bolt">⚡</span>
            </>
          )}
        </button>
      </div>

      {hasValidation && step.validation_deeplink && (
        <div className="telemetry-binding-indicator">
          <span className="binding-label">Bound State Key:</span>
          <code className="binding-key-code">{step.validation_deeplink.key}</code>
          {step.validation_deeplink.condition && (
            <span className="binding-condition-tag">
              Condition: {step.validation_deeplink.condition} ({String(step.validation_deeplink.value)})
            </span>
          )}
        </div>
      )}

      {validationResult && (
        <div className={`verification-outcome-box ${validationResult.is_valid ? 'is-valid' : 'is-invalid'}`}>
          <div className="outcome-icon-col">
            <span className="outcome-symbol">{validationResult.is_valid ? '✓' : '⚠️'}</span>
          </div>
          <div className="outcome-content-col">
            <div className="outcome-status-line">
              <span className="outcome-badge-text">
                {validationResult.is_valid ? 'VERIFICATION PASSED' : 'CHECK FAILED / DISCREPANCY'}
              </span>
              <span className="outcome-key-label">Key: {validationResult.key}</span>
            </div>
            <p className="outcome-message-text">{validationResult.message}</p>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { useTroubleshootingSession } from '../../hooks/useTroubleshootingSession';
import { Header } from '../../components/Header/Header';
import { ProblemInput } from '../../components/ProblemInput/ProblemInput';
import { QuickScenario, QuickScenarioItem } from '../../components/QuickScenario/QuickScenario';
import { DeviceContextCard } from '../../components/DeviceContextCard/DeviceContextCard';
import { EngineStatus } from '../../components/EngineStatus/EngineStatus';
import { DiagnosisCard } from '../../components/DiagnosisCard/DiagnosisCard';
import { ProgressTimeline } from '../../components/ProgressTimeline/ProgressTimeline';
import { TroubleshootingStep } from '../../components/TroubleshootingStep/TroubleshootingStep';
import { VerificationPanel } from '../../components/VerificationPanel/VerificationPanel';
import { DeviceStatus } from '../../components/DeviceStatus/DeviceStatus';
import { EventTimeline } from '../../components/EventTimeline/EventTimeline';
import { ResolutionCard } from '../../components/ResolutionCard/ResolutionCard';
import { EscalationCard } from '../../components/EscalationCard/EscalationCard';
import { IntentTabBar } from '../../components/IntentTabBar/IntentTabBar';

export const TroubleshootingPage: React.FC = () => {
  const {
    session,
    loading,
    error,
    telemetry,
    validationResult,
    validationLoading,
    start,
    feedback,
    switchIntent,
    validateCurrentStep,
    toggleTelemetry,
    reset,
  } = useTroubleshootingSession();

  const [query, setQuery] = useState('');
  const [deviceModel, setDeviceModel] = useState('Galaxy S22');
  const [osVersion, setOsVersion] = useState('One UI 6.1 (Android 14)');
  const [deviceType, setDeviceType] = useState('Phone');
  const [accessory, setAccessory] = useState<string | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);

  // Synchronize active device context when backend returns resolved session
  useEffect(() => {
    if (session?.device_context) {
      const resolvedModel = session.device_context.model || session.device_context.device_model;
      if (resolvedModel && resolvedModel !== deviceModel) {
        setDeviceModel(resolvedModel);
      }
      if (session.device_context.os_version && session.device_context.os_version !== osVersion) {
        setOsVersion(session.device_context.os_version);
      }
      if (session.device_context.device_type) {
        setDeviceType(session.device_context.device_type);
      }
      const resolvedAccessory = session.accessory || session.device_context.accessory || null;
      setAccessory(resolvedAccessory);
    }
  }, [session?.device_context, session?.accessory]);

  const isResolved = session?.status === 'RESOLVED' || session?.resolved === true;
  const isEscalated = session?.status === 'ESCALATED' || session?.escalated === true;
  const isComplete = isResolved || isEscalated;
  const isDiagnosing = Boolean(session && !isComplete && session.current_step);

  const handleStartDiagnosis = (imageData?: string | null, errorCode?: string | null) => {
    if (!query.trim()) return;
    start(query.trim(), deviceModel, osVersion, imageData, errorCode);
  };

  const handleSelectScenario = (scenario: QuickScenarioItem) => {
    setSelectedScenarioId(scenario.id);
    setQuery(scenario.prompt);
    setDeviceModel(scenario.defaultDevice);
    setOsVersion(scenario.defaultOs);
    setAccessory(null);
    // Auto-scroll to problem input
    const el = document.getElementById('problem-textarea');
    if (el) el.focus();
  };

  const handleResetSession = () => {
    reset();
    setSelectedScenarioId(null);
    setAccessory(null);
  };

  return (
    <div className="galaxy-troubleshooting-app">
      {/* Fixed/Sticky Samsung Galaxy Header */}
      <Header
        onReset={handleResetSession}
        isSessionActive={Boolean(session)}
      />

      <main className="main-content-viewport">
        {/* Error Notification Bar */}
        {error && (
          <div className="app-error-banner" role="alert">
            <div className="error-copy-stack">
              <span className="error-icon">⚠️</span>
              <div className="error-text-wrap">
                <span className="error-heading">Diagnostic Engine Notice</span>
                <span className="error-detail">
                  {error.includes('Failed to fetch')
                    ? 'Diagnostic engine is temporarily unavailable. Ensure the FastAPI backend is running on http://localhost:8000.'
                    : error}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleResetSession}
              className="btn-dismiss-error"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Global Loading Overlay */}
        {loading && !session && (
          <div className="loading-curtain-overlay" aria-live="polite">
            <div className="loading-card-modal">
              <div className="loading-pulsing-rings">
                <div className="ring ring-1" />
                <div className="ring ring-2" />
                <div className="ring ring-3" />
              </div>
              <h3 className="loading-modal-title">UNDERSTANDING YOUR PROBLEM</h3>
              <ul className="loading-stages-list">
                <li className="active-stage">
                  <span className="dot pulse" /> Extracting technical symptoms &amp; intent
                </li>
                <li className="active-stage">
                  <span className="dot pulse" /> Identifying Galaxy device context
                </li>
                <li className="active-stage">
                  <span className="dot pulse" /> Checking fast-path cache &amp; semantic domain consistency
                </li>
              </ul>
              <span className="loading-sla-tag">CACHE &lt;300ms Target</span>
            </div>
          </div>
        )}

        {/* ====================================================
            VIEW 1: LANDING PAGE (HERO + INPUT + QUICK SCENARIOS)
           ==================================================== */}
        {!session && (
          <div className="landing-layout-container">
            {/* Hero Title Section */}
            <div className="hero-heading-block">
              <span className="hero-kicker-badge">
                <span className="sparkle">✦</span>
                <span>SMART DIAGNOSTIC</span>
              </span>
              <h1 className="hero-main-headline">
                What's wrong with your Galaxy?
              </h1>
              <p className="hero-subtext">
                Describe the problem in your own words and we'll guide you through a verified step-by-step diagnosis.
              </p>
            </div>

            {/* Primary Visual Hero: Problem Input Card */}
            <ProblemInput
              query={query}
              onQueryChange={setQuery}
              onSubmit={handleStartDiagnosis}
              loading={loading}
            />

            {/* Quick Diagnostics Responsive Scenario Cards */}
            <QuickScenario
              onSelectScenario={handleSelectScenario}
              selectedId={selectedScenarioId}
              disabled={loading}
            />

            {/* Secondary Utility Row (Device Context + Engine Status) */}
            <div className="landing-utility-row">
              <DeviceContextCard
                deviceModel={deviceModel}
                osVersion={osVersion}
                deviceType={deviceType}
                accessory={accessory}
                onDeviceChange={(model, os) => {
                  setDeviceModel(model);
                  setOsVersion(os);
                }}
              />
              <EngineStatus />
            </div>
          </div>
        )}

        {/* ====================================================
            VIEW 2: ACTIVE DIAGNOSIS WORKSPACE
           ==================================================== */}
        {session && !isComplete && (
          <div className="diagnostic-workspace-layout">
            {/* Primary Left Column: Diagnosis & Guided Step Interaction (68%) */}
            <div className="workspace-main-column">
              {session.intents && session.intents.length > 1 && (
                <IntentTabBar
                  intents={session.intents}
                  activeIntentId={session.active_intent_id}
                  onSwitchIntent={(intentId) => switchIntent(intentId)}
                  disabled={loading}
                />
              )}

              {(() => {
                const activeIntent = session.intents?.find(
                  (i) => i.id === session.active_intent_id
                );
                return (
                  <DiagnosisCard
                    deviceModel={session.device_context?.model || session.device_context?.device_model || deviceModel}
                    osVersion={session.device_context?.os_version || osVersion}
                    diagnosis={session.diagnosis}
                    accessory={accessory || session.accessory || session.device_context?.accessory}
                    issue={activeIntent?.issue || session.query}
                    domain={activeIntent?.domain}
                  />
                );
              })()}

              {isDiagnosing && session.current_step && (
                <>
                  <TroubleshootingStep
                    step={session.current_step}
                    progress={session.progress}
                    onFeedback={(res, details) => feedback(res, details, session.active_intent_id)}
                    loading={loading}
                  />

                  <VerificationPanel
                    step={session.current_step}
                    validationResult={validationResult}
                    loading={validationLoading}
                    onValidate={validateCurrentStep}
                  />
                </>
              )}
            </div>

            {/* Secondary Right Column: Progress, Simulated Telemetry & Adaptive Trace (32%) */}
            <div className="workspace-sidebar-column">
              <DeviceContextCard
                deviceModel={session.device_context?.model || session.device_context?.device_model || deviceModel}
                osVersion={session.device_context?.os_version || osVersion}
                deviceType={session.device_context?.device_type || deviceType}
                accessory={accessory || session.accessory || session.device_context?.accessory}
                onDeviceChange={(model, os) => {
                  setDeviceModel(model);
                  setOsVersion(os);
                }}
              />

              <ProgressTimeline progress={session.progress} />

              <DeviceStatus
                telemetry={telemetry}
                onToggle={toggleTelemetry}
              />

              <EventTimeline session={session} />
            </div>
          </div>
        )}

        {/* ====================================================
            VIEW 3: OUTCOME SCREENS (RESOLVED / ESCALATED)
           ==================================================== */}
        {isComplete && (
          <div className="outcome-view-container">
            {isResolved && (
              <ResolutionCard
                summary={session.resolution_summary}
                intents={session.intents}
                onReset={handleResetSession}
              />
            )}

            {isEscalated && (
              <EscalationCard
                summary={session.escalation_summary}
                onReset={handleResetSession}
              />
            )}
          </div>
        )}
      </main>

      {/* Global Site Footer */}
      <footer className="samsung-global-footer">
        <div className="footer-inner">
          <p className="footer-brand-text">
            Samsung Galaxy Smart Guided Diagnostic Engine • Theme 02 Hackathon Showcase
          </p>
          <p className="footer-disclaimer-text">
            Settings actions executed via safe deep link emulation. Device telemetry state is simulated for testing.
          </p>
        </div>
      </footer>
    </div>
  );
};

"""Interactive Web UI Dashboard for the Smart Guided Troubleshooting Engine.
Provides both Guided Diagnostic Mode (Interactive Multi-Turn Session) and
Fast-Path API Inspector (One-shot Direct Troubleshooting & Schema ablation).
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Smart Guided Troubleshooting Engine | Samsung Galaxy</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-primary: #0a0e17;
      --bg-surface: #111827;
      --bg-card: #162032;
      --bg-card-hover: #1c2940;
      --border-color: rgba(255, 255, 255, 0.08);
      --accent-blue: #2563eb;
      --accent-cyan: #06b6d4;
      --accent-glow: rgba(37, 99, 235, 0.35);
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --badge-auto: #10b981;
      --badge-manual: #3b82f6;
      --badge-critical: #f59e0b;
      --color-success: #10b981;
      --color-danger: #ef4444;
      --font-main: 'Outfit', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: radial-gradient(circle at 50% 0%, #172554 0%, var(--bg-primary) 70%);
      color: var(--text-primary);
      font-family: var(--font-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      padding: 1.25rem 2.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color);
      backdrop-filter: blur(12px);
      background: rgba(10, 14, 23, 0.8);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }
    .logo-badge {
      background: linear-gradient(135deg, #2563eb, #06b6d4);
      padding: 0.4rem 0.85rem;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.9rem;
      letter-spacing: 0.5px;
      box-shadow: 0 0 15px var(--accent-glow);
    }
    .brand h1 { font-size: 1.35rem; font-weight: 600; letter-spacing: -0.3px; }

    .nav-tabs {
      display: flex;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      border-radius: 30px;
      padding: 0.25rem;
      gap: 0.25rem;
    }
    .nav-tab {
      padding: 0.45rem 1.15rem;
      border-radius: 20px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
      color: var(--text-secondary);
      border: none;
      background: transparent;
    }
    .nav-tab.active {
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #fff;
      box-shadow: 0 2px 10px var(--accent-glow);
    }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      padding: 0.4rem 0.9rem;
      border-radius: 20px;
      font-size: 0.85rem;
      font-weight: 500;
    }
    .pulse-dot {
      width: 8px; height: 8px;
      background: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 8px #10b981;
      animation: pulse 2s infinite;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

    main {
      flex: 1;
      max-width: 1350px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem 2rem;
    }

    .view-container { display: none; }
    .view-container.active { display: block; }

    /* Cards & Containers */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 1.75rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
      backdrop-filter: blur(10px);
    }
    .card-title {
      font-size: 1.15rem;
      font-weight: 600;
      margin-bottom: 1.25rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    /* Guided Mode Layout */
    .guided-grid {
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 1.75rem;
    }
    @media (max-width: 900px) {
      .guided-grid { grid-template-columns: 1fr; }
    }

    /* Interactive Step Card */
    .step-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border-color);
    }
    .step-indicator {
      font-size: 0.9rem;
      font-weight: 700;
      letter-spacing: 0.5px;
      color: #38bdf8;
      text-transform: uppercase;
      font-family: var(--font-mono);
    }
    .step-title {
      font-size: 1.35rem;
      font-weight: 700;
      margin-bottom: 0.75rem;
      color: #fff;
    }
    .step-instruction {
      font-size: 1.05rem;
      line-height: 1.6;
      color: #e2e8f0;
      margin-bottom: 1.25rem;
      background: rgba(0, 0, 0, 0.25);
      padding: 1rem 1.25rem;
      border-radius: 10px;
      border-left: 4px solid var(--accent-blue);
    }

    .info-block {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 1rem;
      margin-bottom: 1rem;
    }
    .info-label {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--accent-cyan);
      margin-bottom: 0.35rem;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }
    .info-text {
      font-size: 0.9rem;
      color: var(--text-secondary);
      line-height: 1.5;
    }

    /* Telemetry & Validation Widget */
    .telemetry-widget {
      background: #0d1424;
      border: 1px solid rgba(6, 182, 212, 0.3);
      border-radius: 12px;
      padding: 1.25rem;
      margin-bottom: 1.5rem;
    }
    .telemetry-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.85rem;
    }
    .telemetry-title {
      font-size: 0.85rem;
      font-weight: 700;
      color: #38bdf8;
      font-family: var(--font-mono);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .telemetry-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.6rem;
      margin-bottom: 1rem;
    }
    .telemetry-chip {
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 0.5rem 0.75rem;
      font-size: 0.8rem;
      font-family: var(--font-mono);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .telemetry-chip .val { font-weight: 600; }
    .telemetry-chip .val.true { color: #34d399; }
    .telemetry-chip .val.false { color: #f87171; }

    .validation-badge {
      padding: 0.6rem 0.9rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 500;
      margin-top: 0.75rem;
      display: none;
    }
    .validation-badge.pass {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid #10b981;
      color: #34d399;
      display: block;
    }
    .validation-badge.fail {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid #ef4444;
      color: #f87171;
      display: block;
    }

    /* Buttons */
    button.btn-primary {
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      border: none;
      color: #fff;
      font-weight: 600;
      font-size: 0.95rem;
      padding: 0.75rem 1.5rem;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 4px 15px var(--accent-glow);
    }
    button.btn-primary:hover {
      background: linear-gradient(135deg, #3b82f6, #2563eb);
      transform: translateY(-1px);
    }

    button.btn-simulate {
      background: rgba(6, 182, 212, 0.15);
      border: 1px solid var(--accent-cyan);
      color: #38bdf8;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      padding: 0.6rem 1rem;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }
    button.btn-simulate:hover {
      background: var(--accent-cyan);
      color: #000;
    }

    .feedback-section {
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.25rem;
      margin-top: 1rem;
    }
    .feedback-title {
      font-size: 0.95rem;
      font-weight: 600;
      margin-bottom: 0.85rem;
      color: #f1f5f9;
    }
    .feedback-row {
      display: flex;
      gap: 0.85rem;
      flex-wrap: wrap;
    }
    button.btn-yes {
      flex: 1;
      min-width: 140px;
      background: linear-gradient(135deg, #10b981, #059669);
      border: none;
      color: #fff;
      font-weight: 600;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }
    button.btn-yes:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4); }

    button.btn-no {
      flex: 1;
      min-width: 140px;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid #ef4444;
      color: #fca5a5;
      font-weight: 600;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }
    button.btn-no:hover { background: #ef4444; color: #fff; }

    button.btn-skip {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border-color);
      color: var(--text-secondary);
      font-weight: 500;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      cursor: pointer;
    }
    button.btn-skip:hover { background: rgba(255, 255, 255, 0.15); color: #fff; }

    /* Badges */
    .badge {
      font-size: 0.75rem;
      text-transform: uppercase;
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }
    .badge-auto { background: rgba(16, 185, 129, 0.2); color: var(--badge-auto); border: 1px solid var(--badge-auto); }
    .badge-manual { background: rgba(59, 130, 246, 0.2); color: var(--badge-manual); border: 1px solid var(--badge-manual); }
    .badge-critical { background: rgba(245, 158, 11, 0.2); color: var(--badge-critical); border: 1px solid var(--badge-critical); }

    /* Timeline */
    .timeline {
      list-style: none;
      position: relative;
      padding-left: 1.5rem;
    }
    .timeline::before {
      content: '';
      position: absolute;
      left: 6px;
      top: 10px;
      bottom: 10px;
      width: 2px;
      background: var(--border-color);
    }
    .timeline-item {
      position: relative;
      margin-bottom: 1.25rem;
      font-size: 0.9rem;
    }
    .timeline-item::before {
      content: '';
      position: absolute;
      left: -1.5rem;
      top: 5px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #334155;
      border: 2px solid var(--bg-card);
    }
    .timeline-item.done::before {
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }
    .timeline-item.active::before {
      background: #38bdf8;
      box-shadow: 0 0 8px #38bdf8;
    }
    .timeline-item .time-title { font-weight: 600; color: #fff; }
    .timeline-item .time-desc { font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.2rem; }

    /* Preset chips */
    .preset-chips { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.25rem; }
    .chip {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-color);
      color: var(--text-secondary);
      padding: 0.4rem 0.8rem;
      border-radius: 20px;
      font-size: 0.8rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .chip:hover {
      background: rgba(37, 99, 235, 0.2);
      border-color: var(--accent-blue);
      color: #fff;
    }

    textarea {
      width: 100%;
      background: #0d131f;
      border: 1px solid var(--border-color);
      border-radius: 10px;
      color: #fff;
      font-family: inherit;
      font-size: 0.95rem;
      padding: 1rem;
      resize: vertical;
      min-height: 100px;
      outline: none;
      transition: border-color 0.2s;
    }
    textarea:focus { border-color: var(--accent-blue); box-shadow: 0 0 10px var(--accent-glow); }

    /* Results Card: Resolved & Escalated */
    .outcome-card {
      text-align: center;
      padding: 3rem 2rem;
      border-radius: 16px;
    }
    .outcome-card.resolved {
      background: radial-gradient(circle at 50% 20%, rgba(16, 185, 129, 0.15) 0%, rgba(17, 24, 39, 0.8) 70%);
      border: 1px solid #10b981;
    }
    .outcome-card.escalated {
      background: radial-gradient(circle at 50% 20%, rgba(245, 158, 11, 0.15) 0%, rgba(17, 24, 39, 0.8) 70%);
      border: 1px solid #f59e0b;
    }
    .outcome-icon {
      font-size: 3.5rem;
      margin-bottom: 1rem;
    }
    .outcome-title {
      font-size: 1.75rem;
      font-weight: 700;
      margin-bottom: 0.75rem;
    }
    .outcome-desc {
      font-size: 1rem;
      color: #cbd5e1;
      max-width: 600px;
      margin: 0 auto 1.5rem auto;
      line-height: 1.6;
    }

    .deeplink-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(37, 99, 235, 0.15);
      border: 1px solid var(--accent-blue);
      color: #60a5fa;
      padding: 0.6rem 1.1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-family: var(--font-mono);
      text-decoration: none;
      transition: all 0.2s;
    }
    .deeplink-btn:hover { background: var(--accent-blue); color: #fff; }

    pre.json-view {
      background: #090d16;
      padding: 1rem;
      border-radius: 10px;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      overflow-x: auto;
      max-height: 250px;
      color: #a5f3fc;
      border: 1px solid var(--border-color);
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="logo-badge">GALAXY · THEME 02</div>
      <h1>Smart Guided Troubleshooting Engine</h1>
    </div>

    <div class="nav-tabs">
      <button class="nav-tab active" onclick="switchView('guided')">Guided Diagnostic Mode</button>
      <button class="nav-tab" onclick="switchView('inspector')">Fast-Path API Inspector</button>
    </div>

    <div class="status-badge">
      <div class="pulse-dot"></div>
      Sub-300ms SLA Ready · Active Simulation
    </div>
  </header>

  <main>
    <!-- VIEW 1: GUIDED DIAGNOSTIC MODE (Interactive Multi-Turn) -->
    <div id="viewGuided" class="view-container active">
      
      <!-- Diagnostic Initializer Form (Shown when no session active) -->
      <div id="guidedInitContainer" class="card" style="max-width: 800px; margin: 0 auto;">
        <div class="card-title">
          <span>Start Interactive Troubleshooting Session</span>
          <span style="font-size: 0.8rem; color: #38bdf8;">Multi-Turn Guided Flow</span>
        </div>

        <div style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 1.25rem;">
          Select a common device issue or enter a complaint. The engine will guide you through step-by-step verification, live telemetry checks, and resolution branches.
        </div>

        <div class="preset-chips">
          <span class="chip" onclick="setGuidedPreset('My Galaxy S22 screen turns completely blank or white and no text appears')">Blank Display</span>
          <span class="chip" onclick="setGuidedPreset('My Galaxy S22 Wi-Fi keeps disconnecting and cannot load web pages')">Intermittent Wi-Fi</span>
          <span class="chip" onclick="setGuidedPreset('My Galaxy Z Flip 7 screen is cracked again right where it folds')">Cracked Fold</span>
          <span class="chip" onclick="setGuidedPreset('My tablet screen flickers and then goes blank when opening Gmail')">Email Sync / Flicker</span>
          <span class="chip" onclick="setGuidedPreset('Floating circle with quick shortcuts hovering on screen, want to remove')">Floating Menu</span>
        </div>

        <div style="display: flex; gap: 1rem; margin-bottom: 1.25rem;">
          <div style="flex: 1;">
            <label style="font-size: 0.8rem; color: var(--text-secondary); display: block; margin-bottom: 0.35rem;">Device Model</label>
            <input type="text" id="deviceModelInput" value="Galaxy S22 Ultra" style="width: 100%; background: #0d131f; border: 1px solid var(--border-color); border-radius: 8px; color: #fff; padding: 0.6rem 0.8rem; font-family: inherit;">
          </div>
          <div style="flex: 1;">
            <label style="font-size: 0.8rem; color: var(--text-secondary); display: block; margin-bottom: 0.35rem;">Software Version</label>
            <input type="text" id="osVersionInput" value="One UI 6.1 (Android 14)" style="width: 100%; background: #0d131f; border: 1px solid var(--border-color); border-radius: 8px; color: #fff; padding: 0.6rem 0.8rem; font-family: inherit;">
          </div>
        </div>

        <textarea id="guidedQueryInput" placeholder="Describe the device problem in natural language..."></textarea>

        <div style="margin-top: 1.25rem; display: flex; justify-content: flex-end;">
          <button class="btn-primary" id="btnStartSession" onclick="startGuidedSession()">
            🚀 Start Guided Diagnosis
          </button>
        </div>
      </div>

      <!-- Active Session View -->
      <div id="guidedSessionActive" style="display: none;">
        
        <!-- Header status bar -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; background: var(--bg-card); padding: 1rem 1.5rem; border-radius: 12px; border: 1px solid var(--border-color);">
          <div>
            <div style="font-size: 0.8rem; color: #38bdf8; font-weight: 700; text-transform: uppercase;" id="sessionDeviceBadge">Galaxy S22 Ultra · One UI 6.1</div>
            <div style="font-size: 1.15rem; font-weight: 700; color: #fff;" id="sessionDiagnosisTitle">Diagnosing Device Issue</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 0.8rem; color: var(--text-secondary);">CONFIDENCE</div>
            <div style="font-size: 1.1rem; font-weight: 700; font-family: var(--font-mono); color: #34d399;" id="sessionConfidence">0.95</div>
          </div>
        </div>

        <div class="guided-grid">
          <!-- Left Column: Current Active Step -->
          <div class="card">
            <div class="step-banner">
              <span class="step-indicator" id="stepProgressIndicator">STEP 1 / 4</span>
              <span class="badge badge-auto" id="stepCategoryBadge">AUTO</span>
            </div>

            <div class="step-title" id="stepActionTitle">Check Device Settings</div>
            <div class="step-instruction" id="stepInstructionText">Navigate to Settings and verify options.</div>

            <div class="info-block">
              <div class="info-label">💡 Why this step?</div>
              <div class="info-text" id="stepWhyText">Determines whether the issue is caused by misconfigured device options.</div>
            </div>

            <div class="info-block">
              <div class="info-label">🎯 Expected Result</div>
              <div class="info-text" id="stepExpectedText">Settings should be properly configured and display normal parameters.</div>
            </div>

            <div id="deeplinkContainer" style="margin-bottom: 1.25rem; display: none;">
              <a href="#" id="stepDeeplinkBtn" class="deeplink-btn" onclick="event.preventDefault(); alertDeeplink();">
                🚀 Launch Masked Settings Screen
              </a>
            </div>

            <!-- Simulated Telemetry & State Evaluation Widget -->
            <div class="telemetry-widget">
              <div class="telemetry-header">
                <span class="telemetry-title">⚡ SIMULATED DEVICE TELEMETRY</span>
                <button class="btn-simulate" onclick="simulateStepValidation()">[ CHECK / SIMULATE ]</button>
              </div>

              <div class="telemetry-grid" id="telemetryGrid">
                <!-- Populated dynamically with simulated telemetry chips -->
              </div>

              <div id="validationResultBadge" class="validation-badge"></div>
            </div>

            <!-- Step Feedback Section -->
            <div class="feedback-section">
              <div class="feedback-title">Did this action resolve your problem?</div>
              <div class="feedback-row">
                <button class="btn-yes" onclick="submitFeedback('passed')">✓ YES — FIXED</button>
                <button class="btn-no" onclick="submitFeedback('failed')">✗ NO — CONTINUE</button>
                <button class="btn-skip" onclick="submitFeedback('skipped')">⏭ SKIP STEP</button>
              </div>
            </div>
          </div>

          <!-- Right Column: Live Diagnostic Event Timeline -->
          <div class="card">
            <div class="card-title">
              <span>Diagnostic Event Timeline</span>
              <span id="sessionStatusPill" class="badge badge-auto">ACTIVE</span>
            </div>

            <ul class="timeline" id="eventTimeline">
              <!-- Dynamically populated with steps -->
            </ul>

            <div style="margin-top: 1.5rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
              <button style="width: 100%; background: transparent; border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; padding: 0.5rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem;" onclick="resetGuidedSession()">
                Cancel Diagnostic Session
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Resolved Outcome View -->
      <div id="guidedResolvedView" class="card outcome-card resolved" style="display: none; max-width: 750px; margin: 2rem auto;">
        <div class="outcome-icon">✅</div>
        <div class="outcome-title" style="color: #34d399;">ISSUE RESOLVED</div>
        <div class="outcome-desc" id="resolvedProblemText">Your Galaxy device configuration has been successfully restored.</div>

        <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 2rem; font-family: var(--font-mono);">
          <div>
            <div style="font-size: 0.8rem; color: var(--text-secondary);">STEPS COMPLETED</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #fff;" id="resolvedStepsCount">3 / 4</div>
          </div>
          <div>
            <div style="font-size: 0.8rem; color: var(--text-secondary);">DIAGNOSTIC TIME</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #38bdf8;" id="resolvedTimeCount">18s</div>
          </div>
        </div>

        <div style="text-align: left; background: rgba(0, 0, 0, 0.3); border-radius: 10px; padding: 1.25rem; margin-bottom: 2rem; border: 1px solid var(--border-color);">
          <div style="font-size: 0.85rem; font-weight: 700; color: #34d399; margin-bottom: 0.5rem;">Actions Executed & Verified:</div>
          <ul id="resolvedActionsList" style="list-style: disc; padding-left: 1.5rem; font-size: 0.9rem; color: #cbd5e1; line-height: 1.6;"></ul>
        </div>

        <button class="btn-primary" onclick="resetGuidedSession()">Start New Diagnosis</button>
      </div>

      <!-- Escalated Outcome View -->
      <div id="guidedEscalatedView" class="card outcome-card escalated" style="display: none; max-width: 750px; margin: 2rem auto;">
        <div class="outcome-icon">⚠️</div>
        <div class="outcome-title" style="color: #f59e0b;">ESCALATION RECOMMENDED</div>
        <div class="outcome-desc">
          We could not resolve the issue using available software diagnostics. Further assistance may be required.
        </div>

        <div style="text-align: left; background: rgba(0, 0, 0, 0.35); border-radius: 10px; padding: 1.25rem; margin-bottom: 2rem; border: 1px solid rgba(245, 158, 11, 0.3);">
          <div style="font-size: 0.85rem; font-weight: 700; color: #fbbf24; margin-bottom: 0.5rem;">Recommended Next Action:</div>
          <div style="font-size: 0.95rem; color: #f1f5f9; margin-bottom: 1rem;">
            Contact Samsung Support or visit an authorized Samsung Service Center for hardware inspection.
          </div>
          <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 0.35rem;">Diagnostic Handover Report:</div>
          <pre id="escalationReportJson" style="background: #090d16; padding: 0.75rem; border-radius: 8px; font-family: var(--font-mono); font-size: 0.75rem; color: #fed7aa; overflow-x: auto;"></pre>
        </div>

        <button class="btn-primary" onclick="resetGuidedSession()">Start New Diagnosis</button>
      </div>

    </div>

    <!-- VIEW 2: FAST-PATH API INSPECTOR (Existing direct troubleshooting dashboard) -->
    <div id="viewInspector" class="view-container">
      <div style="display: grid; grid-template-columns: 1fr 1.3fr; gap: 2rem;">
        
        <!-- Left Column: Input -->
        <div class="card">
          <div class="card-title">Device Complaint Input</div>
          
          <div class="preset-chips">
            <span class="chip" onclick="setInspectorPreset('My Galaxy S22 screen turns completely blank or white and no text appears')">Blank Display</span>
            <span class="chip" onclick="setInspectorPreset('My phone swipe navigation gestures are misbehaving and go the wrong way')">Swipe Gestures</span>
            <span class="chip" onclick="setInspectorPreset('My Galaxy Z Flip 7 screen is cracked again right where it folds')">Cracked Fold</span>
            <span class="chip" onclick="setInspectorPreset('Floating circle with quick shortcuts hovering on display, want to remove')">Floating Menu</span>
            <span class="chip" onclick="setInspectorPreset('Smart switch cannot scan qr code for transferring data')">Smart Switch</span>
          </div>

          <textarea id="inspectorQueryInput" placeholder="Describe the device problem in natural language..."></textarea>

          <div style="display: flex; gap: 1rem; margin-top: 1.25rem;">
            <button class="btn-primary" id="btnSubmitInspector" onclick="runInspectorTroubleshoot()">Diagnose & Generate Plan</button>
          </div>

          <div id="inspectorVariationsContainer" style="display: none; margin-top: 1.5rem; padding: 1rem; background: rgba(0,0,0,0.25); border-radius: 10px; border: 1px solid var(--border-color);">
            <div style="font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem; color: #38bdf8;">Query Variations (8-10 Multi-Register Paraphrases):</div>
            <div id="inspectorVariationsList" style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.6;"></div>
          </div>
        </div>

        <!-- Right Column: Remediation Plan -->
        <div class="card">
          <div class="card-title">
            <span>Actionable Remediation Plan</span>
            <span id="inspectorHitBadge" style="font-size: 0.8rem; font-weight: 500;"></span>
          </div>

          <div id="inspectorMetaBar" style="display: none; gap: 1.5rem; margin-bottom: 1.25rem; padding: 0.75rem 1rem; background: rgba(0,0,0,0.25); border-radius: 10px; font-size: 0.85rem;">
            <div>Latency: <span style="font-weight: 600; font-family: var(--font-mono); color: #38bdf8;" id="inspectorLatency">0 ms</span></div>
            <div>Cache: <span style="font-weight: 600; font-family: var(--font-mono);" id="inspectorCache">HIT</span></div>
            <div>Confidence: <span style="font-weight: 600; font-family: var(--font-mono); color: #34d399;" id="inspectorScore">0.95</span></div>
          </div>

          <div id="inspectorPlanContent">
            <div style="text-align: center; color: var(--text-secondary); padding: 4rem 1rem;">
              Select a preset or enter a customer complaint to evaluate raw contract responses.
            </div>
          </div>

          <div style="margin-top: 1.5rem;">
            <details>
              <summary style="font-size: 0.85rem; color: var(--text-secondary); cursor: pointer; margin-bottom: 0.5rem;">View Raw Validated JSON (Pydantic Contract)</summary>
              <pre class="json-view" id="inspectorRawJson">{ "status": "awaiting request" }</pre>
            </details>
          </div>
        </div>
      </div>
    </div>
  </main>

  <script>
    let activeSession = null;
    let currentStepData = null;
    let simulatedState = {};

    function switchView(viewName) {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.view-container').forEach(c => c.classList.remove('active'));

      if (viewName === 'guided') {
        document.querySelectorAll('.nav-tab')[0].classList.add('active');
        document.getElementById('viewGuided').classList.add('active');
      } else {
        document.querySelectorAll('.nav-tab')[1].classList.add('active');
        document.getElementById('viewInspector').classList.add('active');
      }
    }

    function setGuidedPreset(text) {
      document.getElementById('guidedQueryInput').value = text;
    }

    function setInspectorPreset(text) {
      document.getElementById('inspectorQueryInput').value = text;
      runInspectorTroubleshoot();
    }

    // --- Guided Diagnostic Session Management ---
    async function startGuidedSession() {
      const query = document.getElementById('guidedQueryInput').value.trim();
      if (!query) {
        alert("Please enter a device complaint.");
        return;
      }

      const deviceModel = document.getElementById('deviceModelInput').value.trim();
      const osVersion = document.getElementById('osVersionInput').value.trim();

      const btn = document.getElementById('btnStartSession');
      btn.innerText = "Analyzing Complaint...";
      btn.disabled = true;

      try {
        const res = await fetch('/v1/session/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: query,
            device_model: deviceModel,
            os_version: osVersion
          })
        });

        if (!res.ok) {
          throw new Error("HTTP " + res.status);
        }

        const data = await res.json();
        activeSession = data;
        await refreshTelemetry();
        renderSessionView(data);
      } catch (err) {
        alert("Failed to start troubleshooting session: " + err);
      } finally {
        btn.innerText = "🚀 Start Guided Diagnosis";
        btn.disabled = false;
      }
    }

    async function refreshTelemetry() {
      try {
        const res = await fetch('/v1/telemetry/state');
        if (res.ok) {
          simulatedState = await res.json();
          renderTelemetryGrid();
        }
      } catch (e) {
        console.error(e);
      }
    }

    function renderTelemetryGrid() {
      const grid = document.getElementById('telemetryGrid');
      if (!grid) return;
      const keysToShow = ["wifi_enabled", "internet_connected", "screen_responsive", "battery_level", "safe_mode", "double_tap_to_wake"];
      
      grid.innerHTML = keysToShow.map(k => {
        const val = simulatedState[k];
        const displayVal = typeof val === 'boolean' ? (val ? 'ON' : 'OFF') : val;
        const cls = typeof val === 'boolean' ? (val ? 'true' : 'false') : '';
        return `
          <div class="telemetry-chip" onclick="toggleTelemetryKey('${k}')" style="cursor: pointer;" title="Click to toggle simulated value">
            <span>${k.replace('_', ' ')}:</span>
            <span class="val ${cls}">${displayVal}</span>
          </div>`;
      }).join('');
    }

    async function toggleTelemetryKey(key) {
      if (typeof simulatedState[key] === 'boolean') {
        simulatedState[key] = !simulatedState[key];
      } else if (typeof simulatedState[key] === 'number') {
        simulatedState[key] = simulatedState[key] > 50 ? 25 : 85;
      }
      renderTelemetryGrid();
      await fetch('/v1/telemetry/state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(simulatedState)
      });
    }

    async function simulateStepValidation() {
      if (!activeSession) return;
      const badge = document.getElementById('validationResultBadge');
      badge.style.display = 'block';
      badge.className = 'validation-badge';
      badge.innerText = "Querying simulated device telemetry...";

      try {
        const res = await fetch(`/v1/session/${activeSession.session_id}/simulate-validation`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ state_overrides: simulatedState })
        });
        const data = await res.json();
        if (data.is_valid) {
          badge.className = 'validation-badge pass';
          badge.innerText = `✓ Check PASSED: ${data.message}`;
        } else {
          badge.className = 'validation-badge fail';
          badge.innerText = `✗ Check FAILED: ${data.message}`;
        }
      } catch (err) {
        badge.className = 'validation-badge fail';
        badge.innerText = "Simulation check error: " + err;
      }
    }

    function renderSessionView(session) {
      document.getElementById('guidedInitContainer').style.display = 'none';
      document.getElementById('guidedResolvedView').style.display = 'none';
      document.getElementById('guidedEscalatedView').style.display = 'none';
      document.getElementById('guidedSessionActive').style.display = 'block';

      document.getElementById('sessionDeviceBadge').innerText = 
        `${session.device_context?.device_model || 'Galaxy Device'} · ${session.device_context?.os_version || 'One UI 6'}`;
      document.getElementById('sessionDiagnosisTitle').innerText = session.diagnosis?.title || "Troubleshooting Session";
      document.getElementById('sessionConfidence').innerText = session.diagnosis?.confidence ? session.diagnosis.confidence.toFixed(2) : "0.95";

      currentStepData = session.current_step;
      if (!currentStepData) return;

      document.getElementById('stepProgressIndicator').innerText = 
        `STEP ${session.progress.current} / ${session.progress.total}`;

      const cat = currentStepData.category || 'auto';
      const badge = document.getElementById('stepCategoryBadge');
      badge.className = `badge badge-${cat}`;
      badge.innerText = cat.toUpperCase();

      document.getElementById('stepActionTitle').innerText = currentStepData.action_name;
      document.getElementById('stepInstructionText').innerText = currentStepData.instruction;
      document.getElementById('stepWhyText').innerText = currentStepData.why_this_step || "Restores normal Galaxy operations.";
      document.getElementById('stepExpectedText').innerText = currentStepData.expected_result || "Device operates as expected.";

      const dl = currentStepData.actionable_deeplink;
      const dlContainer = document.getElementById('deeplinkContainer');
      const dlBtn = document.getElementById('stepDeeplinkBtn');
      if (dl && dl.deeplink) {
        dlContainer.style.display = 'block';
        dlBtn.innerText = `🚀 Launch: ${dl.message || dl.description} (${dl.deeplink})`;
      } else {
        dlContainer.style.display = 'none';
      }

      document.getElementById('validationResultBadge').style.display = 'none';

      // Update Timeline
      renderTimeline(session);
    }

    function renderTimeline(session) {
      const timeline = document.getElementById('eventTimeline');
      let html = `
        <li class="timeline-item done">
          <div class="time-title">Query Received</div>
          <div class="time-desc">${session.query || 'Customer complaint registered'}</div>
        </li>
        <li class="timeline-item done">
          <div class="time-title">Diagnosis Generated</div>
          <div class="time-desc">${session.diagnosis?.title || 'Initial triage'}</div>
        </li>`;

      const completed = session.completed_steps || [];
      completed.forEach((s, idx) => {
        html += `
          <li class="timeline-item done">
            <div class="time-title">${s.action_name} (${s.result.toUpperCase()})</div>
            <div class="time-desc">${s.instruction.slice(0, 60)}...</div>
          </li>`;
      });

      if (session.status === 'ACTIVE' && currentStepData) {
        html += `
          <li class="timeline-item active">
            <div class="time-title">Current: ${currentStepData.action_name}</div>
            <div class="time-desc">${currentStepData.instruction.slice(0, 60)}...</div>
          </li>`;
      }

      timeline.innerHTML = html;
    }

    function alertDeeplink() {
      if (!currentStepData?.actionable_deeplink) return;
      const dl = currentStepData.actionable_deeplink;
      alert(`[SIMULATED DEEPLINK LAUNCH]\\nURI: ${dl.deeplink}\\nTarget: ${dl.message || dl.description}\\nAction: Opened native Samsung Settings screen via Bixby deep link.`);
    }

    async function submitFeedback(result) {
      if (!activeSession) return;
      try {
        const res = await fetch(`/v1/session/${activeSession.session_id}/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ result: result })
        });
        const data = await res.json();
        activeSession = data;

        if (data.resolved) {
          showResolvedView(data);
        } else if (data.escalated) {
          showEscalatedView(data);
        } else {
          renderSessionView(data);
        }
      } catch (err) {
        alert("Failed to submit feedback: " + err);
      }
    }

    function showResolvedView(session) {
      document.getElementById('guidedSessionActive').style.display = 'none';
      document.getElementById('guidedResolvedView').style.display = 'block';

      const sum = session.resolution_summary || {};
      document.getElementById('resolvedProblemText').innerText = sum.problem || session.query;
      document.getElementById('resolvedStepsCount').innerText = `${sum.steps_completed || 1} / ${sum.total_steps || 1}`;
      document.getElementById('resolvedTimeCount').innerText = `${sum.elapsed_seconds || 5}s`;

      const actionsList = document.getElementById('resolvedActionsList');
      const actions = sum.actions_taken || ["Completed diagnostic verifications."];
      actionsList.innerHTML = actions.map(a => `<li>${a}</li>`).join('');
    }

    function showEscalatedView(session) {
      document.getElementById('guidedSessionActive').style.display = 'none';
      document.getElementById('guidedEscalatedView').style.display = 'block';

      const sum = session.escalation_summary || {};
      document.getElementById('escalationReportJson').innerText = JSON.stringify(sum, null, 2);
    }

    function resetGuidedSession() {
      activeSession = null;
      currentStepData = null;
      document.getElementById('guidedSessionActive').style.display = 'none';
      document.getElementById('guidedResolvedView').style.display = 'none';
      document.getElementById('guidedEscalatedView').style.display = 'none';
      document.getElementById('guidedInitContainer').style.display = 'block';
    }

    // --- Fast-Path API Inspector Functions ---
    async function runInspectorTroubleshoot() {
      const query = document.getElementById('inspectorQueryInput').value.trim();
      if (!query) return;

      const btn = document.getElementById('btnSubmitInspector');
      btn.innerText = "Analyzing...";
      btn.disabled = true;

      try {
        const res = await fetch('/v1/troubleshoot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query })
        });
        const data = await res.json();
        renderInspectorResponse(data);
      } catch (err) {
        alert("Failed to query troubleshoot API: " + err);
      } finally {
        btn.innerText = "Diagnose & Generate Plan";
        btn.disabled = false;
      }
    }

    function renderInspectorResponse(data) {
      document.getElementById('inspectorMetaBar').style.display = 'flex';
      document.getElementById('inspectorLatency').innerText = `${data.meta.latency_ms} ms`;
      document.getElementById('inspectorCache').innerText = data.meta.cache_hit ? "CACHE HIT" : "COLD PATH";
      document.getElementById('inspectorCache').style.color = data.meta.cache_hit ? "#10b981" : "#f59e0b";

      document.getElementById('inspectorRawJson').innerText = JSON.stringify(data, null, 2);

      if (data.query_variations && data.query_variations.length > 0) {
        document.getElementById('inspectorVariationsContainer').style.display = 'block';
        document.getElementById('inspectorVariationsList').innerHTML = data.query_variations.map(v => `• ${v}`).join('<br>');
      }

      const contexts = data.response?.contexts || [];
      if (contexts.length === 0) {
        document.getElementById('inspectorPlanContent').innerHTML = `
          <div style="text-align: center; color: #f59e0b; padding: 3rem 1rem;">
            No immediate remediation found in local catalog (Fallback: no_match).
          </div>`;
        return;
      }

      const goal = contexts[0];
      document.getElementById('inspectorScore').innerText = goal.score ? goal.score.toFixed(2) : "0.95";

      let html = `
        <div style="border-bottom: 1px solid var(--border-color); padding-bottom: 1rem; margin-bottom: 1.25rem;">
          <div style="font-size: 1.05rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.35rem;">${goal.goal}</div>
          <span style="font-size: 0.8rem; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 0.2rem 0.6rem; border-radius: 4px; display: inline-block;">${goal.title}</span>
        </div>`;

      goal.actions.forEach(action => {
        const cat = action.category || 'auto';
        let stepsHtml = '';
        let deeplinkBtnHtml = '';

        if (action.stepGroups && action.stepGroups.length > 0) {
          const sg = action.stepGroups[0];
          stepsHtml = '<ul style="list-style: decimal; padding-left: 1.5rem; margin-bottom: 0.75rem; font-size: 0.9rem; color: #cbd5e1;">' + 
            sg.steps.map(s => `<li style="margin-bottom: 0.35rem;">${s}</li>`).join('') + '</ul>';
          
          if (sg.actionableDeeplink) {
            const dl = sg.actionableDeeplink;
            deeplinkBtnHtml = `
              <div style="margin-top: 0.75rem;">
                <a href="${dl.deeplink}" class="deeplink-btn" onclick="event.preventDefault(); alert('Triggering Deeplink:\\n${dl.deeplink}\\n\\nTarget: ${dl.message || dl.description}');">
                  🚀 Launch: ${dl.message || 'Settings'} (${dl.deeplink})
                </a>
              </div>`;
          }
        }

        html += `
          <div style="background: rgba(13, 19, 31, 0.7); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.15rem; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <span style="font-size: 1rem; font-weight: 600;">${action.actionName}</span>
              <span class="badge badge-${cat}">${cat}</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.75rem; font-style: italic;">${action.description}</div>
            ${stepsHtml}
            ${deeplinkBtnHtml}
          </div>`;
      });

      document.getElementById('inspectorPlanContent').innerHTML = html;
    }
  </script>
</body>
</html>
"""

# Samsung Smart Guided Troubleshooting Engine — System Workflow Walkthrough

**Document Version:** 1.0.0  
**Focus:** Live End-to-End Diagnostic Journeys for Multi-Intent Problem Scenarios

---

## 1. Primary Scenario Walkthrough: 2-Intent Complaint

### User Complaint:
> *"My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect."*

---

### Step 1: Query Ingestion
- The user inputs the complaint into the search bar on the diagnostic dashboard (or client application).
- Client issues `POST /v1/session/start` with payload:
  ```json
  {
    "query": "My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect",
    "device_model": "Galaxy S22",
    "os_version": "One UI 6.1 (Android 14)"
  }
  ```

---

### Step 2: Query Enrichment & Semantic Analysis
- `QueryEnricher` inspects the text and identifies two distinct technical concepts:
  1. `"Wi-Fi keeps disconnecting"` → Canonical key: `wifi network connectivity`
  2. `"Bluetooth earbuds won't connect"` → Canonical key: `bluetooth connection pairing`

---

### Step 3: Multi-Intent Detection & Decomposition
- `GeneralizedQueryPipeline` identifies the compound syntactic structure (conjunction *"and"* between two independent problem statements).
- It decomposes the query into two discrete intent records:
  - **Intent 1 (`intent_1`):** Subsystem: `NETWORK`, Issue: *"Wi-Fi disconnecting"*
  - **Intent 2 (`intent_2`):** Subsystem: `BLUETOOTH`, Issue: *"Bluetooth earbuds won't connect"*
- `SessionManager` initializes the session with:
  - `active_intent_id`: `"intent_1"`
  - Intent 1 Status: `ACTIVE`
  - Intent 2 Status: `PENDING`

---

### Step 4: Network Diagnosis Generation
- `DiagnosisValidator` evaluates Intent 1:
  - Domain: `NETWORK`
  - Confidence: `0.95`
  - Canonical Title: *"Wi-Fi Disconnecting"*
- Selects the canonical network plan from `DOMAIN_CANONICAL_PLANS["NETWORK"]`.

---

### Step 5: Trusted Troubleshooting Plan & Flow Construction
- `DiagnosticFlow` constructs a 4-step sequential troubleshooting path:
  - **Step 1:** Toggle Wi-Fi Off and On (Quick Refresh)
  - **Step 2:** Forget and Reconnect Wi-Fi Network
  - **Step 3:** Reset Network Settings (Remedial candidate)
  - **Step 4:** Restart Device in Safe Mode

---

### Step 6: Samsung Settings Deep Link Resolution
- `DeeplinkRetriever` matches Step 1 to the trusted deep link catalog:
  - Deep Link URI: `bixby://dummy_positive` (Masked protocol)
  - UI Breadcrumb: `Settings → Connections → Wi-Fi`
- Frontend renders the interactive **"OPEN SETTINGS →"** action button.

---

### Step 7: User Step Execution & Telemetry Simulation
- The user taps **"OPEN SETTINGS"** to navigate directly to the Wi-Fi settings page.
- The user toggles Wi-Fi off and back on.
- The verification panel queries `POST /v1/session/{id}/simulate-validation`, checking simulated device telemetry.

---

### Step 8: Validation Feedback & Progression
- The user taps the feedback button: **"Worked / Next Step"**.
- Client issues `POST /v1/session/{id}/feedback` with `{"result": "passed"}`.
- Step 1 completes; progress advances from 25% to 50%.
- Steps 2 through 4 are executed sequentially until the network problem is fixed.

---

### Step 9: Intent 1 Resolution
- Upon completion of the final network step (or explicit resolution):
  - Intent 1 status transitions to `RESOLVED`.
  - Intent 1 progress reaches 100%.

---

### Step 10: Automatic Transition to Intent 2 (Bluetooth)
- `SessionManager` detects that Intent 1 is `RESOLVED` while Intent 2 (`intent_2`) is `PENDING`.
- **Auto-Advance Trigger:** 
  - `session.active_intent_id` is updated to `"intent_2"`.
  - Intent 2 status transitions from `PENDING` to `ACTIVE`.
  - UI smoothly shifts focus to the Bluetooth troubleshooting track with a visual transition toast.

---

### Step 11: Bluetooth Diagnostic Flow Execution
- The dashboard updates with Intent 2's diagnostic flow:
  - Domain: `BLUETOOTH`
  - Action 1: Toggle Bluetooth and reconnect Galaxy Buds
  - Deeplink: `Settings → Connections → Bluetooth`
- User follows steps and submits positive feedback.

---

### Step 12: Final Global Resolution
- Intent 2 transitions to `RESOLVED`.
- `SessionManager` verifies that **all** constituent intents (`intent_1` and `intent_2`) are `RESOLVED`.
- The global session status transitions to `RESOLVED`.
- The dashboard renders the celebratory **Resolution Card**, displaying:
  - Total steps completed
  - All resolved problem categories
  - A clean **"Start New Diagnosis"** button for subsequent inquiries.

---

## 2. Advanced Multi-Intent Walkthrough: 3-Intent Complaint

### User Complaint:
> *"Wi-Fi disconnects, Bluetooth fails, and my camera crashes."*

### Orchestration Sequence:
1. **Compound Extraction:** Engine decomposes query into 3 distinct tracks:
   - `intent_1`: `NETWORK`
   - `intent_2`: `BLUETOOTH`
   - `intent_3`: `CAMERA`
2. **Interactive Tab Bar:** The UI displays three dedicated tabs with domain icons and live progress rings:
   - `[Wi-Fi (Active)]` `[Bluetooth (Pending)]` `[Camera (Pending)]`
3. **Manual Intent Switching:**
   - The user can click any tab (e.g. `[Camera]`) at any time.
   - `POST /v1/session/{id}/switch-intent` switches view to the Camera track (`Settings → Apps → Camera → Clear Cache`).
4. **Strict Feedback Isolation:**
   - Submitting step feedback on `CAMERA` increments only Camera progress.
   - Network and Bluetooth step counts remain untouched at 0.
5. **Sequential Auto-Advancement:**
   - As each intent resolves, the engine auto-advances to the next unfinished intent.
   - Once all 3 intents are completed, global status becomes `RESOLVED`.

---

## 3. Failure & Escalation Workflow

```
Step 1: Primary Action (Toggle Wi-Fi)
             │
      Feedback = "failed"
             │
             ▼
Step 2: Remedial Action (Reset Network Settings, is_remedial=True)
             │
      Feedback = "failed"
             │
             ▼
Step 3: Advanced Remedial (Safe Mode Inspection)
             │
      Feedback = "failed" (Repeated failures reach limit: 6)
             │
             ▼
[EXHAUSTION ESCALATION]
- Session status transitions to "ESCALATED"
- Escalation card renders on UI with:
  • Diagnostic Summary Report (completed vs failed steps)
  • One-tap Samsung Support hotline link
  • Nearest Authorized Samsung Service Center locator
```

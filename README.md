# Smart Guided Troubleshooting Engine
### Samsung PRISM GenAI Hackathon — Theme 02: Intelligent Device Troubleshooting & Settings Deep Linking

An intelligent, multimodal troubleshooting microservice and interactive guided diagnostics engine for Samsung Galaxy devices. The system transforms natural-language customer complaints and raw Samsung Issue Information System (SIIS) troubleshooting articles into machine-actionable, deeplink-enriched step-by-step diagnostic workflows.

---

## 1. Project Title
**Smart Guided Troubleshooting Engine**  
*Galaxy Diagnostic & Remediation Platform*

---

## 2. Problem & Purpose
When Galaxy device users experience technical malfunctions (e.g., Wi-Fi disconnections, blank screens, rapid battery drain, or pairing issues), they face significant support friction:
- Customer complaints are colloquial, vague, or describe multiple simultaneous symptoms without technical subsystem identifiers.
- Raw technical support documentation (SIIS articles) consists of dense, unstructured prose that users struggle to read and follow manually.
- Navigating deep settings hierarchies (often 4–6 taps inside Samsung One UI) causes high user drop-off.
- Static troubleshooting articles lack state awareness, automated device validation, or dynamic remedial alternatives when an initial step fails.

**Purpose:** The Smart Guided Troubleshooting Engine accepts a user's natural-language query along with raw SIIS technical content and deterministically generates a structured, verified, deeplink-enriched troubleshooting guide conforming strictly to the official Samsung Theme 02 schema.

---

## 3. Theme 02 Solution Overview
The engine implements an end-to-end processing pipeline:
1. **Query Enrichment**: Normalizes colloquial phrasing, extracts subsystem keywords, and identifies symptom anchors.
2. **Deterministic Diagnosis**: Classifies domain and symptom against verified canonical plans (`DOMAIN_CANONICAL_PLANS`), avoiding ungrounded AI hallucinations.
3. **Semantic Deep Link Retrieval**: Retrieves exact settings deep links from a trusted 578-entry Samsung Settings catalog using hybrid BM25 and dense TF-IDF retrieval.
4. **Guardrail Validation**: Enforces official constraints (2–3 word titles, 5–7 word action descriptions starting with `"It will"`, regex-compliant goals, score normalization, zero URL leaks).
5. **Interactive Guided Sessions**: Manages multi-turn state (`active`, `passed`, `failed`, `skipped`) with dynamic remedial branching and diagnostic escalation.
6. **Fast-Path Semantic Cache**: Pre-warmed vector cache delivering sub-5ms latency for repeat and paraphrased queries.
7. **Device & Telemetry Context**: Context-aware adaptation to device model, One UI version, connected wearables, and simulated hardware states.
8. **Multimodal & Error-Code Intelligence**: In-memory PaddleOCR extracts error dialog text and error codes (`BT-204`, `1001`, `ERR_WIFI_01`) from uploaded screenshots.
9. **Multi-Intent Orchestration**: Automatically decouples compound complaints into independent diagnostic tracks with seamless focus auto-advancement.
10. **Controlled Fallback**: Employs controlled fallback mechanisms (canonical keyword fallback and optional Gemini provider) with strict validation when confidence is low.

---

## 4. Architecture
The architecture comprises modular, decoupled components:

```
[ User Input: Natural Language Query / SIIS Response / Screenshot / Error Code ]
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Generalized Query Pipeline                            │
│  - QueryEnricher: Colloquial normalization & semantic expansion            │
│  - Multi-Intent Decomposition: Syntactic splitting into sub-intent tracks    │
│  - ImageAnalyzer: Adaptive PaddleOCR, noise filtration & box ranking        │
│  - ErrorCodeResolver: Canonical regex pattern matching & error catalog     │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FastPathCache (Pre-warmed)                               │
│  - Repeat query hash lookup (< 5ms)                                         │
│  - Cosine semantic similarity lookup for paraphrased queries (< 15ms)      │
└─────────────────────────────────────────────────────────────────────────────┘
                               │ (Cache miss)
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Canonical Diagnosis Validator                           │
│  - Domain & symptom matching via DOMAIN_CANONICAL_PLANS                     │
│  - Device Model & accessory awareness injection                             │
│  - StructuredExtractor: Extracts verified steps directly from raw SIIS text │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DeeplinkRetriever Engine                              │
│  - Dual BM25Okapi + TF-IDF cosine retrieval                                 │
│  - 578 verified masked Samsung Settings URIs (deeplinks.json)               │
│  - Positive fallback injection (bixby://dummy_positive)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Guardrails & Output Validation                       │
│  - URL Scrubber: 0 URL leaks enforced across all text fields                │
│  - Formatting Enforcement: 2–3 word title, 5–7 word description, Goal regex │
│  - Pydantic ContextDeeplinkResponse validation                              │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Interactive SessionManager                             │
│  - Multi-turn state machine (ACTIVE -> RESOLVED / ESCALATED)                │
│  - Remedial branching on step failure (is_remedial: true)                   │
│  - Intent tracking & focus switching for compound issues                    │
│  - ValidationSimulator: In-memory device hardware telemetry verification    │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
           [ REST API Response / React Client Dashboard ]
```

---

## 5. API Reference

The backend provides evaluation and interactive troubleshooting endpoints at `http://127.0.0.1:8000`:

| Method | Endpoint | Description |
|:---:|:---|:---|
| `GET` | `/health` | Health and readiness check. Returns `{"status": "ok"}` without authentication. |
| `POST` | `/v1/troubleshoot` | **Official Theme 02 evaluation endpoint.** Accepts query and SIIS response; returns official `ContextDeeplinkResponse`. |
| `POST` | `/v1/session/start` | Initiates an interactive guided troubleshooting session (supports multimodal screenshots and multi-intent queries). |
| `GET` | `/v1/session/{id}` | Inspects multi-turn session state, active intent, step progress, and completion history. |
| `POST` | `/v1/session/{id}/feedback` | Submits step feedback (`passed`, `failed`, `skipped`). Triggers remedial branching or advances to next step. |
| `POST` | `/v1/session/{id}/switch-intent` | Manually switches active intent focus in a multi-intent troubleshooting session. |
| `POST` | `/v1/session/{id}/simulate-validation` | Runs deterministic simulated device telemetry check against current step condition. |
| `GET` | `/v1/telemetry/state` | Returns the current simulated device hardware state (Wi-Fi, Bluetooth, Screen, Battery). |
| `POST` | `/v1/telemetry/state` | Updates simulated hardware state toggles to test automated step validation. |

---

## 6. Official Theme 02 Request Format

The `POST /v1/troubleshoot` endpoint accepts the exact organizer request structure:

```json
{
  "query": "My Samsung A115G tablet screen flashes and then goes completely black, how can I fix it?",
  "siis_response": {
    "title": "Screen flickers, fluctuates or goes blank",
    "content": "Follow the below steps to troubleshoot screen flicker:\n1. Restart the device: Press and hold the Power and Volume Down keys for more than 7 seconds to restart it.\n2. Check for software updates: Go to Settings > Software update > Download and install.\n3. Test in Safe Mode: Power off, then press and hold Power and Volume Down until Safe Mode appears."
  }
}
```

Optional metadata fields (`device_model`, `os_version`) are supported for enhanced context but are not required.

---

## 7. Official Response Format

The response strictly adheres to the official `ContextDeeplinkResponse` schema:

```json
{
  "contexts": [
    {
      "goal": "Follow these steps to perform this Screen flickers when Troubleshooting",
      "title": "Screen flickers when",
      "score": 0.94,
      "actions": [
        {
          "actionName": "Restart device",
          "description": "It will restart your mobile device now",
          "category": "auto",
          "stepGroups": [
            {
              "steps": [
                "Restart the device: Press and hold the Power and Volume Down keys for more than 7 seconds to restart it."
              ],
              "actionableDeeplink": {
                "deeplink": "bixby://dummy_positive",
                "description": "It will restart your mobile device now",
                "type": "ACTIONABLE"
              },
              "validationDeeplink": {
                "deeplink": "bixby://dummy_positive",
                "description": "It will restart your mobile device now",
                "type": "VALIDATION"
              }
            }
          ]
        },
        {
          "actionName": "Software update",
          "description": "It will check for latest system updates",
          "category": "auto",
          "stepGroups": [
            {
              "steps": [
                "Check for software updates: Go to Settings > Software update > Download and install."
              ],
              "actionableDeeplink": {
                "deeplink": "bixby://sec_settings_mock/software_update",
                "description": "It will check for latest system updates",
                "type": "ACTIONABLE"
              },
              "validationDeeplink": {
                "deeplink": "bixby://dummy_positive",
                "description": "It will check for latest system updates",
                "type": "VALIDATION"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### Key Schema Elements:
- **`contexts`**: List of `Goal` items matching query problems.
- **`Goal`**: Contains `goal` (regex-validated string), `title` (2–3 words), `score` (0.0–1.0), and `actions`.
- **`Action`**: Contains `actionName`, `description` (5–7 words starting with `"It will"`), `category` (`auto` or `manual`), and `stepGroups`.
- **`StepGroup`**: Contains `steps` (derived directly from SIIS text), `actionableDeeplink`, and `validationDeeplink`.
- **`Deeplink` / `ValidationDeepLink`**: Masked `bixby://` URI, description, and type.

---

## 8. Official Contract Compliance

The engine has been verified against the official student kit (`participant-kit/Theme02_Input_Kit/student_kit/`):

| Gate / Requirement | Official Criteria | Verified Status |
|:---|:---|:---:|
| **G2: Health Check** | `GET /health` returns `200 OK` with `{"status": "ok"}` | **PASS** |
| **G3: Coverage Rate** | $\ge 95\%$ test queries covered | **PASS (100.0% — 20/20 cases)** |
| **G4: Schema Validity** | $\ge 90\%$ valid `ContextDeeplinkResponse` | **PASS (100.0% — 20/20 cases)** |
| **G5: URL Leaks** | Exactly 0 normal web URLs (`http://`, `https://`, `www.`, etc.) | **PASS (0 leaks detected)** |
| **A1: Formatting Rules** | Title (2–3 words), description (5–7 words starting with `"It will"`), goal regex | **PASS** |
| **A2: Deeplink Integrity** | 100% actionable deeplinks match 578 catalog or `bixby://dummy_positive` | **PASS** |
| **A3: Cache & Latency** | Repeat query P95 $\le 300\text{ ms}$, hit rate $\ge 90\%$ | **PASS (P95 = 4.75 ms, 100% hit rate)** |
| **A4: Generalization** | Evaluated on novel unseen SIIS scenarios | **PASS (5/5 valid, 0 URL leaks)** |
| **A5: Query Variations** | 8–10 unique, intent-preserving variations per query in `results.jsonl` | **PASS (20/20 canonical cases)** |

---

## 9. Performance Benchmarks

*All metrics are verified from live execution against the running system:*

### Fast Text & Cache Performance
| Operation | Measured Latency | Official Target |
|:---|:---:|:---:|
| **Repeat Query Cache (P50)** | **4.13 ms** | — |
| **Repeat Query Cache (P95)** | **4.75 ms** | $\le 300\text{ ms}$ |
| **Repeat Cache Hit Rate** | **100.0%** | $\ge 90\%$ |
| **Semantic Cache (Paraphrases P50)** | **10.20 ms** | — |
| **Semantic Cache (Paraphrases P95)** | **14.56 ms** | — |
| **Semantic Cache Hit Rate** | **100.0%** | $\ge 80\%$ |
| **Novel Text Query (Uncached P50)** | **14.03 ms** | $\le 50\text{ ms}$ |
| **Multi-Intent Text Query (P50)** | **43.21 ms** | $\le 120\text{ ms}$ |
| **Cold-Start Text Request Latency** | **47.93 ms** (0.048 s) | $\le 8.00\text{ s}$ |

### Multimodal Image / OCR Latency
> **Note on Image/OCR Latency:** OCR execution runs locally on CPU via PaddleOCR without dedicated hardware accelerators.
- **Startup Pre-Warming:** PaddleOCR is pre-warmed during server initialization in **~492 ms**, removing model compilation overhead from the first user request.
- **First Cold Image Request:** **~7.0 seconds** (includes initial image memory allocation and text detection pass).
- **Subsequent Image OCR Requests:** **~3.98–5.04 seconds** (depending on screenshot text density).
- *OCR performance does not affect the text troubleshooting API, which consistently operates under 50 ms.*

---

## 10. Multimodal & Multi-Intent Capabilities

### Multimodal Screenshot Analysis
- **Noise Stripping**: Filters status bar (`y < 5%`) and navigation bar (`y > 92%`).
- **Geometric Saliency Ranking**: Ranks detected bounding boxes to prioritize dialog boxes and error banners.
- **Adaptive OCR Batching**: Recognizes top-priority boxes first with early stopping upon identifying diagnostic keywords or error codes.
- **Error Code Extraction**: Regex identifies patterns like `BT-204`, `ERR_WIFI_01`, `1001`, `0x80004005`.

### Multi-Intent Troubleshooting
- **Decomposition**: Syntactically splits compound complaints (e.g., *"My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect"*) into separate domain intents (`NETWORK` and `BLUETOOTH`).
- **Independent State Tracking**: Each sub-intent maintains isolated step indices, remedial branches, and completion statuses.
- **Auto-Advancement**: Resolving Intent 1 automatically transitions session focus to Intent 2.
- **Terminal Aggregation**: Session marks complete only when all sub-intents are successfully resolved.

---

## 11. Frontend Client Interface

The React 18 / Vite client located in `frontend/` serves as the interactive demonstration interface. The REST API is the core evaluation deliverable.

### Key UI Features:
- **Responsive Quick Diagnostics Grid**: Balanced 3-column desktop layout (2 rows $\times$ 3 cards), 2-column tablet layout, and 1-column mobile layout.
- **Multi-Intent Tab Bar**: Visual badge indicators for active, pending, and resolved issues with one-click intent switching.
- **Interactive Step Execution**: Shows step instructions, One UI navigation breadcrumbs, and simulated "Launch Settings" button.
- **Remedial Branch Indicator**: Distinct visual styling for remedial steps when a user reports a step failure.
- **Telemetry Verification Panel**: Simulated hardware status toggles (Wi-Fi, Bluetooth, Screen, Battery) to demonstrate real-time step verification.

---

## 12. Project Structure

```text
participant-kit-all-themes/
├── README.md                              # Final project README
├── PHASE_8_OFFICIAL_THEME2_CONTRACT_VERIFICATION.md  # Official verification report
├── docs/                                  # Architectural docs and specifications
├── frontend/                              # Interactive React / Vite demonstration UI
│   ├── src/
│   │   ├── components/                    # UI component library
│   │   ├── hooks/                         # Session lifecycle hooks
│   │   ├── services/api.ts                # REST API client (127.0.0.1:8000)
│   │   └── index.css                      # One UI dark/glassmorphic design system
│   ├── package.json
│   └── vite.config.ts
├── participant-kit/                       # Official organizer kits
│   └── Theme02_Input_Kit/student_kit/     # Official schema, deeplinks, and starter data
└── theme02_troubleshooting_engine/        # Core FastAPI backend microservice
    ├── api/
    │   └── app.py                         # REST microservice routes
    ├── core/
    │   ├── cache_manager.py               # Fast-path semantic cache
    │   ├── deeplink_retriever.py          # BM25 + TF-IDF retriever
    │   ├── diagnosis_validator.py         # Canonical domain & safety validation
    │   ├── diagnostic_flow.py             # Diagnostic state machine & remedial branching
    │   ├── error_code_resolver.py         # Error code catalog & regex extraction
    │   ├── extractor.py                   # Structured SIIS plan extractor
    │   ├── guardrails.py                  # URL scrubbing & output format guardrails
    │   ├── image_analyzer.py              # Adaptive PaddleOCR pipeline
    │   ├── query_enricher.py              # Natural language normalization
    │   ├── query_pipeline.py              # Multi-intent & multimodal orchestration
    │   ├── schema.py                      # Pydantic ContextDeeplinkResponse models
    │   ├── session_manager.py             # Stateful multi-intent session store
    │   └── validation_simulator.py        # In-memory device telemetry simulator
    ├── data/
    │   ├── deeplinks.json                 # 578 verified Samsung Settings deep links
    │   ├── error_codes.json               # Canonical error code catalog
    │   ├── siis_responses.json            # Official starter SIIS scenarios
    │   └── cache_store.json               # Pre-warmed vector cache store
    ├── tests/                             # Pytest unit and integration test suite
    ├── Dockerfile                         # Container deployment specification
    ├── requirements.txt                   # Locked Python dependencies
    ├── results.jsonl                      # Pre-generated Theme 02 offline submission file
    └── run_server.py                      # Server entry point with PaddleOCR pre-warming
```

---

## 13. Local Setup Instructions (Windows PowerShell)

### Prerequisites
- **Python 3.10+** (Tested on Python 3.12)
- **Node.js 18+** and **npm**

### Step 1: Clone & Prepare Python Environment
```powershell
# Navigate to workspace root
cd C:\Users\anian\Downloads\participant-kit-all-themes

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r theme02_troubleshooting_engine\requirements.txt
```

### Step 2: Start the Backend Server
```powershell
# Start FastAPI backend (port 8000)
python theme02_troubleshooting_engine\run_server.py
```
*Expected log output:*
```text
Starting Smart Guided Troubleshooting Engine on port 8000...
[Engine] Initializing Deeplink Retriever...
[Engine] Initializing Fast-Path Semantic Cache...
[Engine] PaddleOCR pre-warmed successfully at startup in 492.15 ms.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 3: Verify Backend Health
```powershell
# In a new terminal window:
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
# Output: status: ok
```

### Step 4: Install & Start Frontend Demo Client
```powershell
cd frontend
npm install
npm run dev
```
*Access the interactive dashboard in your browser at:* **`http://localhost:5173`**

---

## 14. Docker Deployment

The project provides a self-contained, multi-stage Docker container specification in `theme02_troubleshooting_engine/Dockerfile`:

### Build Container Image
```bash
docker build -f theme02_troubleshooting_engine/Dockerfile -t samsung-troubleshoot-engine ./theme02_troubleshooting_engine
```

### Run Container
```bash
docker run -d -p 8000:8000 --name samsung-engine samsung-troubleshoot-engine
```

### Verify Container Health
```bash
curl http://localhost:8000/health
# Returns: {"status": "ok"}
```

---

## 15. Testing & Validation

All test suites pass cleanly with zero errors:

### 1. Backend Pytest Suite (119 Tests)
```powershell
python -m pytest theme02_troubleshooting_engine/tests
```
- **Result**: **119 passed, 0 failed** (8.00 s)

### 2. Security & Edge-Case Suite (49 Tests)
```powershell
python scratch/test_phase8_step4_security.py
```
- **Result**: **49 passed, 0 failed** (28.32 s)
- Tests payload size limits, prompt injections, ReDoS attacks, prototype pollution, unicode sanitization, and corrupt image recovery.

### 3. Session State Lifecycle Suite (10 Tests)
```powershell
python scratch/verify_session_state_complete.py
```
- **Result**: **10 passed, 0 failed** (4.88 s)
- Tests multi-turn step completion, remedial branching, intent switching, and diagnostic escalation.

### 4. Frontend Production Build
```powershell
cd frontend
npm run build
```
- **Result**: **49 modules transformed, 0 TypeScript errors, built in 1.02 s**.

---

## 16. Offline Submission File (`results.jsonl`)

The repository includes the required pre-generated evaluation file:
- **Location**: `theme02_troubleshooting_engine/results.jsonl`
- **Format**: JSON Lines, exactly one valid JSON object per line.
- **Content**: 20 lines corresponding to the 20 official canonical SIIS cases.
- **Structure per line**:
  ```json
  {
    "query": "<canonical_user_query>",
    "query_variations": [
      "<variation_1>",
      "<variation_2>",
      "...",
      "<variation_10>"
    ],
    "response": {
      "contexts": [...]
    }
  }
  ```
- **Integrity**: Each case contains 8–10 diverse, intent-preserving query variations and a fully validated `ContextDeeplinkResponse` with 0 URL leaks.

---

## 17. Live Demonstration Guide

To demonstrate the engine's core capabilities:

1. **Launch Stack**: Start backend (`run_server.py`) and frontend (`npm run dev`).
2. **Single-Intent Troubleshooting**:
   - In the frontend Quick Diagnostics grid, click **Wi-Fi Connectivity** or **Black Screen / Blank**.
   - Observe instant (< 15 ms) plan generation with One UI breadcrumbs and settings deep link (`bixby://...`).
3. **Step Feedback & Remedial Branching**:
   - Click **"No, Need More Help"** on Step 1.
   - Observe dynamic remedial branching (`is_remedial: true`), introducing alternative diagnostic steps.
4. **Simulated Telemetry Verification**:
   - Use the **Verification Panel** to test device state validation (e.g., verifying Wi-Fi adapter toggle).
5. **Multi-Intent Troubleshooting**:
   - Click the **Dual Issue (Wi-Fi & Buds)** card.
   - Observe automatic decomposition into two independent tracks (`NETWORK` and `BLUETOOTH`).
   - Switch between tracks using the Intent Tab Bar or observe auto-advancement upon resolving Track 1.
6. **Multimodal / Error-Code Input**:
   - Upload a screenshot with an error dialog or type `"Error BT-204"`.
   - Observe automatic error code extraction and direct resolution to canonical Bluetooth pairing steps.

---

## 18. Security & Guardrails

- **Zero URL Leaks**: Programmatic regex filters enforce zero exposure of external web URLs (`http://`, `https://`, `.com`, `.org`).
- **Deeplink Whitelist**: Actionable deep links are restricted strictly to the verified 578-entry catalog or `bixby://dummy_positive`.
- **Server-Side Key Isolation**: No third-party API keys or credentials exist in the client bundle.
- **Input Sanitization & Payload Caps**: Queries capped at 2,000 characters; image payloads capped at 16 MB.
- **Prompt Injection Defense**: Evaluator prompts and user inputs cannot override canonical plans due to strict schema typing and deterministic validator routing.
- **Corrupt Image Fault Tolerance**: Invalid or malformed image uploads safely degrade to text-only processing without raising uncaught exceptions.

---

## 19. Submission Checklist

- [x] Complete backend microservice source code (`theme02_troubleshooting_engine/`)
- [x] Complete frontend demonstration client source code (`frontend/`)
- [x] Comprehensive root documentation (`README.md`)
- [x] Official contract verification report (`PHASE_8_OFFICIAL_THEME2_CONTRACT_VERIFICATION.md`)
- [x] Container deployment configuration (`theme02_troubleshooting_engine/Dockerfile`)
- [x] Pre-computed offline evaluation file (`theme02_troubleshooting_engine/results.jsonl`)
- [ ] Presentation Slide Deck (PPT / PDF)
- [ ] Demonstration Video ($\le 5\text{ minutes}$)
- [ ] Final Git Submission Tag: `PRISM_GENAI_HACKATHON_Y2026`

---

## 20. Final Status

The implementation has successfully passed the official Samsung Theme 02 contract verification and regression audit:
- **100.0% Coverage** on canonical test queries (Gate G3).
- **100.0% Schema Validity** conforming to `ContextDeeplinkResponse` (Gate G4).
- **0 URL Leaks** across all generated outputs (Gate G5).
- **119/119 Backend Tests Passing** with zero regressions.
- **49/49 Security & Edge-Case Tests Passing**.

```text
==========================================================
STATUS: OFFICIAL CONTRACT READY
==========================================================
```

# Samsung Smart Guided Troubleshooting Engine
### Samsung Hackathon — Theme 02: Intelligent Device Troubleshooting & Settings Deep Linking

Transforming colloquial, frustrating Galaxy device complaints into machine-actionable, validated diagnostic workflows with one-tap Samsung Settings deep links in under 5 milliseconds.

---

## 1. Project Title
**Samsung Smart Guided Troubleshooting Engine** (Galaxy Diagnostic & Remediation Platform)

## 2. Samsung Theme 02 Context
Theme 02 challenges participants to solve customer technical support friction on mobile devices. Traditional support relies on static, text-heavy FAQ articles or rigid chatbots that expect technical terminology and cannot interact with device settings. 

This engine bridges user complaints directly to actionable One UI resolution paths, providing:
- Zero-hallucination troubleshooting steps grounded in canonical domain knowledge.
- Masked Android/Bixby settings deep links (`bixby://...`) mapped to human-readable UI breadcrumbs (`Settings → Connections → Wi-Fi`).
- Multi-intent decomposition, multimodal screenshot error intelligence, and interactive step-by-step verification.

---

## 3. Problem Statement
When Galaxy users experience device malfunctions (e.g., *"My Wi-Fi keeps disconnecting and my earbuds won't pair"*), they face severe diagnostic friction:
1. **Colloquial & Vague Phrasing:** Users describe symptoms informally without knowing underlying subsystem causes.
2. **Compound Multi-Issue Complaints:** Users often report multiple simultaneous problems that traditional single-intent engines fail to decouple.
3. **Complex Manual Navigation:** Following multi-step FAQ guides requires navigating complex Settings menus (4–6 taps deep).
4. **No Verification or Remedial Branching:** Users abandon guides when step 1 fails because static guides offer no dynamic alternatives or escalation paths.

---

## 4. The Solution
An intelligent, high-performance troubleshooting microservice coupled with a reactive Galaxy-styled diagnostic dashboard:
- **Instant Intent Understanding:** Decomposes complex multi-problem queries into independent diagnostic intents.
- **Multimodal Error Intelligence:** Extracts technical evidence (error codes, dialog text) from device screenshots in memory via adaptive PaddleOCR.
- **One-Tap Actionable Settings:** Resolves exact settings deep links from a trusted 578-entry catalog.
- **Interactive Multi-Turn Flow:** Guides the user step-by-step with automated remedial branching and diagnostic escalation if safe steps are exhausted.
- **Sub-5ms Semantic Cache:** Fast-path cache delivers sub-5ms responses for common issues.

---

## 5. Key Capabilities

1. **Multi-Intent Orchestration:** Automatically identifies and decouples multiple simultaneous issues (e.g., Network + Bluetooth + Camera) into separate diagnostic tracks with isolated progress and seamless auto-advancement.
2. **Multimodal OCR & Error-Code Intelligence:** Accepts device screenshots, crops out status/navigation noise, scores text boxes by technical relevance, and extracts error codes (`1001`, `BT-204`, etc.) within ~4 seconds on CPU.
3. **Deterministic Canonical Grounding:** Strict rule prevents LLMs from inventing troubleshooting steps or hallucinating arbitrary settings targets. All steps originate from verified canonical plans.
4. **Adaptive Remedial Branching:** User feedback (`passed`, `failed`, `skipped`) triggers dynamic tree execution; failed primary steps automatically switch to safe remedial alternatives.
5. **Simulated Telemetry & Validation:** Emulates device sensor and connectivity checks (Wi-Fi, Bluetooth, Screen, Battery) to verify step resolution before advancing.
6. **Zero Web URL Leakage:** Strict guardrails scrub all raw HTTP/HTTPS URLs from diagnostic outputs.

---

## 6. High-Level Architecture

```
User Complaint (Text / Image / Error Code)
                │
                ▼
┌────────────────────────────────────────────────────────┐
│               Generalized Query Pipeline               │
│  - Text Normalization & Canonical Key Enrichment      │
│  - Multi-Intent Decomposition                          │
│  - Multimodal Evidence Fusion (PaddleOCR + Heuristics) │
│  - Error-Code Extraction & Mapping                     │
└────────────────────────────────────────────────────────┘
                │
         [Confidence Check]
        ┌───────┴───────┐
  High Confidence   Ambiguous/Low
        │               │
        │       [Clarification Needed]
        ▼
┌────────────────────────────────────────────────────────┐
│            Canonical Diagnosis Validator               │
│  - DOMAIN_CANONICAL_PLANS Matching                     │
│  - Device Model & Accessory Context Injection          │
└────────────────────────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────────────────────┐
│               Deeplink Retriever Engine                │
│  - Dual BM25 + Dense Cosine Retrieval                  │
│  - 578 Verified Samsung Settings Entries               │
└────────────────────────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────────────────────┐
│             Interactive Session Manager                │
│  - Step-by-Step Diagnostic Flow State Machine          │
│  - Multi-Intent Tracking & Auto-Advance                │
│  - Remedial Branching on Failure                       │
│  - Diagnostic Exhaustion Escalation                    │
└────────────────────────────────────────────────────────┘
                │
                ▼
      Client UI / REST Response
```

---

## 7. Technology Stack

### Backend
- **Language & Runtime:** Python 3.12 (compatible with 3.10+)
- **API Framework:** FastAPI, Uvicorn (ASGI)
- **Data Validation:** Pydantic v2 (Strict typing & Theme 02 schema adherence)
- **Search & Retrieval:** `rank-bm25` (BM25Okapi), `scikit-learn` (TF-IDF vectorizer)
- **Computer Vision & OCR:** PaddleOCR, PaddlePaddle (CPU-optimized, pre-warmed), Pillow (PIL)
- **Testing & Benchmarking:** Pytest, AnyIO, Requests, Urllib

### Frontend
- **Framework:** React 18, TypeScript
- **Build Tool:** Vite 5 (Fast HMR & optimized production chunking)
- **Styling:** Custom Vanilla CSS (Samsung One UI design language, dark/light contrast, responsive glassmorphism)
- **State Management:** Custom React hooks (`useTroubleshootingSession`)

---

## 8. Backend Structure

```text
theme02_troubleshooting_engine/
├── api/
│   └── app.py                     # FastAPI REST microservice & endpoint router
├── core/
│   ├── cache_manager.py           # Fast-path semantic cache (< 4ms latency)
│   ├── deeplink_retriever.py      # Dual BM25 + TF-IDF retriever over deeplinks.json
│   ├── diagnosis_validator.py     # Deterministic domain classification & safety checks
│   ├── diagnostic_flow.py         # Step-by-step state machine with remedial branching
│   ├── error_code_resolver.py     # Regex code extraction & canonical error catalog
│   ├── extractor.py               # Structured plan extractor for SIIS articles
│   ├── guardrails.py              # URL scrubbing, benefit phrase syntax, category rules
│   ├── image_analyzer.py          # PaddleOCR engine, adaptive box scoring & evidence fusion
│   ├── query_enricher.py          # Colloquial technical normalization & paraphrase builder
│   ├── query_pipeline.py          # Unified multimodal & multi-intent orchestration pipeline
│   ├── schema.py                  # Pydantic contracts conforming to Theme 02 specs
│   ├── session_manager.py         # Multi-turn session state store with intent isolation
│   └── validation_simulator.py    # Deterministic simulated device telemetry validator
├── data/
│   ├── deeplinks.json             # 578 verified Samsung Settings deep links
│   ├── error_codes.json           # Catalog of recognized Samsung diagnostic codes
│   ├── siis_responses.json        # Starter knowledge scenarios
│   └── cache_store.json           # Pre-warmed fast-path semantic index
├── tests/                         # 12 test suites (119 unit/integration tests)
├── Dockerfile                     # Multi-stage container deployment specification
├── requirements.txt               # Locked production Python dependencies
└── run_server.py                  # Standalone server launcher with OCR pre-warming
```

---

## 9. Frontend Structure

```text
frontend/
├── src/
│   ├── components/
│   │   ├── Header/                # Samsung Galaxy branding & global session reset
│   │   ├── ProblemInput/          # Multimodal input (text, screenshot upload, error code)
│   │   ├── IntentTabBar/          # Interactive multi-intent track switcher
│   │   ├── DiagnosisCard/         # Technical problem summary & confidence breakdown
│   │   ├── DeviceContextCard/     # Detected phone model, OS, and simulated telemetry badge
│   │   ├── TroubleshootingStep/   # Current action, expected result & Launch Settings button
│   │   ├── ProgressTimeline/      # Step completion stepper & progress percentage
│   │   ├── VerificationPanel/     # Real-time telemetry check simulator
│   │   ├── ResolutionCard/        # Issue resolved celebration & summary of completed actions
│   │   ├── EscalationCard/        # Service center recommendation when steps exhausted
│   │   └── QuickScenario/         # 1-click test scenarios for demo presentation
│   ├── hooks/
│   │   └── useTroubleshootingSession.ts # Session lifecycle, feedback & polling logic
│   ├── services/
│   │   └── api.ts                 # REST client targeting backend (127.0.0.1:8000 default)
│   └── types/
│       └── troubleshooting.ts     # TypeScript interface mirrors of backend Pydantic models
├── package.json                   # React + Vite scripts and dependencies
└── vite.config.ts                 # Dev server and build configurations
```

---

## 10. API Endpoints

| Method | Endpoint | Description |
|:---:|:---|:---|
| `GET` | `/health` | Liveness & readiness probe (returns `200 OK` when ready) |
| `POST` | `/v1/troubleshoot` | Official Theme 02 one-shot troubleshooting plan generator |
| `POST` | `/v1/session/start` | Initiates an interactive multi-intent diagnostic session |
| `GET` | `/v1/session/{id}` | Inspects full multi-turn state, active intent, and progress |
| `POST` | `/v1/session/{id}/feedback` | Submits step outcome (`passed`, `failed`, `skipped`) and branches |
| `POST` | `/v1/session/{id}/switch-intent` | Manually switches active intent focus without losing state |
| `POST` | `/v1/session/{id}/simulate-validation` | Runs deterministic simulated device telemetry check |
| `GET` | `/v1/telemetry/state` | Returns current simulated device hardware state |
| `POST` | `/v1/telemetry/state` | Dynamically updates simulated device state toggles |

*See [docs/API_DOCUMENTATION.md](file:///c:/Users/anian/Downloads/participant-kit-all-themes/docs/API_DOCUMENTATION.md) for complete request/response schemas and examples.*

---

## 11. Multimodal Processing Pipeline

The multimodal module combines local pixel-level text detection with technical box prioritization:
1. **Resolution Normalization:** Images normalized to optimal diagnostic resolution (640×960).
2. **Noise Filtration:** Automatically strips peripheral noise (status bar `y < 5%`, navigation bar `y > 92%`).
3. **Adaptive Box Prioritization:** Detected bounding boxes are scored by geometric saliency (aspect ratio, central focus, dialog prominence).
4. **Selective Recognition:** PaddleOCR recognizes top high-value boxes first; early stopping halts recognition as soon as error codes or critical keywords are identified.
5. **Startup Pre-Warming:** PaddleOCR is initialized during application startup in ~492 ms, shifting ~1.1s of cold startup latency away from user requests.

---

## 12. Error-Code Intelligence

- **Regex Engine:** Detects alpha-numeric and hyphenated error patterns (`BT-204`, `1001`, `ERR_WIFI_01`, `0x80004005`, `BAT-301`, `CAM-502`).
- **Canonical Normalization:** Normalizes case and spacing.
- **Deterministic Resolution:** Matches recognized codes directly to verified canonical troubleshooting plans.
- **Safety Rule:** Unknown error codes never trigger fabricated plans; the engine falls back safely to text-based symptom classification.

---

## 13. Multi-Intent Troubleshooting Orchestration

When a user submits a compound complaint (e.g., *"Wi-Fi disconnects and Bluetooth fails"*):
1. **Decomposition:** Splits the input text into discrete sub-intents based on syntactic conjuncts and subsystem anchors.
2. **Intent Session States:** Creates independent `IntentSessionState` tracks (`intent_1`, `intent_2`, etc.).
3. **Feedback Isolation:** Submitting feedback on Intent 1 advances Intent 1's step index without affecting Intent 2.
4. **Auto-Advancement:** When Intent 1 reaches `RESOLVED`, the session manager automatically transitions active focus to the next pending intent.
5. **Terminal Resolution:** The session transitions to `RESOLVED` only when all constituent intents are resolved.

---

## 14. Session Lifecycle & Remedial Branching

```
                  ┌─────────────────┐
                  │ POST /start     │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
            ┌────►│     ACTIVE      │◄────┐
            │     └────────┬────────┘     │
            │              │              │
       Step Passed   Step Failed    Step Skipped
            │              │              │
            │              ▼              │
            │     ┌─────────────────┐     │
            │     │ Remedial Step   │─────┘
            │     │ (is_remedial)   │
            │     └────────┬────────┘
            │              │ 6 Failures
            ▼              ▼
    ┌───────────────┐ ┌───────────────┐
    │   RESOLVED    │ │   ESCALATED   │
    │  (Completed)  │ │ (Call Support)│
    └───────────────┘ └───────────────┘
```

---

## 15. Security & Guardrails

- **Zero Raw URLs:** No `http://` or `https://` URLs are emitted in diagnostic outputs; all deep links are internal device intents.
- **Deeplink Verification:** Every generated deeplink is validated against `deeplinks.json`. Fabricated schemes are strictly rejected.
- **Prompt Injection Immunity:** Instruction overrides (`"ignore instructions"`, `"execute rm -rf"`) are neutralized by strict schema validation and deterministic canonical routing.
- **Memory-Safe Image Processing:** Malformed Base64, corrupt PNG headers, and 16MB oversized payloads are caught safely and fall back to text diagnosis without crashing.
- **Credential Protection:** Frontend production bundle contains zero API keys or secrets.

---

## 16. Performance Metrics

*Measured live against the running backend:*

| Metric | Measured Value | Target SLA |
|:---|:---:|:---:|
| **Fast-Path Cache (P50)** | **3.93 ms** | < 15 ms |
| **Normal Text Query (P50)** | **7.89 ms** | < 50 ms |
| **Cold Path Query (P50)** | **19.56 ms** | < 80 ms |
| **Multi-Intent Query (P50)** | **43.21 ms** | < 120 ms |
| **Error Code Query (P50)** | **4.54 ms** | < 25 ms |
| **Session Feedback Step (P50)** | **2.47 ms** | < 10 ms |
| **First Image Request (Post-Warm)** | **4,011 ms** | < 8,000 ms |
| **Subsequent Image OCR (P50)** | **3,986 ms** | < 6,000 ms |

---

## 17. Local Setup Instructions

### Prerequisites
- **Python 3.10+** (Tested on Python 3.12.10)
- **Node.js 18+** and **npm**

### Step 1: Install Backend Dependencies
```bash
cd participant-kit-all-themes
pip install -r theme02_troubleshooting_engine/requirements.txt
```

### Step 2: Install Frontend Dependencies
```bash
cd frontend
npm install
```

---

## 18. Environment Variables

| Variable | Scope | Default | Description |
|:---|:---:|:---:|:---|
| `PORT` | Backend | `8000` | Port for the FastAPI server |
| `GEMINI_API_KEY` | Backend | `""` (Optional) | API key for uncertain natural language fallback |
| `VITE_API_BASE_URL` | Frontend | `http://127.0.0.1:8000` | Target URL for backend API requests |

---

## 19. Running the Backend Server

```bash
# From workspace root:
python theme02_troubleshooting_engine/run_server.py
```
*Output will confirm:*
```text
Starting Smart Guided Troubleshooting Engine on port 8000...
[Engine] Initializing Deeplink Retriever...
[Engine] Initializing Fast-Path Semantic Cache...
[Engine] PaddleOCR pre-warmed successfully at startup in 492.15 ms.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Verify backend health:
```bash
curl http://127.0.0.1:8000/health
# Returns: {"status": "ok"}
```

---

## 20. Running the Frontend Dashboard

```bash
# In a separate terminal:
cd frontend
npm run dev
```
*Access the dashboard in your browser at:* **`http://localhost:5173`**

---

## 21. Testing

### Run Complete Backend Test Suite (119 Tests)
```bash
python -m pytest theme02_troubleshooting_engine/tests
```

### Run Security & Edge-Case Audit (49 Tests)
```bash
python scratch/test_phase8_step4_security.py
```

### Run Frontend Production Build Validation
```bash
cd frontend
npm run build
```

---

## 22. Deployment Readiness

> [!IMPORTANT]
> The current setup is configured for **local hackathon demonstration**. The table below details the separation between local demo configuration and production deployment requirements:

| Area | Local Demo Configuration | Production Cloud Deployment |
|:---|:---|:---|
| **API Host** | `http://127.0.0.1:8000` (eliminates Windows DNS latency) | Injected via `VITE_API_BASE_URL` (e.g. `https://api.troubleshoot.samsung.com`) |
| **CORS** | Permissive `["*"]` | Locked to authorized company domains |
| **Process Manager** | Uvicorn single process (`run_server.py`) | Gunicorn multi-worker container (`-w 2 -k uvicorn.workers.UvicornWorker`) |
| **Frontend Serving** | Vite dev server (`npm run dev`) | Static hosting via Nginx, S3 + CloudFront, or CDN edge |
| **Containerization** | Local Python execution | Multi-stage Docker container (`Dockerfile` provided) with `libgl1` Linux libraries |
| **Device Telemetry** | In-memory deterministic simulator (`ValidationSimulator`) | Real Samsung Knox / One UI system service intent broadcasts |

---

## 23. Known Limitations

1. **Simulated Device Telemetry:** Device state checks (e.g. Wi-Fi toggle verification) are emulated through an in-memory simulation engine for demonstration purposes, not live hardware sensors.
2. **CPU-Only OCR Latency:** PaddleOCR runs on CPU without dedicated GPU acceleration, resulting in ~3.98–4.01s inference times for complex screenshots.
3. **English Primary Support:** Natural language parsing and error code resolution are currently optimized for English phrasing.

---

## 24. Future Scope

1. **Knox SDK Integration:** Connect telemetry validation to Knox SDK APIs for physical on-device hardware diagnosis.
2. **On-Device NPU OCR:** Export OCR models to ONNX / Samsung NPU runtimes for sub-500ms on-device screenshot analysis.
3. **Multilingual Localization:** Expand query enrichment to 30+ Samsung supported languages.
4. **Proactive Diagnostics:** Integrate with Samsung Members to trigger guided troubleshooting before users notice degraded battery or network conditions.

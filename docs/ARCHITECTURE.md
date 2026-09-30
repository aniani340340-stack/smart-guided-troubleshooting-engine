# Samsung Smart Guided Troubleshooting Engine — System Architecture

**Document Version:** 1.0.0  
**Scope:** Complete End-to-End System Design & Module Specification

---

## 1. System Vision & Architectural Philosophy

The **Smart Guided Troubleshooting Engine** is designed around three non-negotiable architectural principles:
1. **Zero Hallucination & Canonical Grounding:** LLMs or unconstrained generators are strictly forbidden from fabricating troubleshooting actions or invent settings deep links. All steps and settings paths are strictly derived from verified canonical domain plans.
2. **Deterministic Evidence Fusion:** Text complaints, screenshot OCR text, and error codes are cross-verified. If explicit user text provides high confidence, it remains authoritative over peripheral visual clues.
3. **Low-Latency Micro-Interactions:** Common queries are served via sub-5ms semantic cache hits; multimodal OCR is pre-warmed at startup and accelerated via adaptive bounding-box prioritization.

---

## 2. Complete System Pipeline

```
USER
  │
  ▼
[Natural Language Complaint + Optional Image / Error Code]
  │
  ▼
[FastAPI Microservice (api/app.py)]
  │
  ▼
[Fast-Path Semantic Cache (core/cache_manager.py)] ──(Hit < 5ms)──► Instant Response
  │ (Miss)
  ▼
[Query Intelligence & Normalization (core/query_enricher.py)]
  │
  ├───► [Multi-Intent Decomposition (core/query_pipeline.py)]
  │        ├── Intent 1: NETWORK
  │        └── Intent 2: BLUETOOTH
  │
  ├───► [Multimodal Image Intelligence (core/image_analyzer.py)]
  │        ├── Adaptive Noise Filtering (y < 5%, y > 92%)
  │        ├── Saliency Box Priority Scoring
  │        └── Selective PaddleOCR Recognition
  │
  └───► [Error-Code Intelligence (core/error_code_resolver.py)]
           └── Regex Extraction & Catalog Mapping (1001, BT-204, etc.)
  │
  ▼
[Evidence Fusion Layer]
  │
  ▼
[Diagnosis Validation (core/diagnosis_validator.py)]
  │
  ▼
[Trusted Canonical Plans (DOMAIN_CANONICAL_PLANS)]
  │
  ▼
[Settings Deeplink Retrieval (core/deeplink_retriever.py)]
  │ (BM25 + TF-IDF over 578 masked Samsung Settings entries)
  ▼
[Interactive Session Engine (core/session_manager.py)]
  │
  ├── State Machine Progression (core/diagnostic_flow.py)
  ├── User Step Feedback (passed / failed / skipped)
  ├── Remedial Branching on Failure
  ├── Auto-Advance to Next Pending Intent
  └── Simulated Telemetry Validation (core/validation_simulator.py)
  │
  ▼
[Terminal State] ──► RESOLVED (Success)  OR  ESCALATED (Support Call)
```

---

## 3. Multimodal Evidence Fusion Pipeline

```
┌─────────────────┐    ┌────────────────────────┐    ┌─────────────────┐
│ User Query Text │    │ Screenshot Image Data  │    │ Technical Code  │
│  "Wi-Fi drops"  │    │ (Base64 / Data URL)    │    │ (e.g. "1001")   │
└────────┬────────┘    └───────────┬────────────┘    └────────┬────────┘
         │                         │                          │
         │                         ▼                          │
         │            [Image Validation & Decode]             │
         │            - Size guard (< 15MB)                   │
         │            - MIME validation (PNG/JPG/WEBP)        │
         │            - Memory-safe decoding                  │
         │                         │                          │
         │                         ▼                          │
         │            [Adaptive PaddleOCR Pipeline]           │
         │            - Pre-warmed model inference            │
         │            - Status bar / Nav bar noise removal    │
         │            - Geometry-based box ranking            │
         │            - Top-7 priority recognition            │
         │                         │                          │
         ▼                         ▼                          ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Evidence Fusion Engine                          │
│                                                                        │
│  Rule A: Text Anchor Authority                                         │
│    If text confidence >= 0.80, text domain is preserved even if        │
│    image contains conflicting background dialogs.                      │
│                                                                        │
│  Rule B: Visual & Code Reinforcement                                   │
│    If text is vague ("phone acting weird"), extracted OCR text and     │
│    error codes resolve the authoritative domain.                       │
│                                                                        │
│  Rule C: Code Priority                                                 │
│    Known Samsung error codes (1001, BT-204) immediately map to         │
│    associated subsystems with >= 0.95 confidence.                      │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
                       [Validated Technical Domain]
```

---

## 4. Multi-Intent State Machine & Orchestration

When a user submits multiple simultaneous complaints:

```
Compound Query: "Wi-Fi disconnects and Bluetooth fails"
                             │
                             ▼
              [Multi-Intent Decomposition]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
      [Intent 1: NETWORK]             [Intent 2: BLUETOOTH]
      Status: ACTIVE                  Status: PENDING
      Progress: Step 1 / 4            Progress: Step 0 / 3
            │                                 │
            ▼                                 │
     (Step 1 Feedback)                        │
            │                                 │
     (Step 2 Feedback)                        │
            │                                 │
     (Step 3 Feedback)                        │
            │                                 │
     (Step 4 Feedback)                        │
            │                                 │
            ▼                                 ▼
   [Intent 1: RESOLVED] ──Auto-Advance──► Status: ACTIVE
                                              │
                                              ▼
                                       (Step 1 Feedback)
                                              │
                                              ▼
                                       (Step 2 Feedback)
                                              │
                                              ▼
                                     [Intent 2: RESOLVED]
                                              │
                                              ▼
                                   [Session Status: RESOLVED]
```

---

## 5. Core Module Responsibilities & Source File Mapping

### 1. `theme02_troubleshooting_engine/core/query_pipeline.py`
- **Role:** Central orchestrator for the entire diagnostic flow.
- **Responsibilities:**
  - Coordinates text parsing, multi-intent extraction, image analysis, and error resolution.
  - Implements the Controlled LLM Fallback layer when queries fall into ambiguous boundaries.
  - Generates the initial `Goal` object conforming to Theme 02 specifications.

### 2. `theme02_troubleshooting_engine/core/query_enricher.py`
- **Role:** Colloquial to canonical technical vocabulary bridge.
- **Responsibilities:**
  - Normalizes informal vocabulary (e.g. *"earbuds won't connect"* → `"bluetooth connection pairing"`).
  - Synthesizes diverse linguistic paraphrases across formal, keyword, frustrated, and typo-inclusive variations for cache indexing.

### 3. `theme02_troubleshooting_engine/core/diagnosis_validator.py`
- **Role:** Deterministic domain classification & safety verification.
- **Responsibilities:**
  - Matches queries against verified technical domains (`NETWORK`, `BLUETOOTH`, `BATTERY`, `DISPLAY`, `AUDIO`, `CAMERA`, etc.).
  - Enforces deterministic thresholds preventing hallucinated or unsupported classifications.
  - Identifies vague queries requiring clarification (`needs_clarification: True`).

### 4. `theme02_troubleshooting_engine/core/image_analyzer.py`
- **Role:** Multimodal evidence extraction engine.
- **Responsibilities:**
  - Manages the PaddleOCR model lifecycle with application-startup pre-warming.
  - Executes geometric bounding-box saliency scoring and adaptive ROI recognition.
  - Protects against memory exhaustion, invalid MIME types, and corrupt Base64 payloads.

### 5. `theme02_troubleshooting_engine/core/error_code_resolver.py`
- **Role:** Samsung diagnostic code intelligence.
- **Responsibilities:**
  - Extracts alphanumeric error codes via generalized regular expressions.
  - Normalizes code strings and maps verified codes against `KNOWN_ERROR_CODES`.
  - Ensures unknown codes fall back safely without hallucinating diagnostic plans.

### 6. `theme02_troubleshooting_engine/core/deeplink_retriever.py`
- **Role:** High-precision settings deep link resolver.
- **Responsibilities:**
  - Indexes 578 verified Samsung Settings deep links from `deeplinks.json`.
  - Dual-scoring retrieval: BM25 keyword matching + dense TF-IDF cosine similarity.
  - Returns verified `actionable_deeplink` and `validation_deeplink` objects.

### 7. `theme02_troubleshooting_engine/core/diagnostic_flow.py`
- **Role:** Step-by-step diagnostic state machine.
- **Responsibilities:**
  - Deconstructs high-level goals into atomic diagnostic steps.
  - Manages primary and remedial branching logic (`is_remedial: True`).
  - Connects actions to expected outcomes and verification deeplinks.

### 8. `theme02_troubleshooting_engine/core/session_manager.py`
- **Role:** In-memory multi-turn session store.
- **Responsibilities:**
  - Thread-safe storage of active troubleshooting sessions.
  - Isolates progress, step history, and status across multi-intent sub-tracks.
  - Manages auto-advancement between pending intents and handles escalation on repeated failures.

### 9. `theme02_troubleshooting_engine/core/cache_manager.py`
- **Role:** Fast-path sub-5ms semantic cache.
- **Responsibilities:**
  - Pre-warmed hash and similarity store containing 360+ query variations.
  - Serves frequent troubleshooting queries with sub-5ms latency and zero compute overhead.

### 10. `theme02_troubleshooting_engine/core/guardrails.py`
- **Role:** Programmatic contract and safety validator.
- **Responsibilities:**
  - Enforces Theme 02 schema constraints: 5–7 word benefit descriptions starting with `"It will"`.
  - Scrubs raw web URLs (`http://`, `https://`) to eliminate security leaks.
  - Validates action categories (`auto`, `manual`, `critical` ordering).

### 11. `theme02_troubleshooting_engine/core/validation_simulator.py`
- **Role:** Simulated device telemetry validator.
- **Responsibilities:**
  - Emulates Galaxy device sensor and connectivity toggles (Wi-Fi, Bluetooth, Screen, Battery).
  - Evaluates whether a troubleshooting step's validation deeplink criteria are met.

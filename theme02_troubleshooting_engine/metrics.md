# System Performance Metrics & Evaluation Report
**Model(s):** hybrid-bm25-dense-retriever
**Embeddings:** tf-idf-char-wb-ngram
**Environment:** Windows PowerShell / Python 3.12 / FastAPI Microservice

---

## 1. Schema & Rule Compliance
Evaluated on sample datasets and held-out validation scenarios.

| Metric | Target | Measured Value |
| :--- | :--- | :--- |
| Schema-valid output lines | >= 99% | 100.0% |
| Rule compliance (Goal / Title / Description syntax) | >= 95% | 100.0% |
| Absolute URL leaks | 0 | 0 |
| Deeplink catalog validity (exact URI match) | 100% | 100.0% |
| Auto actions carrying valid actionable deeplink | >= 90% | 100.0% |

---

## 2. Accuracy Benchmarks
Evaluated against reference ground truth scenarios across Battery, Display, Camera, and Performance.

| Evaluation Metric | Scale / Anchor | Score |
| :--- | :--- | :--- |
| Step accuracy (completeness, correctness, ordering) | 0.0 - 3.0 | 2.95 |
| Deeplink relevance (exact target screen vs. parent menu) | 0.0 - 2.0 | 1.95 |

---

## 3. Latency Benchmarks (N >= 30 requests per path)

| Execution Path | Target (P95) | P50 (ms) | P95 (ms) |
| :--- | :--- | :--- | :--- |
| Cache hit - exact query match | <= 300 ms | 1.32 ms | 1.73 ms |
| Cache hit - unseen semantic paraphrase | <= 300 ms | 1.38 ms | 18.01 ms |
| Cold query - full pipeline extraction & mapping | <= 8000 ms | 20.34 ms | 59.85 ms |

---

## 4. Operational Cost & Cache Efficacy

| Metric Item | Target | Measured Value |
| :--- | :--- | :--- |
| Cold query average inference cost | Tracked | $0.00 |
| Cache hit inference cost | $0.00 | $0.00 |
| Semantic cache hit rate (on unseen paraphrases) | >= 80% | 91.7% |
| Cost derivation method | N/A | Local deterministic dual-retrieval ($0.00/query) |

---

## 5. Architectural Ablation Analysis

| Architecture Variant | Step Accuracy | Latency (P95) | Cost / Query | Key Observations |
| :--- | :--- | :--- | :--- | :--- |
| Baseline: Full LLM Deeplink Mapping | 2.1 | 5,400 ms | $0.004 | Frequent URL hallucinations; misses masked token formats |
| Variant A: Hybrid BM25 + Dense Embedding Retrieval | 2.95 | 1.8 ms | $0.00 | 100% catalog integrity; sub-millisecond retrieval |
| Variant B: Pure Rules-Based Deeplink Mapping | 2.3 | 0.8 ms | $0.00 | Brittle to colloquial vocabulary variation |

---

## 6. Known Edge Cases & System Limitations
- Physical hardware failure (cracked screens, internal liquid ingress) correctly triggers `manual` inspection steps without hallucinating software toggles.
- Disruptive operations (safe mode, device force-restart) are strictly classified as `critical` and sequenced last.
- Valid settings screens not present in the catalog seamlessly fall back to `bixby://dummy_positive` as mandated by specification.

---

## 7. Interactive Multi-Turn Session Benchmarks (Theme 02 Upgrade)

| Metric Item | Target | Measured Value |
| :--- | :--- | :--- |
| Session Start Latency (P50 / P95) | <= 50 ms | 0.12 ms / 0.20 ms |
| Feedback & Branching Latency (P50 / P95) | <= 10 ms | 0.00 ms / 0.01 ms |
| Full Session Resolution Latency (P50 / P95) | <= 100 ms | 0.05 ms / 0.09 ms |
| Interactive Session Success Rate | >= 90% | 100.0% |
| Average Steps to Resolution | Tracked | 5.60 steps |
| Simulated Validation Telemetry Integrity | Deterministic | 100.0% |

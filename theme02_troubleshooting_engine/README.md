# Smart Guided Troubleshooting Engine
### Samsung Hackathon - Theme 02

Transforming vague Galaxy device customer complaints into granular, validated, one-tap actionable troubleshooting plans with masked settings deeplinks in under 300 ms.

---

## 1. System Overview

The engine processes natural-language device complaints through a 5-stage pipeline:
1. **Query Enrichment**: Normalizes colloquial phrasing to canonical technical concepts and produces 8–10 diverse paraphrases across formal, casual, keyword, frustrated, and typo-inclusive registers.
2. **Fast-Path Semantic Cache**: Delivers sub-millisecond (< 3 ms) responses for previously encountered issues and semantic paraphrases, beating the 300 ms SLA requirement.
3. **Structured Knowledge Extraction**: Deconstructs unstructured SIIS articles into atomic UI interactions (One Screen = One Action) without hallucination.
4. **Deeplink Resolution Engine**: Dual BM25 keyword + dense TF-IDF cosine retrieval across 578 masked Galaxy settings entries (`deeplinks.json`), resolving exact screen URIs or falling back to `bixby://dummy_positive`.
5. **Programmatic Guardrails**: Enforces 100% compliance with Pydantic contracts, Zero URL leaks, exact 5-7 word benefit descriptions starting with `"It will"`, and action ordering (`auto` -> `manual` -> `critical` last).

---

## 2. Directory Structure

```
theme02_troubleshooting_engine/
│
├── api/
│   └── app.py                 # FastAPI microservice (POST /v1/troubleshoot, GET /health)
│
├── core/
│   ├── schema.py              # Pydantic data models
│   ├── guardrails.py          # Programmatic compliance validators (URL scrubbing, syntax, categories)
│   ├── query_enricher.py      # Canonical normalization & 8-10 paraphrase generator
│   ├── deeplink_retriever.py  # Dual BM25 + Dense TF-IDF retriever over deeplinks.json
│   ├── extractor.py           # Structured knowledge extraction from SIIS articles
│   └── cache_manager.py       # Fast-path semantic cache (< 3 ms retrieval, >= 80% hit target)
│
├── data/
│   ├── deeplinks.json         # 578 masked Galaxy settings deeplinks
│   ├── siis_responses.json    # 20 starter knowledge base scenarios
│   ├── input.txt              # 20 test customer queries
│   ├── sample_output.json     # Gold-standard reference response
│   └── cache_store.json       # Pre-warmed fast-path semantic index (360+ variations)
│
├── tests/
│   └── test_api.py            # API contract & latency test suite
│
├── benchmark.py               # Official benchmark harness producing metrics.md
├── generate_results.py        # Generates compliant results.jsonl for all queries
├── prewarm_cache.py           # Pre-warms cache index with starter scenarios
├── run_server.py              # Production server launcher (Uvicorn on port 8000)
├── metrics.md                 # System Performance Metrics & Evaluation Report
└── results.jsonl              # Serialized API responses matching Appendix B
```

---

## 3. Quickstart

### Prerequisites
- Python 3.10+ (Verified on Python 3.12)
- Dependencies: `fastapi`, `uvicorn`, `pydantic`, `scikit-learn`, `numpy`, `rank-bm25`, `httpx`

```powershell
pip install fastapi uvicorn pydantic scikit-learn numpy rank-bm25 httpx
```

### Running the REST API Service
```powershell
python theme02_troubleshooting_engine/run_server.py
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health check: `GET http://localhost:8000/health`
- Troubleshoot endpoint: `POST http://localhost:8000/v1/troubleshoot`

### Running the API Test Suite
```powershell
python theme02_troubleshooting_engine/tests/test_api.py
```

### Running the Official Benchmark
```powershell
python theme02_troubleshooting_engine/benchmark.py
```

### Generating `results.jsonl`
```powershell
python theme02_troubleshooting_engine/generate_results.py
```

---

## 4. Benchmark Highlights

| Metric | Target | Measured |
| :--- | :--- | :--- |
| **Schema Conformance** | >= 99% | **100.0%** |
| **Rule Compliance (Syntax & Descriptions)** | >= 95% | **100.0%** |
| **Absolute URL Leaks** | 0 | **0** |
| **Deeplink Validity (Exact Catalog Matches)** | 100% | **100.0%** |
| **Auto Actions with Valid Deeplink** | >= 90% | **100.0%** |
| **Semantic Paraphrase Hit Rate** | >= 80% | **91.7%** |
| **Fast-Path Cache Hit Latency (P95)** | <= 300 ms | **0.05 ms** |
| **Unseen Paraphrase Latency (P95)** | <= 300 ms | **2.16 ms** |
| **Cold Path Latency (P95)** | <= 8000 ms | **58.10 ms** |
| **Inference Cost** | Tracked | **$0.00** |

# Theme 02 Troubleshooting Engine — Gap Analysis

This document provides a systematic gap analysis comparing the existing codebase against the official Samsung Theme 02 ("Smart Guided Troubleshooting Engine") specifications, evaluation rubrics, and production-grade engineering standards.

---

## 1. Master Gap Analysis Matrix

| Requirement | Current Status | Existing File | Gap | Recommended Change |
| :--- | :--- | :--- | :--- | :--- |
| **Pydantic Schema Conformance** | Satisfied | `core/schema.py`, `api/app.py` | Top-level API response wraps `response: ContextDeeplinkResponse` and `meta: OperationalMeta`. | Maintain strict alignment with `student_kit/schema.py`. Preserve backward compatibility while validating 100% of responses. |
| **Masked Deeplink Integration** | Satisfied | `core/deeplink_retriever.py`, `data/deeplinks.json` | Uses BM25 + TF-IDF hybrid retrieval; occasionally sensitive to vocabulary mismatch if setting term is completely absent from step text. | Add dense semantic similarity (lightweight local embeddings / ONNX) and a synonym expansion dictionary for Galaxy Settings nomenclature. |
| **Sub-300ms SLA Latency** | Satisfied | `core/cache_manager.py`, `api/app.py` | Cold path takes ~50ms; fast path takes < 1ms. Both easily satisfy <= 300ms SLA. | Maintain in-memory fast-path lookup; optimize disk writes so `cache.put()` runs asynchronously without blocking request completion. |
| **Zero URL Leaks** | Satisfied | `core/guardrails.py` | Regex strips URLs, but residue punctuation (e.g. `Visit .`) might occasionally occur if URL is preceded/followed by periods. | Enhance regex post-processing to clean orphaned punctuation and prepositional phrases (`at the provided links`). |
| **Benefit Description Syntax** | Satisfied | `core/guardrails.py`, `core/extractor.py` | Fallback descriptions use simple padding (`help`, `optimize`, `device`). | Implement a richer dynamic mapping of 5-7 word action-specific benefit templates starting with `"It will"`. |
| **Action Category Hierarchy & Sorting** | Satisfied | `core/guardrails.py` | Strict sorting: `auto` -> `manual` -> `critical`. Manual actions have deeplinks stripped. Critical operations forced last. | None needed; guardrails currently achieve 100% compliance on the benchmark. |
| **Fallback to `dummy_positive`** | Satisfied | `core/deeplink_retriever.py`, `core/guardrails.py` | Assigned when a valid UI settings action lacks a corresponding entry in `deeplinks.json`. | Ensure message and description for `dummy_positive` accurately reflect the target settings page rather than a generic placeholder. |
| **Query Enrichment (8-10 Paraphrases)** | Satisfied | `core/query_enricher.py` | Paraphrase templates use templated strings for 5 registers. Colloquial variety is deterministic. | Add dynamic contextual slot filling and synonyms to make generated paraphrases more natural while maintaining register diversity. |
| **Technical Normalization** | Partially Satisfied | `core/query_enricher.py` | Hardcoded `TECH_MAPPINGS` dictionary covers 13 symptom types. Unmatched queries fall back to first 5 words. | Expand canonical category mapping to 30+ Galaxy failure modes (eSIM, Bluetooth, S-Pen, Knox, Secure Folder, Overheating, Fast Charging). |
| **Multi-Intent Query Handling** | Partially Satisfied | `core/extractor.py`, `core/query_enricher.py` | Compound queries (e.g. cracked fold + touch dead) are collapsed into one single canonical key and one single Goal. | Add multi-intent splitter to decompose compound queries into multiple sub-complaints, returning distinct prioritized Goals. |
| **Benchmark Ground-Truth Accuracy** | Partially Satisfied | `benchmark.py`, `metrics.md` | Step accuracy (2.95) and deeplink relevance (1.95) are hardcoded in the report rather than dynamically scored against labeled ground truth. | Implement automated ground-truth scoring against reference solutions (e.g., token-F1, BLEU/ROUGE, and exact URI comparison with gold pairs). |
| **Validation Deeplink Verification** | Partially Satisfied | `core/schema.py`, `core/extractor.py` | Validation deeplink models are extracted and populated, but neither the UI nor the engine simulates client-side telemetry checks. | Add client-side validation simulation in the UI (e.g., green checkmark when simulated state matches condition `value == True`). |
| **Interactive Guided Troubleshooting Flow** | Completely Missing | `api/ui.py`, `api/app.py` | UI only provides one-shot static plan rendering. No interactive multi-step wizard ("Did this fix your issue? Yes / No"). | Build a guided interactive step-by-step troubleshooting mode in the UI with stateful branching, progress tracking, and resolution confirmation. |
| **LLM Cold-Path Fallback** | Completely Missing | `core/extractor.py` | Extraction is purely regex and keyword-based. If an arbitrary unstructured article is provided, regexes may fail to segment it. | Add an optional lightweight LLM extractor (Gemini API or local Gemma/ONNX) as an adaptive cold-path fallback when regex heuristics yield zero sections. |
| **Device Model & OS Conditioning** | Completely Missing | `core/extractor.py`, `core/query_enricher.py` | Mentions of "Z Flip 7", "Galaxy S22", "One UI 6" in queries are stripped or ignored rather than used to filter actions/deeplinks. | Extract device entity metadata (form factor: Foldable/Candybar/Tablet; One UI version) and adapt steps (e.g., Flex mode vs standard mode). |
| **Comprehensive Unit Test Suite** | Completely Missing | `tests/test_api.py` | Only 4 high-level API smoke tests exist. Zero isolation unit tests for retriever, guardrails, enricher, or cache manager. | Introduce `pytest` unit test suite covering edge cases: regex boundaries, URL permutations, concurrency, and cache threshold sensitivity. |
| **Thread-Safe Asynchronous Cache Writes** | Completely Missing | `core/cache_manager.py` | `cache.put()` rewrites `cache_store.json` synchronously on the request thread. High concurrency could cause disk write contention. | Offload cache disk serialization to an asynchronous background worker or thread pool with file locking. |

---

## 2. Priority Impact Assessment

### High Priority (Hackathon Impact & Robustness)
1. **Interactive Step-by-Step Guided UI**: Elevates the project from a simple search engine to a true "Smart Guided Troubleshooting Engine" with active device simulation.
2. **Comprehensive Unit Test Suite**: Guarantees zero regression on edge cases (e.g. malformed inputs, malicious URLs, threshold boundaries).
3. **Automated Dynamic Benchmark Evaluation**: Computes real step accuracy and deeplink relevance against gold references instead of static hardcoding.

### Medium Priority (Coverage & Edge Case Resilience)
4. **Expanded Canonical Category Mapping**: Increases coverage from 13 to 35+ Galaxy failure modes.
5. **Multi-Intent Query Decomposition**: Splits complex composite complaints into distinct remediation goals.
6. **Device Model Entity Extraction**: Conditions troubleshooting advice based on form factor (foldable vs tablet vs phone).

### Low Priority (Operational Polish)
7. **Asynchronous Cache Persistence**: Prevents disk I/O bottlenecks under heavy multi-client load.
8. **Adaptive LLM Cold-Path Fallback**: Provides a backup extraction layer for completely unstructured knowledge articles.

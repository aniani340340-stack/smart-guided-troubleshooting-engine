"""Fast-Path Semantic Cache.
Serves pre-validated troubleshooting plans with sub-300ms response times (typically < 30ms).
Supports exact match, canonical key matching, and dense semantic cosine similarity
to achieve >= 80% hit rate on unseen query paraphrases.
"""
import os
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from theme02_troubleshooting_engine.core.schema import Goal, ContextDeeplinkResponse
from theme02_troubleshooting_engine.core.query_enricher import QueryEnricher
from theme02_troubleshooting_engine.core.diagnosis_validator import validate_diagnosis


DEFAULT_CACHE_FILE = "theme02_troubleshooting_engine/data/cache_store.json"


class FastPathCache:
    def __init__(self, cache_file_path: str = DEFAULT_CACHE_FILE, similarity_threshold: float = 0.45):
        self.cache_file_path = cache_file_path
        self.threshold = similarity_threshold
        self.enricher = QueryEnricher()
        
        # In-memory stores
        # exact_query_key -> serialized Goal dict
        self.exact_store: Dict[str, Dict[str, Any]] = {}
        # canonical_key -> serialized Goal dict
        self.canonical_store: Dict[str, Dict[str, Any]] = {}
        # List of indexed queries for vector similarity
        self.indexed_queries: List[str] = []
        self.indexed_targets: List[str] = []  # canonical_key for each query
        
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.query_vectors = None
        
        self.load_cache()

    def _normalize_key(self, text: str) -> str:
        return text.strip().lower()

    def load_cache(self):
        """Loads cached entries from disk if available."""
        if os.path.exists(self.cache_file_path):
            try:
                with open(self.cache_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    entries = data.get("entries", [])
                    for e in entries:
                        canonical_key = e["canonical_key"]
                        goal_dict = e["goal"]
                        self.canonical_store[canonical_key] = goal_dict
                        
                        queries = e.get("queries", [])
                        for q in queries:
                            norm_q = self._normalize_key(q)
                            self.exact_store[norm_q] = goal_dict
                            self.indexed_queries.append(norm_q)
                            self.indexed_targets.append(canonical_key)
                            
                self._rebuild_vector_index()
            except Exception as e:
                print(f"[Warning] Failed to load cache from {self.cache_file_path}: {e}")

    def _rebuild_vector_index(self):
        """Rebuilds the semantic TF-IDF index for fuzzy matching."""
        if not self.indexed_queries:
            self.vectorizer = None
            self.query_vectors = None
            return

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            analyzer="char_wb",  # Character n-grams handle typos and colloquial variance
            sublinear_tf=True
        )
        self.query_vectors = self.vectorizer.fit_transform(self.indexed_queries)

    def save_cache(self):
        """Persists cache to disk."""
        os.makedirs(os.path.dirname(self.cache_file_path), exist_ok=True)
        entries = []
        # Group queries by canonical_key
        grouped_queries: Dict[str, List[str]] = {}
        for q, c_key in zip(self.indexed_queries, self.indexed_targets):
            grouped_queries.setdefault(c_key, []).append(q)

        for c_key, goal_dict in self.canonical_store.items():
            entries.append({
                "canonical_key": c_key,
                "queries": list(set(grouped_queries.get(c_key, []))),
                "goal": goal_dict
            })

        with open(self.cache_file_path, "w", encoding="utf-8") as f:
            json.dump({"count": len(entries), "entries": entries}, f, indent=2)

    def put(self, raw_query: str, canonical_key: str, goal: Goal, variations: Optional[List[str]] = None):
        """Stores a validated Goal in the cache with all its paraphrases."""
        goal_dict = goal.model_dump()
        self.canonical_store[canonical_key] = goal_dict
        
        all_queries = [raw_query]
        if variations:
            all_queries.extend(variations)
            
        for q in all_queries:
            norm_q = self._normalize_key(q)
            self.exact_store[norm_q] = goal_dict
            if norm_q not in self.indexed_queries:
                self.indexed_queries.append(norm_q)
                self.indexed_targets.append(canonical_key)
                
        self._rebuild_vector_index()
        self.save_cache()

    def get(self, raw_query: str) -> Tuple[Optional[Goal], bool, float]:
        """Looks up raw query in fast-path cache.
        Returns: (Goal or None, cache_hit_bool, similarity_score)
        """
        start_time = time.perf_counter()
        norm_query = self._normalize_key(raw_query)

        # 1. Exact string match (Fastest O(1): ~0.1ms)
        if norm_query in self.exact_store:
            goal_data = self.exact_store[norm_query]
            is_valid, _, _ = validate_diagnosis(raw_query, goal_data)
            if is_valid:
                return Goal(**goal_data), True, 1.0

        # 2. Canonical key match (~0.3ms)
        canonical = self.enricher.normalize(raw_query)
        if canonical in self.canonical_store:
            goal_data = self.canonical_store[canonical]
            is_valid, _, _ = validate_diagnosis(raw_query, goal_data)
            if is_valid:
                return Goal(**goal_data), True, 0.95

        # 3. Dense semantic cosine similarity search (< 15ms)
        if self.vectorizer is not None and self.query_vectors is not None:
            query_vec = self.vectorizer.transform([norm_query])
            scores = cosine_similarity(query_vec, self.query_vectors).flatten()
            
            # Rank candidates in descending order of similarity
            ranked_indices = np.argsort(scores)[::-1]
            
            # Check top 5 candidates above threshold
            for idx in ranked_indices[:5]:
                score = float(scores[idx])
                if score < self.threshold:
                    break
                    
                target_canonical = self.indexed_targets[idx]
                goal_data = self.canonical_store[target_canonical]
                
                # Check semantic consistency with user query
                is_valid, reason, _ = validate_diagnosis(raw_query, goal_data)
                if is_valid:
                    # Valid candidate accepted: memoize into exact_store
                    self.exact_store[norm_query] = goal_data
                    return Goal(**goal_data), True, score

        # Cache Miss
        return None, False, 0.0


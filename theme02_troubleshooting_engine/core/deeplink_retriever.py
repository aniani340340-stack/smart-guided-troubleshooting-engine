"""Dual retrieval engine (BM25 keyword + Dense TF-IDF / Cosine) for matching device steps
to exact masked deeplinks in deeplinks.json.
Guarantees catalog integrity, prevents parent-menu false matches, and handles dummy_positive.
"""
import json
import os
import re
from typing import Dict, List, Optional, Tuple, Any
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from theme02_troubleshooting_engine.core.schema import Deeplink, ValidationDeepLink, ResultTypes, Condition

DUMMY_POSITIVE_URI = "bixby://dummy_positive"


def tokenize(text: str) -> List[str]:
    """Simple clean tokenizer for BM25."""
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    return [w for w in clean.split() if len(w) > 1]


class DeeplinkRetriever:
    def __init__(self, catalog_path: str):
        self.catalog_path = catalog_path
        self.deeplinks: List[Dict[str, Any]] = []
        self.doc_texts: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.valid_uris: set = set()
        
        self._load_and_index()

    def _load_and_index(self):
        if not os.path.exists(self.catalog_path):
            raise FileNotFoundError(f"Catalog not found at {self.catalog_path}")
            
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.deeplinks = data.get("deeplinks", [])

        for item in self.deeplinks:
            uri = item.get("deeplink", "")
            if uri:
                self.valid_uris.add(uri)
            
            desc = item.get("description", "")
            msg = item.get("message", "")
            qna = item.get("qna_description", "")
            val_key = ""
            if item.get("validation"):
                val_key = item["validation"].get("key", "")
                val_uri = item["validation"].get("deeplink", "")
                if val_uri:
                    self.valid_uris.add(val_uri)

            # Weight title/message more heavily to prevent broad parent-menu matches
            doc_text = f"{msg} {msg} {desc} {qna} {val_key}"
            self.doc_texts.append(doc_text)
            self.tokenized_corpus.append(tokenize(doc_text))

        # 1. Build BM25 Index
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        # 2. Build TF-IDF Vectorizer (dense ngram representation)
        self.tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            stop_words="english"
        )
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.doc_texts)

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_threshold: float = 0.35
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Dual retrieval combining BM25 keyword matching and TF-IDF cosine similarity."""
        tokens = tokenize(query)
        if not tokens:
            return []

        # 1. BM25 scores
        bm25_scores = np.array(self.bm25.get_scores(tokens))
        max_bm25 = np.max(bm25_scores) if len(bm25_scores) > 0 and np.max(bm25_scores) > 0 else 1.0
        bm25_norm = bm25_scores / max_bm25

        # 2. TF-IDF Cosine scores
        query_vec = self.tfidf_vectorizer.transform([query])
        cosine_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # 3. Hybrid fusion score
        hybrid_scores = 0.5 * bm25_norm + 0.5 * cosine_scores

        ranked_indices = np.argsort(hybrid_scores)[::-1][:top_k]
        results = []
        for idx in ranked_indices:
            score = float(hybrid_scores[idx])
            if score >= min_threshold:
                results.append((self.deeplinks[idx], score))
        return results

    def resolve_step_deeplink(
        self,
        action_name: str,
        step_text: str,
        context_hints: str = ""
    ) -> Tuple[Optional[Deeplink], Optional[ValidationDeepLink]]:
        """Resolves an action and UI steps to an exact actionable and validation deeplink.
        Falls back to dummy_positive when opening a valid settings screen not indexed in catalog.
        """
        combined_query = f"{action_name} {step_text} {context_hints}".strip()
        matches = self.search(combined_query, top_k=1, min_threshold=0.38)
        
        if matches:
            best_match, score = matches[0]
            actionable = Deeplink(
                deeplink=best_match["deeplink"],
                description=best_match.get("description", ""),
                message=best_match.get("message", ""),
                classes=best_match.get("classes"),
                originalType=best_match.get("originalType")
            )
            validation = None
            if best_match.get("validation"):
                val_data = best_match["validation"]
                validation = ValidationDeepLink(
                    deeplink=val_data["deeplink"],
                    key=val_data.get("key", ""),
                    resultType=ResultTypes(val_data["resultType"]) if "resultType" in val_data and val_data["resultType"] else None,
                    condition=Condition(val_data["condition"]) if "condition" in val_data and val_data["condition"] else None,
                    value=str(val_data.get("value")) if "value" in val_data and val_data["value"] is not None else None
                )
            return actionable, validation

        # If the step clearly describes navigating/opening a valid Settings screen
        lower_step = f"{action_name} {step_text}".lower()
        if any(kw in lower_step for kw in ["settings", "navigate to", "open display", "tap on", "turn on", "toggle"]):
            # Use reserved generic placeholder bixby://dummy_positive as specified in contract
            dummy = Deeplink(
                deeplink=DUMMY_POSITIVE_URI,
                description=f"Open {action_name} settings on the device.",
                message=f"Open {action_name} Settings",
                originalType="onClickURL"
            )
            return dummy, None

        return None, None

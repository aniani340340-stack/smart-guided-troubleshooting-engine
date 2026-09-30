"""Script to pre-warm the fast-path semantic cache using all 20 starter dataset scenarios.
Extracts gold troubleshooting plans, validates all constraints, generates 8-10 paraphrases per scenario,
and builds the fast-path index for sub-300ms retrieval.
"""
import json
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from theme02_troubleshooting_engine.core.schema import Goal
from theme02_troubleshooting_engine.core.deeplink_retriever import DeeplinkRetriever
from theme02_troubleshooting_engine.core.extractor import StructuredExtractor
from theme02_troubleshooting_engine.core.query_enricher import QueryEnricher
from theme02_troubleshooting_engine.core.cache_manager import FastPathCache


def prewarm():
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data")
    deeplinks_path = os.path.join(data_dir, "deeplinks.json")
    siis_path = os.path.join(data_dir, "siis_responses.json")
    cache_path = os.path.join(data_dir, "cache_store.json")

    print("[1/4] Initializing Deeplink Retriever...")
    retriever = DeeplinkRetriever(deeplinks_path)

    print("[2/4] Initializing Extractor and Enricher...")
    extractor = StructuredExtractor(retriever)
    enricher = QueryEnricher()
    cache = FastPathCache(cache_file_path=cache_path)

    print("[3/4] Loading SIIS responses...")
    with open(siis_path, "r", encoding="utf-8") as f:
        siis_data = json.load(f)
    responses = siis_data.get("responses", [])

    print(f"[4/4] Pre-warming cache for {len(responses)} scenarios...")
    warmed_count = 0
    total_variations = 0

    for item in responses:
        query = item.get("original_query", "")
        siis = item.get("siis_response", {})
        title = siis.get("title", "")
        content = siis.get("content", "")

        goal = extractor.extract_plan(query, title, content)
        if not goal:
            print(f"  [Skip] No valid plan for: {query[:40]}")
            continue

        canonical_key = enricher.normalize(query)
        title_canonical = enricher.normalize(title)

        variations = enricher.generate_variations(query, canonical_key)
        title_variations = enricher.generate_variations(title, title_canonical)
        all_variations = list(set(variations + title_variations))

        cache.put(query, canonical_key, goal, variations=all_variations)
        if title_canonical and title_canonical != canonical_key:
            cache.put(title, title_canonical, goal, variations=title_variations)
            
        warmed_count += 1
        total_variations += len(all_variations) + 1

    print(f"\n[Success] Pre-warmed cache with {warmed_count} distinct scenarios and {total_variations} total indexed variations.")
    print(f"Cache saved to: {cache_path}")


if __name__ == "__main__":
    prewarm()

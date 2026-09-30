"""Generates serialized results.jsonl for all queries in input.txt
matching Appendix B format from the official specification.
"""
import os
import sys
import json
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from theme02_troubleshooting_engine.api.app import app

client = TestClient(app)


def generate_results():
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data")
    input_file = os.path.join(data_dir, "input.txt")
    output_file = os.path.join(base_dir, "results.jsonl")

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(lines)} queries from input.txt...")
    results = []

    for i, line in enumerate(lines, 1):
        payload = {"query": line}
        response = client.post("/v1/troubleshoot", json=payload)
        if response.status_code == 200:
            result_json = response.json()
            results.append(result_json)
            hit_str = "CACHE HIT" if result_json["meta"]["cache_hit"] else "CACHE MISS"
            print(f"[{i}/{len(lines)}] {hit_str} ({result_json['meta']['latency_ms']} ms): {line[:50]}...")
        else:
            print(f"[{i}/{len(lines)}] Error {response.status_code}: {response.text}")

    with open(output_file, "w", encoding="utf-8") as f:
        for res in results:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")

    print(f"\n[Success] Generated {len(results)} serialized results into {output_file}")


if __name__ == "__main__":
    generate_results()

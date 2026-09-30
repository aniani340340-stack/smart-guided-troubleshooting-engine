"""End-to-end API test suite using FastAPI TestClient.
Tests GET /health, POST /v1/troubleshoot with cache hit, cold path, and fallback cases.
"""
import os
import sys
import json
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from theme02_troubleshooting_engine.api.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("[PASS] GET /health returns 200 {'status': 'ok'}")


def test_troubleshoot_cache_hit():
    payload = {
        "query": "My Galaxy S22 screen turns completely blank or white and no text appears"
    }
    response = client.post("/v1/troubleshoot", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["meta"]["cache_hit"] is True
    assert data["meta"]["latency_ms"] < 300
    assert len(data["query_variations"]) >= 8
    assert len(data["response"]["contexts"]) == 1
    
    ctx = data["response"]["contexts"][0]
    assert ctx["goal"].startswith("Follow these steps to perform this ")
    assert 2 <= len(ctx["title"].split()) <= 3
    assert len(ctx["actions"]) > 0
    
    # Verify description constraint: 5 to 7 words starting with "It will"
    for action in ctx["actions"]:
        words = action["description"].split()
        assert 5 <= len(words) <= 7, f"Description word count fail: {action['description']}"
        assert words[0] == "It" and words[1] == "will"
        
    print(f"[PASS] POST /v1/troubleshoot (Cache Hit) in {data['meta']['latency_ms']} ms")


def test_troubleshoot_cold_path_with_siis():
    payload = {
        "query": "device display flickers when opening gallery",
        "siis_response": {
            "title": "Display flicker settings",
            "content": "## Step 1: Adjust Motion Smoothness\nNavigate to Settings. Tap Display. Select Motion smoothness and choose Standard.\n## Step 2: Restart Device\nPress and hold the Power and Volume down buttons."
        }
    }
    response = client.post("/v1/troubleshoot", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["response"]["contexts"]) == 1
    
    ctx = data["response"]["contexts"][0]
    # Verify category ordering: auto before critical
    categories = [a["category"] for a in ctx["actions"]]
    if "critical" in categories and "auto" in categories:
        assert categories.index("auto") < categories.index("critical")
        
    print(f"[PASS] POST /v1/troubleshoot (Cold Path) in {data['meta']['latency_ms']} ms")


def test_troubleshoot_fallback_no_match():
    payload = {
        "query": "completely unknown alien spaceship quantum engine problem xyz123"
    }
    response = client.post("/v1/troubleshoot", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["response"]["contexts"]) == 0
    assert data["meta"]["fallback"] == "no_match"
    print("[PASS] POST /v1/troubleshoot (Fallback no_match) handled gracefully")


if __name__ == "__main__":
    print("=" * 50)
    print(" Running REST API Contract Test Suite")
    print("=" * 50)
    test_health()
    test_troubleshoot_cache_hit()
    test_troubleshoot_cold_path_with_siis()
    test_troubleshoot_fallback_no_match()
    print("=" * 50)
    print(" ALL 4 API TESTS PASSED SUCCESSFULLY!")
    print("=" * 50)

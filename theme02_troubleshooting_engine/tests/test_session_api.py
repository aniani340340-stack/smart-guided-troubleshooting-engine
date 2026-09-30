"""Integration tests for Interactive Session REST API endpoints.
Verifies /v1/session/start, /v1/session/{id}/feedback, /v1/session/{id}/simulate-validation,
and backward compatibility with /v1/troubleshoot.
"""
import pytest
from fastapi.testclient import TestClient

from theme02_troubleshooting_engine.api.app import app

client = TestClient(app)


def test_session_start_success():
    payload = {
        "query": "My Galaxy S22 screen turns completely blank or white and no text appears",
        "device_model": "Galaxy S22 Ultra",
        "os_version": "One UI 6.1"
    }
    response = client.post("/v1/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "session_id" in data
    assert data["status"] == "ACTIVE"
    assert "diagnosis" in data
    assert "current_step" in data
    assert data["current_step"] is not None
    assert "progress" in data
    assert data["progress"]["current"] == 1
    assert data["progress"]["total"] >= 1


def test_session_start_empty_query_400():
    response = client.post("/v1/session/start", json={"query": "   "})
    assert response.status_code == 400


def test_session_get_state():
    # Start session
    start_res = client.post("/v1/session/start", json={"query": "Screen flickers and battery dies fast"})
    sid = start_res.json()["session_id"]

    get_res = client.get(f"/v1/session/{sid}")
    assert get_res.status_code == 200
    s_data = get_res.json()
    assert s_data["session_id"] == sid
    assert s_data["status"] == "ACTIVE"


def test_session_feedback_lifecycle_to_resolution():
    start_res = client.post("/v1/session/start", json={"query": "My Galaxy S22 screen turns completely blank or white"})
    sid = start_res.json()["session_id"]
    total_steps = start_res.json()["progress"]["total"]

    # Iterate passing feedback until resolved
    is_resolved = False
    for step_num in range(total_steps + 2):
        fb_res = client.post(f"/v1/session/{sid}/feedback", json={"result": "passed"})
        assert fb_res.status_code == 200
        fb_data = fb_res.json()
        if fb_data["resolved"]:
            is_resolved = True
            assert fb_data["status"] == "RESOLVED"
            assert fb_data["resolution_summary"] is not None
            assert fb_data["resolution_summary"]["resolved"] is True
            break

    assert is_resolved is True


def test_session_feedback_skipped():
    start_res = client.post("/v1/session/start", json={"query": "My Galaxy S22 screen turns completely blank or white"})
    sid = start_res.json()["session_id"]

    fb_res = client.post(f"/v1/session/{sid}/feedback", json={"result": "skipped"})
    assert fb_res.status_code == 200
    assert len(fb_res.json()["completed_steps"]) == 1


def test_session_feedback_invalid_result_400():
    start_res = client.post("/v1/session/start", json={"query": "My Galaxy S22 screen turns completely blank or white"})
    sid = start_res.json()["session_id"]

    bad_fb = client.post(f"/v1/session/{sid}/feedback", json={"result": "unknown_option_xyz"})
    assert bad_fb.status_code == 400


def test_session_simulate_validation():
    start_res = client.post("/v1/session/start", json={"query": "My Galaxy S22 screen turns completely blank or white"})
    sid = start_res.json()["session_id"]

    val_res = client.post(f"/v1/session/{sid}/simulate-validation", json={})
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert "is_valid" in val_data
    assert "simulated_telemetry" in val_data


def test_session_not_found_404():
    res = client.get("/v1/session/non-existent-session-id-999")
    assert res.status_code == 404

    fb_res = client.post("/v1/session/non-existent-session-id-999/feedback", json={"result": "passed"})
    assert fb_res.status_code == 404


def test_backward_compatibility_troubleshoot_endpoint():
    """Ensures POST /v1/troubleshoot remains 100% compliant with existing contract."""
    payload = {
        "query": "My Galaxy S22 screen turns completely blank or white and no text appears"
    }
    response = client.post("/v1/troubleshoot", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["meta"]["cache_hit"] is True
    assert len(data["query_variations"]) >= 8
    assert len(data["response"]["contexts"]) == 1
    ctx = data["response"]["contexts"][0]
    assert ctx["goal"].startswith("Follow these steps to perform this ")
    assert 2 <= len(ctx["title"].split()) <= 3

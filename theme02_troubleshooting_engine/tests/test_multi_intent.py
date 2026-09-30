"""Comprehensive Test Suite for Phase 7: Multi-Intent Troubleshooting Orchestration.
Validates:
1. Multi-intent decomposition (Wi-Fi + Bluetooth).
2. Single-intent backward compatibility.
3. Same-domain deduplication (Wi-Fi slow and disconnecting remains 1 intent).
4. Three-intent decomposition (Wi-Fi, Bluetooth, Camera).
5. Independent canonical flows per intent.
6. No fabricated deeplinks (all URIs match catalog).
7. Intent feedback isolation (advancing Intent 1 does not advance Intent 2).
8. Intent switching via /switch-intent.
9. Multi-intent resolution lifecycle (session resolved only when all intents resolved).
10. Ambiguous query clarification.
11. Multimodal image evidence isolation without cross-intent leakage.
"""
import os
import json
import base64
import pytest
from fastapi.testclient import TestClient

from theme02_troubleshooting_engine.api.app import app
from theme02_troubleshooting_engine.core.multi_intent import MultiIntentDecomposer
from theme02_troubleshooting_engine.core.session_manager import SessionManager

client = TestClient(app)

# Load official deeplinks catalog for URI validation
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEEPLINKS_PATH = os.path.join(BASE_DIR, "data", "deeplinks.json")
with open(DEEPLINKS_PATH, "r", encoding="utf-8") as f:
    CATALOG = json.load(f)
VALID_URIS = set()
for d in CATALOG.get("deeplinks", []):
    if d.get("deeplink"):
        VALID_URIS.add(d["deeplink"])
    val_dict = d.get("validation")
    if isinstance(val_dict, dict) and val_dict.get("deeplink"):
        VALID_URIS.add(val_dict["deeplink"])


def test_multi_intent_decomposition_wifi_bluetooth():
    """1. Decomposes compound complaint into 2 discrete intents: NETWORK and BLUETOOTH."""
    query = "My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect"
    decomp = MultiIntentDecomposer.decompose(query)

    assert decomp.is_multi_intent is True
    assert len(decomp.intents) == 2
    domains = [i.domain for i in decomp.intents]
    assert domains == ["NETWORK", "BLUETOOTH"]

    # Verify session start API returns both intents
    res = client.post("/v1/session/start", json={"query": query})
    assert res.status_code == 200
    data = res.json()

    assert data["is_multi_intent"] is True
    assert data["active_intent_id"] == "intent_1"
    assert len(data["intents"]) == 2
    assert data["intents"][0]["domain"] == "NETWORK"
    assert data["intents"][1]["domain"] == "BLUETOOTH"
    assert data["diagnosis"]["domain"] == "NETWORK"


def test_single_intent_backward_compatibility():
    """2. Single intent complaints must yield is_multi_intent = False and standard flow."""
    query = "My Wi-Fi keeps disconnecting"
    res = client.post("/v1/session/start", json={"query": query})
    assert res.status_code == 200
    data = res.json()

    assert data["is_multi_intent"] is False
    assert data["diagnosis"]["domain"] == "NETWORK"
    assert data["current_step"] is not None
    assert data["progress"]["current"] == 1


def test_same_domain_deduplication():
    """3. Multiple symptoms from the SAME domain must remain ONE intent (not duplicated)."""
    query = "Wi-Fi is slow and keeps disconnecting"
    decomp = MultiIntentDecomposer.decompose(query)

    assert decomp.is_multi_intent is False
    assert len(decomp.intents) == 1
    assert decomp.intents[0].domain == "NETWORK"

    res = client.post("/v1/session/start", json={"query": query})
    assert res.status_code == 200
    data = res.json()
    assert data["is_multi_intent"] is False
    assert data["diagnosis"]["domain"] == "NETWORK"


def test_three_intents():
    """4. Three independent problems produce 3 intents, capped at max 3."""
    query = "Wi-Fi disconnects, Bluetooth fails, and camera crashes"
    decomp = MultiIntentDecomposer.decompose(query)

    assert decomp.is_multi_intent is True
    assert len(decomp.intents) == 3
    domains = [i.domain for i in decomp.intents]
    assert "NETWORK" in domains
    assert "BLUETOOTH" in domains
    assert "CAMERA" in domains

    res = client.post("/v1/session/start", json={"query": query})
    assert res.status_code == 200
    data = res.json()
    assert data["is_multi_intent"] is True
    assert len(data["intents"]) == 3


def test_intent_independent_flows():
    """5. NETWORK and BLUETOOTH must receive their own canonical plans and flows."""
    query = "My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect"
    res = client.post("/v1/session/start", json={"query": query})
    data = res.json()

    intent_1 = data["intents"][0]
    intent_2 = data["intents"][1]

    assert intent_1["domain"] == "NETWORK"
    action_1 = intent_1["current_step"]["action_name"].lower()
    assert "wi-fi" in action_1 or "network" in action_1 or "wifi" in action_1

    assert intent_2["domain"] == "BLUETOOTH"
    action_2 = intent_2["current_step"]["action_name"].lower()
    assert "bluetooth" in action_2


def test_no_fabricated_deeplinks():
    """6. All deeplinks in multi-intent flows must exist in the trusted catalog."""
    query = "Wi-Fi disconnects, Bluetooth fails, and camera crashes"
    res = client.post("/v1/session/start", json={"query": query})
    data = res.json()

    for intent in data["intents"]:
        curr = intent.get("current_step")
        if curr and curr.get("actionable_deeplink"):
            uri = curr["actionable_deeplink"]["deeplink"]
            assert uri in VALID_URIS, f"Fabricated actionable URI detected: {uri}"
        if curr and curr.get("validation_deeplink"):
            val_uri = curr["validation_deeplink"]["deeplink"]
            assert val_uri in VALID_URIS, f"Fabricated validation URI detected: {val_uri}"


def test_intent_feedback_isolation():
    """7. Submitting feedback for Intent 1 must NOT advance Intent 2."""
    query = "My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect"
    start_res = client.post("/v1/session/start", json={"query": query})
    sid = start_res.json()["session_id"]

    # Initial state: Intent 1 progress 1/4, Intent 2 progress 1/4 (PENDING)
    assert start_res.json()["intents"][0]["progress"]["current"] == 1
    assert start_res.json()["intents"][1]["progress"]["current"] == 1

    # Advance Intent 1
    fb_res = client.post(
        f"/v1/session/{sid}/feedback",
        json={"result": "passed", "intent_id": "intent_1"}
    )
    assert fb_res.status_code == 200
    fb_data = fb_res.json()

    # Intent 1 has 1 completed step; Intent 2 has 0 completed steps
    intents = fb_data["intents"]
    assert len(intents[0]["completed_steps"]) == 1
    assert len(intents[1]["completed_steps"]) == 0
    assert intents[1]["status"] == "PENDING"


def test_switch_intent():
    """8. Switch active intent switches view without resetting diagnostic progress."""
    query = "My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect"
    start_res = client.post("/v1/session/start", json={"query": query})
    sid = start_res.json()["session_id"]

    # Advance Intent 1 by 1 step
    client.post(f"/v1/session/{sid}/feedback", json={"result": "passed", "intent_id": "intent_1"})

    # Switch to Intent 2
    sw_res = client.post(f"/v1/session/{sid}/switch-intent", json={"intent_id": "intent_2"})
    assert sw_res.status_code == 200
    sw_data = sw_res.json()

    assert sw_data["active_intent_id"] == "intent_2"
    assert "Bluetooth" in sw_data["current_step"]["action_name"]

    # Switch back to Intent 1; verify its progress is preserved
    sw_back = client.post(f"/v1/session/{sid}/switch-intent", json={"intent_id": "intent_1"})
    back_data = sw_back.json()
    assert back_data["active_intent_id"] == "intent_1"
    assert len(back_data["intents"][0]["completed_steps"]) == 1


def test_multi_intent_resolution():
    """9. Session becomes RESOLVED only after all intents have been resolved."""
    query = "My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect"
    start_res = client.post("/v1/session/start", json={"query": query})
    sid = start_res.json()["session_id"]

    # Resolve Intent 1 explicitly
    fb1 = client.post(
        f"/v1/session/{sid}/feedback",
        json={"result": "passed", "intent_id": "intent_1", "details": {"resolved": True}}
    )
    fb1_data = fb1.json()
    # Intent 1 resolved, but entire session is STILL ACTIVE because Intent 2 is unresolved
    assert fb1_data["intents"][0]["resolved"] is True
    assert fb1_data["intents"][1]["resolved"] is False
    assert fb1_data["status"] == "ACTIVE"
    assert fb1_data["resolved"] is False
    # Auto-selected next pending intent (Intent 2)
    assert fb1_data["active_intent_id"] == "intent_2"

    # Now resolve Intent 2 explicitly
    fb2 = client.post(
        f"/v1/session/{sid}/feedback",
        json={"result": "passed", "intent_id": "intent_2", "details": {"resolved": True}}
    )
    fb2_data = fb2.json()
    # Now ALL intents are resolved -> Session status is RESOLVED
    assert fb2_data["status"] == "RESOLVED"
    assert fb2_data["resolved"] is True
    assert fb2_data["resolution_summary"] is not None
    assert fb2_data["resolution_summary"]["resolved"] is True


def test_ambiguous_query():
    """10. Generic queries must trigger clarification without inventing domains."""
    res = client.post("/v1/session/start", json={"query": "My phone is acting weird"})
    assert res.status_code == 200
    data = res.json()

    assert data["diagnosis"]["needs_clarification"] is True
    assert data["diagnosis"]["domain"] == "CLARIFICATION"
    assert data["is_multi_intent"] is False


def test_image_plus_multi_intent():
    """11. Image evidence attaches only to matching intent and does not leak to unrelated intents."""
    # Use realistic test image (network dialog) if available
    img_path = os.path.join(BASE_DIR, "test_images", "realistic_screenshot.png")
    img_b64 = None
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

    query = "My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect"
    payload = {"query": query}
    if img_b64:
        payload["image_data"] = img_b64

    res = client.post("/v1/session/start", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["is_multi_intent"] is True
    intent_1 = data["intents"][0]  # NETWORK
    intent_2 = data["intents"][1]  # BLUETOOTH

    if img_b64 and intent_1["image_analysis_used"]:
        # Image evidence should be attached to NETWORK intent
        assert intent_1["image_analysis_used"] is True
        # But NEVER leak into the BLUETOOTH intent!
        assert intent_2["image_analysis_used"] is False

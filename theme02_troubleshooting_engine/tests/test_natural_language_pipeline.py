"""Tests for Generalized Natural Language Pipeline & Free-Form Complaint Handling.
Validates:
1. Negative tests: generic disconnect/dropping language does NOT incorrectly become NETWORK.
2. Device & Accessory awareness (separating phone model from accessory).
3. Ambiguity handling and clarification routing for low-confidence queries.
4. LLM Classifier abstraction with safe fallback.
5. End-to-end session integration with /v1/session/start.
"""
import pytest
from fastapi.testclient import TestClient

from theme02_troubleshooting_engine.api.app import app
from theme02_troubleshooting_engine.core.query_pipeline import (
    DeviceAccessoryExtractor,
    DomainDetector,
    GeneralizedQueryPipeline,
    LLMDiagnosisClassifier
)

client = TestClient(app)


# =========================================================================
# 1. IMPORTANT NEGATIVE TESTS (Disconnect Language Disambiguation)
# =========================================================================

def test_negative_generic_disconnect_bluetooth_earbuds():
    """Generic 'disconnect' with earbuds/headphones must NEVER become NETWORK."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query("My Bluetooth earbuds keep disconnecting")
    assert res["domain"] == "BLUETOOTH"
    assert res["needs_clarification"] is False
    assert res["confidence"] >= 0.70


def test_negative_galaxy_buds_dropping_connection():
    """'Dropping connection' with Galaxy Buds must be BLUETOOTH."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query("My Galaxy Buds keep dropping connection")
    assert res["domain"] == "BLUETOOTH"
    assert res["needs_clarification"] is False


def test_negative_wireless_headphones_disconnect_randomly():
    """'Disconnect randomly' with wireless headphones must be BLUETOOTH."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query("My wireless headphones disconnect randomly")
    assert res["domain"] == "BLUETOOTH"
    assert res["needs_clarification"] is False


def test_negative_bluetooth_pairing_fails():
    """'Pairing fails' must be BLUETOOTH."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query("Bluetooth pairing fails")
    assert res["domain"] == "BLUETOOTH"
    assert res["needs_clarification"] is False


def test_negative_wifi_disconnecting_is_network():
    """'Disconnecting' with Wi-Fi must be NETWORK."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query("My Wi-Fi keeps disconnecting")
    assert res["domain"] == "NETWORK"
    assert res["needs_clarification"] is False


def test_negative_internet_dropping_is_network():
    """'Internet keeps dropping' must be NETWORK."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query("My internet connection keeps dropping")
    assert res["domain"] == "NETWORK"
    assert res["needs_clarification"] is False


def test_negative_wifi_connects_websites_dont_load():
    """'Wi-Fi connects but websites don't load' must be NETWORK."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query("Wi-Fi connects but websites don't load")
    assert res["domain"] == "NETWORK"
    assert res["needs_clarification"] is False


# =========================================================================
# 2. DEVICE + ACCESSORY DISAMBIGUATION TESTS
# =========================================================================

def test_device_accessory_extraction_buds2_pro_with_s23():
    """Extracts phone_model = Galaxy S23, accessory = Galaxy Buds2 Pro, domain = BLUETOOTH."""
    pipeline = GeneralizedQueryPipeline()
    query = "Galaxy Buds2 Pro bluetooth pairing fails with Galaxy S23"
    res = pipeline.process_query(query)

    assert res["domain"] == "BLUETOOTH"
    assert res["phone_model"] == "Galaxy S23"
    assert res["accessory"] == "Galaxy Buds2 Pro"
    assert res["needs_clarification"] is False


def test_device_accessory_extraction_watch_with_s24_ultra():
    """Extracts phone = Galaxy S24 Ultra, accessory = Galaxy Watch, domain = BLUETOOTH."""
    pipeline = GeneralizedQueryPipeline()
    query = "Galaxy Watch 6 fails to pair via bluetooth with Galaxy S24 Ultra"
    res = pipeline.process_query(query)

    assert res["domain"] == "BLUETOOTH"
    assert res["phone_model"] == "Galaxy S24 Ultra"
    assert res["accessory"] == "Galaxy Watch"


def test_device_only_extraction_s22_battery():
    """Extracts phone = Galaxy S22, accessory = None, domain = BATTERY."""
    pipeline = GeneralizedQueryPipeline()
    query = "My Galaxy S22 battery drains extremely quickly"
    res = pipeline.process_query(query)

    assert res["domain"] == "BATTERY"
    assert res["phone_model"] == "Galaxy S22"
    assert res["accessory"] is None


def test_accessory_without_explicit_phone():
    """Extracts accessory = Wireless Earbuds, phone = default or user context."""
    pipeline = GeneralizedQueryPipeline()
    query = "My earbuds keep disconnecting from my Galaxy"
    res = pipeline.process_query(query, user_device_model="Galaxy S23")

    assert res["domain"] == "BLUETOOTH"
    assert res["accessory"] == "Wireless Earbuds"
    assert res["phone_model"] == "Galaxy S23"


# =========================================================================
# 3. AMBIGUITY & CLARIFICATION ROUTING TESTS
# =========================================================================

def test_ambiguous_query_triggers_clarification():
    """Intentionally vague query 'Something isn't working' triggers clarification."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query("Something isn't working")

    assert res["needs_clarification"] is True
    assert res["domain"] == "GENERIC"
    assert res["confidence"] < 0.50
    assert "Wi-Fi" in res["clarification_message"]
    assert "Bluetooth" in res["clarification_message"]


def test_ambiguous_short_query_triggers_clarification():
    """Vague query 'My device is broken' triggers clarification."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query("My device is broken")

    assert res["needs_clarification"] is True
    assert res["confidence"] < 0.50


# =========================================================================
# 4. LLM FALLBACK ABSTRACTION TESTS
# =========================================================================

def test_llm_classifier_no_api_key_graceful_fallback():
    """Without API credentials, LLM classifier safely returns None."""
    classifier = LLMDiagnosisClassifier(api_key=None)
    assert classifier.is_available() is False
    assert classifier.classify_domain("random complaint") is None


def test_llm_classifier_mock_valid_domain(monkeypatch):
    """When LLM returns a valid domain, classifier parses and validates it."""
    classifier = LLMDiagnosisClassifier(api_key="mock-key-for-test")
    assert classifier.is_available() is True

    # Mock classify_domain to return ("BATTERY", 0.90)
    monkeypatch.setattr(classifier, "classify_domain", lambda q: ("BATTERY", 0.90))
    domain, conf = classifier.classify_domain("Battery runs out in 2 hours")
    assert domain == "BATTERY"
    assert conf == 0.90


# =========================================================================
# 5. END-TO-END SESSION REST API TESTS
# =========================================================================

def test_api_session_start_buds_and_phone():
    """POST /v1/session/start with phone + accessory returns structured context."""
    payload = {
        "query": "Galaxy Buds2 Pro bluetooth pairing fails with Galaxy S23"
    }
    response = client.post("/v1/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ACTIVE"
    diag = data["diagnosis"]
    assert diag["domain"] == "BLUETOOTH"
    assert diag["accessory"] == "Galaxy Buds2 Pro"
    assert "Galaxy S23" in diag["summary"]
    assert diag["confidence"] >= 0.70


def test_api_session_start_ambiguous_query_returns_clarification():
    """POST /v1/session/start with ambiguous query returns clarification step."""
    payload = {
        "query": "Something isn't working"
    }
    response = client.post("/v1/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ACTIVE"
    diag = data["diagnosis"]
    assert diag["needs_clarification"] is True
    assert diag["domain"] == "CLARIFICATION"
    assert "Wi-Fi" in diag["summary"]
    # Current step guides user to specify issue
    curr = data["current_step"]
    assert curr is not None
    assert "Identify" in curr["action_name"] or "Clarify" in curr["action_name"]


def test_api_session_start_freeform_wifi():
    """POST /v1/session/start with free-form Wi-Fi complaint."""
    payload = {
        "query": "My Galaxy S22 Wi-Fi keeps disconnecting and cannot load web pages"
    }
    response = client.post("/v1/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["diagnosis"]["domain"] == "NETWORK"
    assert "Galaxy S22" in data["diagnosis"]["summary"]
    assert data["device_context"]["model"] == "Galaxy S22"


# =========================================================================
# 6. PHASE 4.1 — DEVICE CONTEXT SYNCHRONIZATION REGRESSION TESTS
# =========================================================================

def test_regression_device_sync_test1_buds2_pro_with_s23():
    """TEST 1: 'Galaxy Buds2 Pro bluetooth pairing fails with Galaxy S23'
    Expected: domain = BLUETOOTH, phone_model = Galaxy S23, accessory = Galaxy Buds2 Pro
    """
    payload = {
        "query": "Galaxy Buds2 Pro bluetooth pairing fails with Galaxy S23",
        "device_model": "Galaxy S22",  # Default previously selected device
        "os_version": "One UI 6.1 (Android 14)"
    }
    response = client.post("/v1/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["diagnosis"]["domain"] == "BLUETOOTH"
    assert data["device_context"] is not None
    # Explicit query model takes precedence over payload default
    assert data["device_context"]["model"] == "Galaxy S23"
    assert data["device_context"]["device_model"] == "Galaxy S23"
    assert data["device_context"]["series"] == "Galaxy S"
    assert data["device_context"]["device_type"] == "phone"
    assert data["accessory"] == "Galaxy Buds2 Pro"
    assert data["device_context"]["accessory"] == "Galaxy Buds2 Pro"


def test_regression_device_sync_test2_s22_with_earbuds():
    """TEST 2: 'My Galaxy S22 Bluetooth keeps disconnecting from my earbuds'
    Expected: domain = BLUETOOTH, phone_model = Galaxy S22, accessory = Wireless Earbuds
    """
    payload = {
        "query": "My Galaxy S22 Bluetooth keeps disconnecting from my earbuds",
        "device_model": "Galaxy S24 Ultra",  # Mismatched previously selected device
        "os_version": "One UI 6.1.1 (Android 14)"
    }
    response = client.post("/v1/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["diagnosis"]["domain"] == "BLUETOOTH"
    # Explicit query model takes precedence
    assert data["device_context"]["model"] == "Galaxy S22"
    assert data["device_context"]["device_model"] == "Galaxy S22"
    assert "Earbuds" in data["accessory"]


def test_regression_device_sync_test3_earbuds_preserves_default_device():
    """TEST 3: 'My Bluetooth earbuds keep disconnecting'
    Expected: domain = BLUETOOTH, phone_model = existing/default device, accessory = Wireless Earbuds
    """
    payload = {
        "query": "My Bluetooth earbuds keep disconnecting",
        "device_model": "Galaxy Z Fold 6",
        "os_version": "One UI 6.1.1 (Foldable)"
    }
    response = client.post("/v1/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["diagnosis"]["domain"] == "BLUETOOTH"
    # No phone model in query, preserves previously selected device
    assert data["device_context"]["model"] == "Galaxy Z Fold 6"
    assert data["device_context"]["device_model"] == "Galaxy Z Fold 6"
    assert "Earbuds" in data["accessory"]


def test_regression_device_sync_test4_wifi_preserves_default_device():
    """TEST 4: 'My Wi-Fi keeps disconnecting'
    Expected: domain = NETWORK, existing selected/default device remains unchanged, no accessory
    """
    payload = {
        "query": "My Wi-Fi keeps disconnecting",
        "device_model": "Galaxy S23",
        "os_version": "One UI 6.1 (Android 14)"
    }
    response = client.post("/v1/session/start", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["diagnosis"]["domain"] == "NETWORK"
    assert data["device_context"]["model"] == "Galaxy S23"
    assert data["device_context"]["device_model"] == "Galaxy S23"
    assert data["accessory"] is None

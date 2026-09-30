"""Phase 5 Tests: Controlled LLM Fallback for Uncertain Query Classification.
Verifies:
1. Safe structured JSON response validation (clamp confidence, supported domains enum)
2. Mandatory diagnosis validator checks (rejection of malicious/incompatible LLM domains)
3. Deterministic precedence (LLM NEVER overrides strong deterministic anchors)
4. Graceful handling of missing API keys, timeouts, network errors, and malformed outputs
5. Zero latency regression (high-confidence queries skip the LLM entirely)
6. Device and accessory context injection into LLM prompt
7. Accurate classification of difficult/ambiguous natural-language complaints
"""
import pytest
import json
from fastapi.testclient import TestClient

from theme02_troubleshooting_engine.core.query_pipeline import (
    GeneralizedQueryPipeline,
    LLMDiagnosisClassifier,
    LLMClassificationResult
)
from theme02_troubleshooting_engine.core.diagnosis_validator import (
    validate_llm_classification,
    classify_text_domain
)
from theme02_troubleshooting_engine.api.app import app

client = TestClient(app)


# =========================================================================
# 1. STRUCTURED OUTPUT PARSING & CLAMPING TESTS
# =========================================================================

def test_llm_no_api_key_graceful():
    """Classifier without API key or mock returns unavailable and None."""
    classifier = LLMDiagnosisClassifier(api_key=None)
    assert classifier.is_available() is False
    assert classifier.classify_domain("any query") is None


def test_llm_structured_output_parsing_clean_json():
    """Valid structured JSON parses domain, clamped confidence, and reason."""
    classifier = LLMDiagnosisClassifier(api_key="mock_key")
    raw = json.dumps({
        "domain": "BLUETOOTH",
        "confidence": 0.875,
        "reason": "The complaint explicitly describes Bluetooth earbuds losing connection."
    })
    result = classifier.parse_and_validate_response(raw)
    assert result is not None
    assert result.domain == "BLUETOOTH"
    assert result["domain"] == "BLUETOOTH"
    assert result.confidence == 0.88
    assert "earbuds" in result.reason
    # Backward compatible tuple unpacking
    domain, conf = result
    assert domain == "BLUETOOTH"
    assert conf == 0.88


def test_llm_structured_output_markdown_fences():
    """Handles markdown ```json ... ``` code blocks cleanly."""
    classifier = LLMDiagnosisClassifier(api_key="mock_key")
    raw = "```json\n{\n  \"domain\": \"NETWORK\",\n  \"confidence\": 0.92,\n  \"reason\": \"Wi-Fi dropping\"\n}\n```"
    result = classifier.parse_and_validate_response(raw)
    assert result is not None
    assert result.domain == "NETWORK"
    assert result.confidence == 0.92


def test_llm_malformed_json_rejected():
    """Malformed non-JSON strings are safely rejected without throwing."""
    classifier = LLMDiagnosisClassifier(api_key="mock_key")
    assert classifier.parse_and_validate_response("This is not JSON at all") is None
    assert classifier.parse_and_validate_response("{incomplete: json") is None
    assert classifier.parse_and_validate_response("") is None
    assert classifier.parse_and_validate_response(None) is None


def test_llm_unsupported_domain_rejected():
    """Arbitrary diagnosis text or unsupported domain names are rejected."""
    classifier = LLMDiagnosisClassifier(api_key="mock_key")
    # Unsupported technical category
    raw1 = json.dumps({"domain": "PRINTER_SETUP", "confidence": 0.90})
    assert classifier.parse_and_validate_response(raw1) is None

    # Arbitrary text instead of supported domain enum
    raw2 = json.dumps({"domain": "Reboot the Galaxy device to restore normal operation", "confidence": 0.85})
    assert classifier.parse_and_validate_response(raw2) is None


def test_llm_invalid_confidence_values():
    """Confidence values must be numeric in [0.0, 1.0] and not booleans."""
    classifier = LLMDiagnosisClassifier(api_key="mock_key")

    # Boolean is rejected
    raw_bool = json.dumps({"domain": "BATTERY", "confidence": True})
    assert classifier.parse_and_validate_response(raw_bool) is None

    # Negative is rejected
    raw_neg = json.dumps({"domain": "BATTERY", "confidence": -0.2})
    assert classifier.parse_and_validate_response(raw_neg) is None

    # Greater than 1.0 is rejected
    raw_high = json.dumps({"domain": "BATTERY", "confidence": 1.5})
    assert classifier.parse_and_validate_response(raw_high) is None

    # String is rejected
    raw_str = json.dumps({"domain": "BATTERY", "confidence": "high"})
    assert classifier.parse_and_validate_response(raw_str) is None


def test_llm_unknown_mapped_to_generic():
    """'UNKNOWN' returned by LLM is normalized to 'GENERIC'."""
    classifier = LLMDiagnosisClassifier(api_key="mock_key")
    raw = json.dumps({"domain": "UNKNOWN", "confidence": 0.20, "reason": "No technical subsystem"})
    result = classifier.parse_and_validate_response(raw)
    assert result is not None
    assert result.domain == "GENERIC"
    assert result.confidence == 0.20


# =========================================================================
# 2. MANDATORY VALIDATOR & DETERMINISTIC PRECEDENCE TESTS
# =========================================================================

def test_validator_rejects_llm_overriding_strong_deterministic_signal():
    """The LLM must NEVER override a stronger deterministic domain signal."""
    query = "My Bluetooth earbuds keep disconnecting"
    # Query has explicit Bluetooth anchors (conf >= 0.80)
    # LLM incorrectly returns NETWORK
    is_valid, reason = validate_llm_classification(
        query=query,
        llm_domain="NETWORK",
        deterministic_domain="BLUETOOTH",
        deterministic_confidence=0.98
    )
    assert is_valid is False
    assert "rejected" in reason.lower()
    assert "bluetooth" in reason.lower()


def test_validator_rejects_incompatible_query_domain_anchors():
    """Validator rejects LLM classification if query explicitly mentions an incompatible subsystem."""
    query = "My Wi-Fi keeps dropping every few minutes"
    # LLM incorrectly attempts to return EMAIL
    is_valid, reason = validate_llm_classification(
        query=query,
        llm_domain="EMAIL",
        deterministic_domain="NETWORK",
        deterministic_confidence=0.85
    )
    assert is_valid is False
    assert "incompatible" in reason.lower() or "rejected" in reason.lower()


def test_validator_approves_safe_candidate():
    """Validator approves LLM classification when semantically consistent with query."""
    query = "The phone can connect to the access point but nothing loads"
    is_valid, reason = validate_llm_classification(
        query=query,
        llm_domain="NETWORK",
        deterministic_domain="GENERIC",
        deterministic_confidence=0.0
    )
    assert is_valid is True
    assert "validated" in reason.lower()


# =========================================================================
# 3. FAST-PATH & LATENCY REGRESSION PREVENTION TESTS
# =========================================================================

def test_no_latency_regression_for_high_confidence_deterministic_query():
    """High-confidence deterministic queries must NEVER invoke the LLM classifier."""
    call_tracker = {"called": False}

    def mock_llm_caller(prompt):
        call_tracker["called"] = True
        return json.dumps({"domain": "NETWORK", "confidence": 0.95})

    classifier = LLMDiagnosisClassifier(client_fn=mock_llm_caller)
    pipeline = GeneralizedQueryPipeline()
    pipeline.llm_classifier = classifier

    # High-confidence query with clear deterministic anchors
    res = pipeline.process_query("My Galaxy S22 Wi-Fi keeps disconnecting")
    assert res["domain"] == "NETWORK"
    assert res["confidence"] >= 0.80
    assert res["matched_via"] != "llm"
    assert res["ai_fallback_used"] is False
    # LLM was NOT called
    assert call_tracker["called"] is False


def test_llm_invoked_only_when_deterministic_confidence_is_insufficient():
    """When query is ambiguous or lacks strong anchors, LLM fallback is invoked."""
    call_tracker = {"called": False}

    def mock_llm_caller(prompt):
        call_tracker["called"] = True
        return json.dumps({
            "domain": "DISPLAY",
            "confidence": 0.85,
            "reason": "Complaint describes digitizer glass unresponsiveness"
        })

    classifier = LLMDiagnosisClassifier(client_fn=mock_llm_caller)
    pipeline = GeneralizedQueryPipeline()
    pipeline.llm_classifier = classifier

    # Colloquial complaint without standard keywords in DOMAIN_ANCHORS
    res = pipeline.process_query("I tap on an app icon but nothing happens on the glass panel")
    assert call_tracker["called"] is True
    assert res["domain"] == "DISPLAY"
    assert res["matched_via"] == "llm"
    assert res["ai_fallback_used"] is True
    assert res["confidence"] >= 0.65


# =========================================================================
# 4. ERROR & TIMEOUT RESILIENCE TESTS
# =========================================================================

def test_llm_timeout_handled_gracefully():
    """If LLM call times out or raises an exception, system falls back safely without crashing."""
    def timeout_mock(prompt):
        raise TimeoutError("LLM API request timed out after 3.0s")

    classifier = LLMDiagnosisClassifier(client_fn=timeout_mock)
    pipeline = GeneralizedQueryPipeline()
    pipeline.llm_classifier = classifier

    # Should not throw exception
    res = pipeline.process_query("Something is wrong with my device")
    assert res is not None
    assert res["needs_clarification"] is True
    assert res["domain"] == "GENERIC"


# =========================================================================
# 5. CONTEXT INJECTION TESTS
# =========================================================================

def test_device_and_accessory_context_injected_in_prompt():
    """Extracted device and accessory are passed into LLM prompt as context."""
    received_prompt = {"text": ""}

    def capture_prompt(prompt):
        received_prompt["text"] = prompt
        return json.dumps({"domain": "BLUETOOTH", "confidence": 0.90, "reason": "Audio accessory issue"})

    classifier = LLMDiagnosisClassifier(client_fn=capture_prompt)
    pipeline = GeneralizedQueryPipeline()
    pipeline.llm_classifier = classifier

    # Query with ambiguous wording where context is injected into LLM fallback
    pipeline.process_query(
        "The peripheral will not communicate with my unit",
        user_device_model="Galaxy S23",
        user_os_version="One UI 6.1"
    )
    assert 'Galaxy S23' in received_prompt["text"]
    assert 'Phone="Galaxy S23"' in received_prompt["text"]


# =========================================================================
# 6. NATURAL LANGUAGE FALLBACK EXAMPLES (SPECIFICATION TEST 10)
# =========================================================================

@pytest.mark.parametrize("query,expected_domain,should_need_clarification", [
    ("Everything was fine yesterday but now the phone can't talk to my buds", "BLUETOOTH", False),
    ("The phone joins the network but nothing online opens", "NETWORK", False),
    ("My display suddenly went dark but the phone still vibrates", "DISPLAY", False),
    ("My phone loses charge much faster than before", "BATTERY", False),
    ("The camera app opens but taking photos fails", "CAMERA", False),
    ("Something is wrong", "GENERIC", True),
])
def test_fallback_natural_language_queries(query, expected_domain, should_need_clarification):
    """Verifies challenging natural language queries resolve accurately to expected domain."""
    pipeline = GeneralizedQueryPipeline()
    res = pipeline.process_query(query)
    assert res["domain"] == expected_domain
    assert res["needs_clarification"] == should_need_clarification


# =========================================================================
# 7. END-TO-END REST API SESSION METADATA TEST
# =========================================================================

def test_api_session_ai_fallback_metadata_propagation(monkeypatch):
    """Session start API propagates ai_fallback_used and matched_via metadata."""
    def mock_classify(query, phone_model=None, accessory=None):
        return LLMClassificationResult(
            domain="DISPLAY",
            confidence=0.88,
            reason="User describes display backlight anomaly"
        )

    # Patch pipeline llm_classifier in the running app
    from theme02_troubleshooting_engine.api import app as api_module
    monkeypatch.setattr(api_module.query_pipeline.llm_classifier, "is_available", lambda: True)
    monkeypatch.setattr(api_module.query_pipeline.llm_classifier, "classify_domain", mock_classify)

    # Query with no keyword anchors
    response = client.post("/v1/session/start", json={
        "query": "The glass panel stays black even though device vibrates",
        "device_model": "Galaxy S23"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert data["diagnosis"]["domain"] == "DISPLAY"
    assert data["diagnosis"]["matched_via"] == "llm"
    assert data["diagnosis"]["ai_fallback_used"] is True
    assert data["ai_fallback_used"] is True

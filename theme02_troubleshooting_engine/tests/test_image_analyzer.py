"""Comprehensive Unit & Multimodal Integration Tests for Image & Error-Code Intelligence.
Tests:
- Input decoding & format validation (PNG, JPEG, WEBP, size limits, corrupted data)
- Security checks: MIME rejection, 5MB limit enforcement, in-memory processing
- Structured evidence extraction: text, error codes, detected domains, visual clues
- Multimodal text + image fusion and evidence priority
- Text-only regression (fast path unharmed, zero image processing overhead)
- Known and unknown error-code mapping integrity
"""
import io
import json
import base64
import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from theme02_troubleshooting_engine.core.image_analyzer import (
    ImageAnalyzer,
    ImageValidationError,
    MAX_IMAGE_SIZE_BYTES
)
from theme02_troubleshooting_engine.core.query_pipeline import GeneralizedQueryPipeline
from theme02_troubleshooting_engine.api.app import app

client = TestClient(app)


# Helper to generate in-memory synthetic test images
def make_synthetic_image(fmt="PNG", size=(200, 200), color=(50, 100, 200)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


# =========================================================================
# 1. IMAGE VALIDATION & SECURITY TESTS
# =========================================================================

def test_validate_valid_images():
    """Valid PNG, JPEG, and WEBP formats validate with dimensions."""
    analyzer = ImageAnalyzer()

    for fmt in ["PNG", "JPEG", "WEBP"]:
        raw = make_synthetic_image(fmt=fmt)
        detected_fmt, (w, h) = analyzer.validate_image_bytes(raw)
        assert detected_fmt in ["PNG", "JPEG", "WEBP"]
        assert w == 200 and h == 200


def test_reject_empty_image():
    """Empty byte payload is rejected immediately."""
    analyzer = ImageAnalyzer()
    with pytest.raises(ImageValidationError, match="Empty image file"):
        analyzer.validate_image_bytes(b"")


def test_reject_oversized_image():
    """Images exceeding 5 MB are rejected for security and memory safety."""
    analyzer = ImageAnalyzer()
    fake_huge_bytes = b"0" * (MAX_IMAGE_SIZE_BYTES + 1024)
    with pytest.raises(ImageValidationError, match="exceeds the maximum limit"):
        analyzer.validate_image_bytes(fake_huge_bytes)


def test_reject_unsupported_mime():
    """Unsupported MIME types (e.g. GIF, PDF) are rejected."""
    analyzer = ImageAnalyzer()
    raw = make_synthetic_image("PNG")
    with pytest.raises(ImageValidationError, match="Unsupported image MIME"):
        analyzer.validate_image_bytes(raw, mime_type="application/pdf")


def test_reject_corrupt_image_bytes():
    """Corrupted binary streams that cannot be decoded by PIL are rejected."""
    analyzer = ImageAnalyzer()
    with pytest.raises(ImageValidationError, match="Corrupt or unreadable"):
        analyzer.validate_image_bytes(b"NOT_A_VALID_IMAGE_FILE_HEADER")


def test_decode_base64_data_url():
    """Decodes data:image/png;base64,... URLs into raw bytes and mime."""
    analyzer = ImageAnalyzer()
    raw = make_synthetic_image("PNG")
    b64 = base64.b64encode(raw).decode("utf-8")
    data_url = f"data:image/png;base64,{b64}"

    decoded_bytes, mime = analyzer.decode_input(data_url)
    assert decoded_bytes == raw
    assert mime == "image/png"


# =========================================================================
# 2. EVIDENCE EXTRACTION TESTS (SPECIFICATION TESTS 1 - 4 & 7)
# =========================================================================

def test_evidence_bluetooth_error():
    """TEST 1: Image containing 'Bluetooth pairing failed' detects BLUETOOTH domain."""
    def mock_vision(image_bytes, mime):
        return {
            "extracted_text": "Bluetooth pairing failed. Make sure your Galaxy Buds are in pairing mode.",
            "error_codes": [],
            "detected_domains": ["BLUETOOTH"],
            "visual_clues": ["Bluetooth connection error dialog"],
            "confidence": 0.92
        }

    analyzer = ImageAnalyzer(vision_fn=mock_vision)
    raw_img = make_synthetic_image("PNG")
    evidence = analyzer.analyze_image(raw_img)

    assert evidence["success"] is True
    assert "Bluetooth pairing failed" in evidence["extracted_text"]
    assert "BLUETOOTH" in evidence["detected_domains"]
    assert evidence["confidence"] >= 0.90


def test_evidence_wifi_error():
    """TEST 2: Image containing 'Unable to connect to Wi-Fi' detects NETWORK domain."""
    def mock_vision(image_bytes, mime):
        return {
            "extracted_text": "Unable to connect to Wi-Fi. IP configuration failure.",
            "error_codes": [],
            "detected_domains": ["NETWORK"],
            "visual_clues": ["Wi-Fi disconnected icon"],
            "confidence": 0.90
        }

    analyzer = ImageAnalyzer(vision_fn=mock_vision)
    raw_img = make_synthetic_image("JPEG")
    evidence = analyzer.analyze_image(raw_img)

    assert evidence["success"] is True
    assert "NETWORK" in evidence["detected_domains"]


def test_evidence_error_code_1001():
    """TEST 3: Image containing 'Error Code: 1001' extracts code and resolves to NETWORK."""
    def mock_vision(image_bytes, mime):
        return {
            "extracted_text": "Connection timed out. Error Code: 1001",
            "error_codes": ["1001"],
            "detected_domains": ["NETWORK"],
            "visual_clues": ["Network error screen"],
            "confidence": 0.94
        }

    analyzer = ImageAnalyzer(vision_fn=mock_vision)
    raw_img = make_synthetic_image("PNG")
    evidence = analyzer.analyze_image(raw_img)

    assert evidence["success"] is True
    assert "1001" in evidence["error_codes"]
    assert evidence["known_error_details"] is not None
    assert evidence["known_error_details"]["domain"] == "NETWORK"


def test_evidence_unreadable_or_no_diagnostic_info():
    """TEST 4: Image with no readable diagnostic information returns low confidence / empty domains."""
    def mock_vision(image_bytes, mime):
        return {
            "extracted_text": "",
            "error_codes": [],
            "detected_domains": [],
            "visual_clues": ["Generic wallpaper"],
            "confidence": 0.0
        }

    analyzer = ImageAnalyzer(vision_fn=mock_vision)
    raw_img = make_synthetic_image("PNG")
    evidence = analyzer.analyze_image(raw_img)

    assert evidence["success"] is True
    assert evidence["confidence"] == 0.0
    assert evidence["detected_domains"] == []
    assert evidence["error_codes"] == []


def test_evidence_unknown_error_code_not_fabricated():
    """TEST 7: Unknown error code is extracted but NOT assigned a fabricated meaning."""
    def mock_vision(image_bytes, mime):
        return {
            "extracted_text": "System error. Error Code: ERR_UNKNOWN_XYZ",
            "error_codes": ["ERR_UNKNOWN_XYZ"],
            "detected_domains": [],
            "visual_clues": [],
            "confidence": 0.50
        }

    analyzer = ImageAnalyzer(vision_fn=mock_vision)
    raw_img = make_synthetic_image("PNG")
    evidence = analyzer.analyze_image(raw_img)

    assert "ERR_UNKNOWN_XYZ" in evidence["error_codes"]
    assert evidence["known_error_details"] is None  # Not fabricated


# =========================================================================
# 3. MULTIMODAL FUSION & EVIDENCE PRIORITY (TESTS 5 & 6)
# =========================================================================

def test_multimodal_fusion_reinforcing_evidence():
    """TEST 5: Text says Bluetooth + image says Bluetooth -> confidence increases / is consistent."""
    def mock_vision(image_bytes, mime):
        return {
            "extracted_text": "Bluetooth pairing failed with Galaxy Buds2 Pro",
            "error_codes": ["BT-204"],
            "detected_domains": ["BLUETOOTH"],
            "visual_clues": ["Bluetooth pairing error dialog"],
            "confidence": 0.95
        }

    pipeline = GeneralizedQueryPipeline()
    pipeline.image_analyzer = ImageAnalyzer(vision_fn=mock_vision)

    raw_img = make_synthetic_image("PNG")
    b64_img = base64.b64encode(raw_img).decode("utf-8")

    res = pipeline.process_query(
        raw_query="My Galaxy Buds keep disconnecting",
        image_data=b64_img
    )

    assert res["domain"] == "BLUETOOTH"
    assert res["image_analysis_used"] is True
    assert res["image_evidence_confidence"] >= 0.90
    assert "BT-204" in res["error_codes"]
    assert res["confidence"] >= 0.95


def test_multimodal_fusion_text_priority_over_conflicting_image():
    """TEST 6: Text explicitly says Bluetooth but image contains unrelated/conflicting clue.
    Deterministic text domain remains authoritative and is NOT overridden!
    """
    def mock_vision(image_bytes, mime):
        return {
            "extracted_text": "Unable to connect to Wi-Fi network",
            "error_codes": [],
            "detected_domains": ["NETWORK"],  # Conflicting image domain
            "visual_clues": ["Wi-Fi settings dialog"],
            "confidence": 0.90
        }

    pipeline = GeneralizedQueryPipeline()
    pipeline.image_analyzer = ImageAnalyzer(vision_fn=mock_vision)

    raw_img = make_synthetic_image("PNG")
    b64_img = base64.b64encode(raw_img).decode("utf-8")

    # User explicitly complains about Bluetooth
    res = pipeline.process_query(
        raw_query="My Bluetooth earbuds keep disconnecting from my Galaxy S22",
        image_data=b64_img
    )

    # Bluetooth MUST remain authoritative
    assert res["domain"] == "BLUETOOTH"
    assert res["image_analysis_used"] is True


def test_multimodal_ambiguous_text_resolved_by_image():
    """When user text is ambiguous ('My phone is showing this error'), image evidence resolves it."""
    def mock_vision(image_bytes, mime):
        return {
            "extracted_text": "Connection timed out. Error Code: 1001",
            "error_codes": ["1001"],
            "detected_domains": ["NETWORK"],
            "visual_clues": ["Wi-Fi error dialog"],
            "confidence": 0.92
        }

    pipeline = GeneralizedQueryPipeline()
    pipeline.image_analyzer = ImageAnalyzer(vision_fn=mock_vision)

    raw_img = make_synthetic_image("PNG")
    b64_img = base64.b64encode(raw_img).decode("utf-8")

    res = pipeline.process_query(
        raw_query="My phone is showing this error",
        image_data=b64_img
    )

    # Resolved to NETWORK via image evidence
    assert res["domain"] == "NETWORK"
    assert res["needs_clarification"] is False
    assert res["matched_via"] == "image_evidence"
    assert res["image_analysis_used"] is True
    assert "1001" in res["error_codes"]


# =========================================================================
# 4. TEXT-ONLY REGRESSION TEST
# =========================================================================

def test_text_only_query_skips_image_processing_completely():
    """Text-only queries must NEVER invoke ImageAnalyzer (zero overhead)."""
    call_tracker = {"called": False}

    def mock_vision(image_bytes, mime):
        call_tracker["called"] = True
        return {}

    pipeline = GeneralizedQueryPipeline()
    pipeline.image_analyzer = ImageAnalyzer(vision_fn=mock_vision)

    res = pipeline.process_query("My Galaxy S22 Wi-Fi keeps disconnecting")
    assert res["domain"] == "NETWORK"
    assert res["image_analysis_used"] is False
    assert res["image_evidence"] is None
    assert call_tracker["called"] is False


# =========================================================================
# 5. REST API MULTIMODAL END-TO-END TEST
# =========================================================================

def test_api_session_start_with_image(monkeypatch):
    """POST /v1/session/start with image_data returns image evidence metadata."""
    def mock_analyze(image_input, mime_type=None):
        return {
            "success": True,
            "extracted_text": "Bluetooth pairing failed. Error Code: BT-204",
            "error_codes": ["BT-204"],
            "detected_domains": ["BLUETOOTH"],
            "visual_clues": ["Bluetooth pairing error"],
            "confidence": 0.94,
            "known_error_details": {"domain": "BLUETOOTH", "known": True},
            "error": None
        }

    from theme02_troubleshooting_engine.api import app as api_module
    monkeypatch.setattr(api_module.query_pipeline.image_analyzer, "analyze_image", mock_analyze)

    raw_img = make_synthetic_image("PNG")
    b64_img = f"data:image/png;base64,{base64.b64encode(raw_img).decode('utf-8')}"

    response = client.post("/v1/session/start", json={
        "query": "My phone is showing this error",
        "image_data": b64_img
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"
    diag = data["diagnosis"]
    assert diag["domain"] == "BLUETOOTH"
    assert data["image_analysis_used"] is True
    assert "BT-204" in data["error_codes"]
    assert data["image_evidence_confidence"] >= 0.90


# =========================================================================
# 6. RELIABLE PRETRAINED PIXEL-OCR TESTS (PADDLEOCR)
# Tests use actual drawn pixel data without PNG metadata.
# =========================================================================

def make_pixel_text_image(text: str, size=(600, 140)) -> bytes:
    """Creates a raw PNG where text is purely drawn into the image pixels."""
    img = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((25, 50), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")  # No metadata, only raw image pixels
    return buf.getvalue()


def test_pixel_ocr_test_a_bluetooth():
    """TEST A: Pretrained pixel-OCR on 'Bluetooth pairing failed / Unable to connect to Galaxy Buds2 Pro'."""
    analyzer = ImageAnalyzer()  # No mock vision_fn! Local PaddleOCR must run on pixels.
    raw_bytes = make_pixel_text_image("Bluetooth pairing failed / Unable to connect to Galaxy Buds2 Pro")
    evidence = analyzer.analyze_image(raw_bytes)

    assert evidence["success"] is True
    assert "BLUETOOTH" in evidence["detected_domains"]
    assert evidence["confidence"] >= 0.80
    assert any(term in evidence["extracted_text"].lower() for term in ["bluetooth", "buds", "pairing"])


def test_pixel_ocr_test_b_wifi():
    """TEST B: Pretrained pixel-OCR on 'Can't connect to Wi-Fi network'."""
    analyzer = ImageAnalyzer()
    raw_bytes = make_pixel_text_image("Can't connect to Wi-Fi network")
    evidence = analyzer.analyze_image(raw_bytes)

    assert evidence["success"] is True
    assert "NETWORK" in evidence["detected_domains"]
    assert evidence["confidence"] >= 0.80
    assert any(term in evidence["extracted_text"].lower() for term in ["wi-fi", "wifi", "network", "connect"])


def test_pixel_ocr_test_c_error_code_1001():
    """TEST C: Pretrained pixel-OCR on 'Error Code: 1001' extracts code and maps to NETWORK."""
    analyzer = ImageAnalyzer()
    raw_bytes = make_pixel_text_image("System Notice: Error Code: 1001")
    evidence = analyzer.analyze_image(raw_bytes)

    assert evidence["success"] is True
    assert "1001" in evidence["error_codes"]
    assert "NETWORK" in evidence["detected_domains"]
    assert evidence["known_error_details"] is not None
    assert evidence["known_error_details"]["code"] == "1001"


def test_pixel_ocr_test_d_unreadable_noise():
    """TEST D: Unreadable image with no drawn text yields low/zero confidence."""
    analyzer = ImageAnalyzer()
    img = Image.new("RGB", (150, 150), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    evidence = analyzer.analyze_image(buf.getvalue())

    assert evidence["success"] is True
    assert evidence["extracted_text"] == ""
    assert evidence["confidence"] == 0.0
    assert len(evidence["error_codes"]) == 0
    assert len(evidence["detected_domains"]) == 0


def test_pixel_ocr_test_e_explicit_text_authority_over_conflicting_image():
    """TEST E: Explicit Bluetooth text + conflicting Wi-Fi screenshot keeps BLUETOOTH diagnosis."""
    pipeline = GeneralizedQueryPipeline()
    # Image is pixel-drawn Wi-Fi screenshot
    wifi_bytes = make_pixel_text_image("Can't connect to Wi-Fi network")
    b64_wifi = f"data:image/png;base64,{base64.b64encode(wifi_bytes).decode('utf-8')}"

    # Explicit user text describes Bluetooth
    res = pipeline.process_query(
        raw_query="My Bluetooth earbuds keep disconnecting from my Galaxy S22",
        image_data=b64_wifi
    )

    # Authority rule: explicit user text MUST preserve BLUETOOTH
    assert res["domain"] == "BLUETOOTH"
    assert res["image_analysis_used"] is True


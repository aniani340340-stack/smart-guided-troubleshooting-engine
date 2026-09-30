"""Unit Tests for Error-Code Intelligence Layer (error_code_resolver.py).
Tests:
- Generalized pattern extraction (e.g. Error 1001, Error Code: BT-204, ERR_WIFI_01, 0x80004005)
- Code normalization to canonical uppercase strings
- Known code resolution to verified domain diagnostic plans
- Unknown code handling: strictly returns known=False without fabricating meanings
- Resilience against empty or noisy text
"""
import pytest
from theme02_troubleshooting_engine.core.error_code_resolver import (
    extract_error_codes,
    resolve_error_code,
    KNOWN_ERROR_CODES
)


def test_extract_error_codes_standard_patterns():
    """Extracts standard error patterns with colon, hyphen, or word separation."""
    text1 = "An issue occurred. Error Code: BT-204 please contact support."
    assert extract_error_codes(text1) == ["BT-204"]

    text2 = "System reported Error 1001 while authenticating to server."
    assert extract_error_codes(text2) == ["1001"]

    text3 = "Connection failed with CODE: ERR_WIFI_01."
    assert extract_error_codes(text3) == ["ERR_WIFI_01"]


def test_extract_error_codes_alphanumeric_and_hex():
    """Extracts hex and alphanumeric device error tags."""
    text1 = "Crash dump indicates fatal error 0x80004005 in driver stack."
    assert "0X80004005" in extract_error_codes(text1)

    text2 = "Diagnostic screen showing BAT-301 and CAM-502 warnings."
    codes = extract_error_codes(text2)
    assert "BAT-301" in codes
    assert "CAM-502" in codes


def test_extract_error_codes_empty_and_noise():
    """Returns empty list for text without error code patterns."""
    assert extract_error_codes("") == []
    assert extract_error_codes(None) == []
    assert extract_error_codes("My phone screen is completely unresponsive") == []


def test_resolve_known_error_codes():
    """Known codes map to verified domains and diagnostic plans."""
    res1001 = resolve_error_code("1001")
    assert res1001["known"] is True
    assert res1001["domain"] == "NETWORK"
    assert res1001["canonical_key"] == "wifi network connectivity"
    assert "Wi-Fi" in res1001["title"]

    res_bt = resolve_error_code("bt-204")  # Case insensitive
    assert res_bt["known"] is True
    assert res_bt["domain"] == "BLUETOOTH"
    assert res_bt["canonical_key"] == "bluetooth connection pairing"

    res_bat = resolve_error_code("BAT-301")
    assert res_bat["known"] is True
    assert res_bat["domain"] == "BATTERY"


def test_resolve_unknown_error_code_does_not_fabricate():
    """Unknown error codes must NOT have meanings fabricated."""
    res = resolve_error_code("ERR_UNKNOWN_99999")
    assert res["known"] is False
    assert res["domain"] is None
    assert res["canonical_key"] is None
    assert res["code"] == "ERR_UNKNOWN_99999"


def test_resolve_empty_code():
    """Empty or None code resolves safely without exceptions."""
    res = resolve_error_code("")
    assert res["known"] is False
    assert res["domain"] is None

"""Samsung Device Error-Code Intelligence Layer.
Extracts, normalizes, and resolves Samsung diagnostic error codes from text and OCR output.
Follows strict safety principles:
- Generalized regex pattern extraction for codes (e.g. Error 1001, BT-204, ERR_WIFI_01).
- Normalizes codes into canonical formats.
- Maps known codes to verified domain diagnoses.
- Never fabricates or invents meanings for unknown codes.
"""
import re
from typing import List, Dict, Optional, Any, Tuple


# Known Samsung Diagnostic Error-Code Catalog
# Mapped strictly to verified domain plans in DOMAIN_CANONICAL_PLANS
KNOWN_ERROR_CODES: Dict[str, Dict[str, Any]] = {
    "1001": {
        "domain": "NETWORK",
        "canonical_key": "wifi network connectivity",
        "title": "Wi-Fi connectivity issue",
        "description": "Network gateway unreachable or DNS resolution failure",
        "confidence": 0.95
    },
    "BT-204": {
        "domain": "BLUETOOTH",
        "canonical_key": "bluetooth connection pairing",
        "title": "Bluetooth pairing issue",
        "description": "Bluetooth peripheral pairing handshake timeout",
        "confidence": 0.95
    },
    "ERR_WIFI_01": {
        "domain": "NETWORK",
        "canonical_key": "wifi network connectivity",
        "title": "Wi-Fi connectivity issue",
        "description": "Wi-Fi network authentication or DHCP timeout",
        "confidence": 0.95
    },
    "BAT-301": {
        "domain": "BATTERY",
        "canonical_key": "battery fast drain",
        "title": "Battery fast drain",
        "description": "Battery high-temperature discharge or abnormal current draw",
        "confidence": 0.95
    },
    "CAM-502": {
        "domain": "CAMERA",
        "canonical_key": "camera video flicker",
        "title": "Camera video flicker",
        "description": "Camera sensor initialization failure or shutter timing discrepancy",
        "confidence": 0.95
    },
    "DISP-404": {
        "domain": "DISPLAY",
        "canonical_key": "blank black display",
        "title": "Blank black display",
        "description": "Display digitizer frame buffer timeout or panel responsiveness drop",
        "confidence": 0.95
    },
    "AUD-601": {
        "domain": "AUDIO",
        "canonical_key": "audio speaker sound",
        "title": "Audio speaker sound",
        "description": "Audio hardware routing deadlock or DSP mute state",
        "confidence": 0.95
    }
}

# Generalized regular expression patterns for Samsung and mobile error codes
ERROR_CODE_PATTERNS = [
    # Explicit prefix with colon or hyphen: "Error Code: BT-204", "Error code 1001", "CODE: 1001"
    re.compile(r"(?:error\s*code|err\s*code|code)\s*[:=\-]?\s*([A-Za-z0-9_\-]+)", re.IGNORECASE),
    # Standalone Error number: "Error 1001", "Error 404"
    re.compile(r"\berror\s*[:=\-]?\s*([0-9]{3,5})\b", re.IGNORECASE),
    # Prefixed error tags: "ERR_1001", "ERR_WIFI_01", "ERR_BT_FAIL"
    re.compile(r"\b(ERR_[A-Za-z0-9_]+)\b", re.IGNORECASE),
    # Hex error codes: "0x80004005", "0x0000007E"
    re.compile(r"\b(0x[0-9a-fA-F]{6,8})\b"),
    # Samsung subsystem tags: "BT-204", "BAT-301", "CAM-502", "DISP-404"
    re.compile(r"\b([A-Z]{2,4}-[0-9]{3,4})\b")
]


def extract_error_codes(text: str) -> List[str]:
    """Extracts and normalizes unique diagnostic error codes from arbitrary text or OCR output.
    Returns: List of normalized error code strings.
    """
    if not text or not isinstance(text, str):
        return []

    found_codes: List[str] = []
    seen = set()

    for pattern in ERROR_CODE_PATTERNS:
        for match in pattern.finditer(text):
            code = match.group(1).strip()
            # Filter out non-code generic words if captured
            if code.lower() in {"the", "a", "an", "is", "of", "and", "or", "in", "on", "to", "for"}:
                continue
            # Normalize to uppercase
            norm_code = code.upper()
            if norm_code not in seen:
                seen.add(norm_code)
                found_codes.append(norm_code)

    return found_codes


def resolve_error_code(code: str) -> Dict[str, Any]:
    """Resolves an extracted error code against known Samsung diagnostic knowledge.
    If the code is unknown, does NOT fabricate a meaning. Returns known=False.
    """
    if not code:
        return {"code": "", "known": False, "domain": None, "diagnosis": None}

    norm = code.strip().upper()
    if norm in KNOWN_ERROR_CODES:
        info = KNOWN_ERROR_CODES[norm]
        return {
            "code": norm,
            "known": True,
            "domain": info["domain"],
            "canonical_key": info["canonical_key"],
            "title": info["title"],
            "description": info["description"],
            "confidence": info["confidence"]
        }

    # Unknown code: return safely without fabrication
    return {
        "code": norm,
        "known": False,
        "domain": None,
        "canonical_key": None,
        "title": None,
        "description": "Unknown or unmapped device error code",
        "confidence": 0.0
    }

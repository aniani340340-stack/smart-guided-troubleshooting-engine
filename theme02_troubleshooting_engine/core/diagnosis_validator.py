"""Semantic Consistency and Diagnosis Validation Layer.
Prevents semantic mismatches (e.g. Wi-Fi queries returning Email diagnoses)
using weighted domain concept matching and cross-domain compatibility rules.
"""
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from theme02_troubleshooting_engine.core.schema import Goal

# Weighted concept lexicon per device subsystem domain
DOMAIN_LEXICON: Dict[str, Dict[str, float]] = {
    "NETWORK": {
        "wifi": 4.5, "wi-fi": 4.5, "internet": 4.0, "network": 3.5, "router": 3.5,
        "mobile data": 3.5, "cellular": 3.5, "hotspot": 3.5, "dns": 3.0,
        "cannot load web": 3.5, "ip address": 3.0,
        "load pages": 3.0, "load web": 3.0, "browser connection": 3.0, "airplane mode": 2.0,
        "connections": 2.0, "ssid": 3.5, "gateway": 3.0, "wlan": 4.0, "web pages": 3.0,
        "webpages": 3.0, "websites": 3.0, "web page": 3.0
    },
    "DISPLAY": {
        "screen": 3.5, "display": 3.5, "black": 3.0, "blank": 3.0, "flicker": 3.0,
        "flickers": 3.0, "flashes": 3.0, "flashing": 3.0, "brightness": 2.5,
        "touch": 3.0, "touchscreen": 3.5, "digitizer": 3.5, "crack": 3.0,
        "cracked": 3.0, "dark": 2.0, "dead display": 3.5, "responsive": 2.5,
        "responsiveness": 2.5, "glitch": 2.0, "lines": 2.0, "hinge": 2.5
    },
    "BATTERY": {
        "battery": 4.5, "charging": 4.0, "charge": 3.5, "charger": 3.5,
        "drain": 3.5, "drains": 3.5, "power": 2.5, "battery life": 4.5,
        "fast drain": 4.0, "overheating": 2.5, "discharging": 3.0, "cable": 2.0,
        "fast charging": 4.0, "wireless charger": 3.5, "won't charge": 4.0, "wont charge": 4.0
    },
    "BLUETOOTH": {
        "bluetooth": 4.5, "wireless headphones": 4.0, "buds": 4.0, "galaxy buds": 4.5,
        "pairing": 3.5, "paired": 3.0, "headset": 3.5, "earbuds": 4.0, "ble": 3.0,
        "connect headphones": 3.5, "headphones": 3.5, "earphones": 3.5, "unpair": 3.5,
        "buds2": 4.5, "buds pro": 4.5, "buds live": 4.5, "wearable": 3.0, "galaxy watch": 3.5
    },
    "AUDIO": {
        "speaker": 4.5, "sound": 4.0, "volume": 3.5, "microphone": 4.5,
        "mic": 3.5, "audio": 4.0, "distortion": 3.0, "no sound": 4.5,
        "caller cannot hear": 4.0, "earpiece": 4.0, "crackling": 3.0, "buzzing": 3.0
    },
    "CAMERA": {
        "camera": 4.5, "photo": 3.5, "photos": 3.0, "video": 3.0,
        "focus": 3.5, "shutter": 3.0, "lens": 3.5, "zoom": 2.5, "blur": 2.5,
        "megapixels": 3.0, "selfie": 3.5, "nightography": 3.5
    },
    "EMAIL": {
        "email": 4.5, "mail": 3.5, "gmail": 4.0, "outlook": 4.0,
        "exchange": 3.5, "mail sync": 4.0, "inbox": 3.5, "email account": 4.5,
        "email server": 4.5, "imap": 4.0, "pop3": 4.0
    },
    "SYSTEM": {
        "gesture": 3.5, "swipe": 3.5, "navigation bar": 4.0, "assistant menu": 4.5,
        "smart switch": 4.5, "multi window": 4.0, "split screen": 4.0, "app pair": 4.0,
        "screen mirror": 4.0, "smart view": 4.5, "auto rotate": 4.0, "transfer data": 3.5
    }
}

# Incompatible domain pairs: query_domain -> set of disallowed candidate domains
INCOMPATIBLE_DOMAINS = {
    "NETWORK": {"EMAIL", "CAMERA", "BATTERY", "BLUETOOTH", "DISPLAY"},
    "DISPLAY": {"BATTERY", "CAMERA", "EMAIL", "BLUETOOTH", "AUDIO", "NETWORK"},
    "BATTERY": {"CAMERA", "EMAIL", "BLUETOOTH", "AUDIO", "DISPLAY", "NETWORK"},
    "BLUETOOTH": {"EMAIL", "DISPLAY", "CAMERA", "BATTERY", "NETWORK"},
    "AUDIO": {"DISPLAY", "BATTERY", "CAMERA", "EMAIL", "NETWORK"},
    "CAMERA": {"BATTERY", "EMAIL", "BLUETOOTH", "AUDIO", "NETWORK"},
    "EMAIL": {"CAMERA", "BATTERY", "BLUETOOTH", "AUDIO", "NETWORK"}
}


def classify_text_domain(text: str) -> Tuple[str, float, Dict[str, float]]:
    """Analyzes text using weighted lexicon scoring to identify its primary subsystem domain.
    Returns: (primary_domain: str, confidence_score: float, all_scores: Dict[str, float])
    """
    clean_text = text.lower()
    scores: Dict[str, float] = {d: 0.0 for d in DOMAIN_LEXICON}

    for domain, terms in DOMAIN_LEXICON.items():
        for term, weight in terms.items():
            # Use word boundary search for exact phrases/words
            escaped = re.escape(term)
            pattern = rf"\b{escaped}\b"
            matches = len(re.findall(pattern, clean_text))
            if matches > 0:
                scores[domain] += matches * weight

    best_domain = max(scores, key=scores.get)
    max_score = scores[best_domain]

    if max_score <= 0.0:
        return "GENERIC", 0.0, scores

    total_score = sum(scores.values())
    confidence = max_score / total_score if total_score > 0 else 0.0

    return best_domain, confidence, scores


def validate_diagnosis(
    query: str,
    diagnosis: Union[Goal, Dict[str, Any], str],
    threshold: float = 0.5
) -> Tuple[bool, str, str]:
    """Validates that a candidate diagnosis is semantically compatible with the user's complaint.
    Returns: (is_compatible: bool, reason: str, detected_query_domain: str)
    """
    query_domain, query_conf, query_scores = classify_text_domain(query)

    # If query is completely generic / unrecognized, do not reject candidates
    if query_domain == "GENERIC" or query_conf < 0.2:
        return True, "Query has generic intent; candidate allowed.", query_domain

    # Extract diagnostic text from candidate
    diag_text = ""
    if isinstance(diagnosis, Goal):
        action_names = " ".join(a.actionName for a in diagnosis.actions)
        diag_text = f"{diagnosis.title} {diagnosis.goal} {action_names}"
    elif isinstance(diagnosis, dict):
        title = diagnosis.get("title", "")
        goal = diagnosis.get("goal", "")
        actions = diagnosis.get("actions", [])
        act_names = " ".join(a.get("actionName", "") if isinstance(a, dict) else "" for a in actions)
        diag_text = f"{title} {goal} {act_names}"
    elif isinstance(diagnosis, str):
        diag_text = diagnosis

    diag_domain, diag_conf, diag_scores = classify_text_domain(diag_text)

    # Check incompatibility rule
    incompatible_targets = INCOMPATIBLE_DOMAINS.get(query_domain, set())
    if diag_domain in incompatible_targets and query_conf >= 0.35:
        reason = (
            f"Semantic mismatch rejected: Query domain is '{query_domain}' (conf: {query_conf:.2f}), "
            f"but candidate diagnosis is '{diag_domain}' (conf: {diag_conf:.2f})."
        )
        return False, reason, query_domain

    # Special check: Query strongly specifies Wi-Fi/Internet, candidate mentions email server
    clean_q = query.lower()
    clean_d = diag_text.lower()
    if any(k in clean_q for k in ["wifi", "wi-fi", "internet", "web pages"]) and not any(k in clean_q for k in ["email", "mail", "gmail"]):
        if any(k in clean_d for k in ["email server", "mail app", "email account", "gmail"]):
            return False, "Query specifically targets Wi-Fi/Internet but candidate is an Email plan.", query_domain

    return True, "Candidate diagnosis is semantically compatible.", query_domain


def validate_llm_classification(
    query: str,
    llm_domain: str,
    deterministic_domain: str = "GENERIC",
    deterministic_confidence: float = 0.0
) -> Tuple[bool, str]:
    """Validates that a candidate domain classified by LLM is safe, supported,
    and does not contradict stronger deterministic domain signals in the user query.
    Returns: (is_valid: bool, reason: str)
    """
    supported_domains = {
        "NETWORK", "DISPLAY", "BATTERY", "BLUETOOTH",
        "AUDIO", "CAMERA", "EMAIL", "SYSTEM"
    }

    if not llm_domain or not isinstance(llm_domain, str):
        return False, "LLM domain is empty or invalid type."

    clean_llm_domain = llm_domain.strip().upper()

    if clean_llm_domain not in supported_domains and clean_llm_domain != "GENERIC":
        return False, f"LLM domain '{llm_domain}' is not in the supported domain enum."

    if clean_llm_domain == "GENERIC":
        return True, "LLM returned GENERIC; valid candidate for clarification fallback."

    # 1. Deterministic domain signal check:
    # The LLM must NEVER override a stronger deterministic domain signal.
    if deterministic_domain != "GENERIC":
        if deterministic_confidence >= 0.80 and clean_llm_domain != deterministic_domain:
            return False, (
                f"LLM domain '{clean_llm_domain}' rejected: query has strong deterministic domain "
                f"'{deterministic_domain}' (confidence: {deterministic_confidence:.2f})."
            )
        incompatible = INCOMPATIBLE_DOMAINS.get(deterministic_domain, set())
        if clean_llm_domain in incompatible:
            return False, (
                f"LLM domain '{clean_llm_domain}' rejected: incompatible with detected query domain '{deterministic_domain}'."
            )

    # 2. Lexical domain check on the raw query text:
    # Prevent semantic bypass if query explicitly contains anchors of an incompatible domain.
    lexical_domain, lexical_conf, _ = classify_text_domain(query)
    if lexical_domain != "GENERIC" and lexical_conf >= 0.35:
        incompatible_targets = INCOMPATIBLE_DOMAINS.get(lexical_domain, set())
        if clean_llm_domain in incompatible_targets:
            return False, (
                f"LLM domain '{clean_llm_domain}' rejected: contradicts explicit '{lexical_domain}' anchors in user query."
            )

    return True, f"LLM domain '{clean_llm_domain}' validated and semantically consistent."

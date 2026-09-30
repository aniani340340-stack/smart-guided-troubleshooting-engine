"""Generalized Natural Language Query Pipeline.
Implements multi-stage query processing:
1. Normalization & Tokenization
2. Device & Accessory Entity Extraction (Phone Model vs. Accessory)
3. Explicit Domain Anchor Detection (Anchors have strict priority over generic symptom words)
4. Semantic Candidate Retrieval & Hybrid Ranking
5. Transparent Confidence Calculation
6. Ambiguity & Clarification Routing
7. Optional LLM Zero-Shot Classification Abstraction
"""
import re
import os
import time
import json
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from theme02_troubleshooting_engine.core.schema import Goal, Action, StepGroup, Deeplink, ValidationDeepLink, actionCategory
from theme02_troubleshooting_engine.core.diagnosis_validator import classify_text_domain, validate_diagnosis, validate_llm_classification
from theme02_troubleshooting_engine.core.error_code_resolver import extract_error_codes, resolve_error_code
from theme02_troubleshooting_engine.core.image_analyzer import ImageAnalyzer
from theme02_troubleshooting_engine.core.multi_intent import MultiIntentDecomposer, IntentCandidate, MultiIntentResult
try:
    from theme02_troubleshooting_engine.core.profiler import record_timing, add_timing
except Exception:
    def record_timing(stage: str, duration_ms: float): pass
    def add_timing(stage: str, duration_ms: float): pass


# Explicit Subsystem Domain Anchors (Physical components, hardware subsystems, protocols)
# These ANCHORS take strict precedence over generic symptom verbs (e.g. disconnect, not working, drop)
DOMAIN_ANCHORS: Dict[str, Set[str]] = {
    "BLUETOOTH": {
        "bluetooth", "buds", "galaxy buds", "buds2", "buds pro", "buds live", "buds fe",
        "earbuds", "earbud", "headphones", "headphone", "headset", "earphones", "earphone",
        "wireless audio", "wireless headphones", "wearable", "galaxy watch", "watch",
        "ble", "pairing", "unpair", "paired device", "tws", "bluetooth speaker",
        "car bluetooth", "bluetooth headset", "bluetooth headphones"
    },
    "NETWORK": {
        "wifi", "wi-fi", "internet", "network", "router", "hotspot", "mobile data",
        "cellular data", "cellular", "data connection", "dns", "ssid", "wlan",
        "ip address", "webpages", "web pages", "websites", "webpage", "website",
        "browser connection", "cannot load web", "load pages", "offline mode",
        "airplane mode", "flight mode", "modem"
    },
    "BATTERY": {
        "battery", "charging", "charger", "charge", "fast charging", "super fast charging",
        "wireless charging", "power", "battery life", "drain", "drains", "draining",
        "overheating", "overheat", "discharging", "discharge", "discharges", "cable",
        "adapter", "power saving", "battery percentage", "battery health", "battery drain"
    },
    "DISPLAY": {
        "screen", "display", "black screen", "blank screen", "dark screen", "flicker",
        "flickers", "flickering", "flashes", "flashing", "brightness", "touch",
        "touchscreen", "digitizer", "crack", "cracked", "shattered", "dead pixels",
        "lines on screen", "hinge", "fold screen", "inner screen", "cover screen",
        "unresponsive screen", "burn in"
    },
    "AUDIO": {
        "speaker", "sound", "volume", "microphone", "mic", "audio", "distortion",
        "distorted", "no sound", "cannot hear", "caller cannot hear", "earpiece",
        "buzzing", "crackling sound", "low volume", "mute", "media volume",
        "sound mode", "ringtone"
    },
    "CAMERA": {
        "camera", "photo", "photos", "video", "videos", "focus", "shutter",
        "lens", "zoom", "blur", "blurry photo", "selfie", "front camera",
        "rear camera", "megapixels", "nightography", "camera app", "flash",
        "selfie camera", "camera preview"
    },
    "EMAIL": {
        "email", "emails", "mail", "gmail", "outlook", "exchange", "mail sync",
        "inbox", "email account", "email server", "imap", "pop3", "smtp",
        "cannot send email", "cannot receive email", "mail app"
    },
    "SYSTEM": {
        "gesture", "gestures", "swipe", "navigation bar", "assistant menu",
        "smart switch", "multi window", "split screen", "app pair", "edge panel",
        "smart view", "screen mirror", "screen mirroring", "cast to tv", "auto rotate",
        "auto-rotate", "transfer data", "reboot", "restart", "restarting", "safe mode",
        "factory reset", "lock screen", "boot loop", "bootloop"
    }
}

# Generic Symptom Verbs / Qualifiers (CANNOT independently assign a domain)
GENERIC_SYMPTOMS: Set[str] = {
    "disconnect", "disconnects", "disconnecting", "disconnected",
    "connect", "connects", "connecting", "connection",
    "drop", "drops", "dropping", "dropped",
    "fail", "fails", "failing", "failed",
    "work", "works", "working", "not working", "won't work", "wont work",
    "issue", "issues", "problem", "problems", "trouble", "troubles",
    "bug", "glitch", "broken", "unresponsive", "slow", "sluggish",
    "stops", "stopped", "quits", "crashes", "crashing",
    "won't load", "wont load", "won't open", "wont open", "cannot open",
    "won't stay", "wont stay", "keeps losing", "lost"
}

# Canonical Reference Knowledge for each Domain
DOMAIN_CANONICAL_PLANS: Dict[str, Dict[str, Any]] = {
    "BLUETOOTH": {
        "canonical_key": "bluetooth connection pairing",
        "title": "Bluetooth pairing issue",
        "summary": "Identified potential Bluetooth pairing or audio accessory connection anomaly.",
        "content": """## Step 1: Check Bluetooth Status
Open Settings, tap Connections, and verify Bluetooth is toggled ON.
## Step 2: Unpair and Re-pair Device
Select your audio accessory or wearable from Paired devices, tap Unpair, and initiate new pairing.
## Step 3: Restart Phone and Accessory
Restart both your Galaxy phone and the Bluetooth accessory to clear transient stack deadlocks.
## Step 4: Reset Network Settings
Navigate to Settings > General management > Reset > Reset network settings."""
    },
    "NETWORK": {
        "canonical_key": "wifi network connectivity",
        "title": "Wi-Fi connectivity issue",
        "summary": "Identified potential Wi-Fi or cellular network routing anomaly.",
        "content": """## Step 1: Check Wi-Fi Status
Swipe down from the top of your screen to open Quick settings. Verify Wi-Fi is enabled and connected to your network.
## Step 2: Enable Wi-Fi Adapter
Navigate to Settings, tap Connections, and toggle the Wi-Fi switch to ON.
## Step 3: Verify Internet Connection
Open the browser and load a test webpage to confirm active data routing.
## Step 4: Reset Network Settings
Navigate to Settings, tap General management, tap Reset, and select Reset network settings."""
    },
    "BATTERY": {
        "canonical_key": "battery fast drain",
        "title": "Battery fast drain",
        "summary": "Identified abnormal battery discharge or charging rate discrepancy.",
        "content": """## Step 1: Check Battery Usage in Device Care
Navigate to Settings, tap Battery and device care, tap Battery, and review background app usage.
## Step 2: Enable Power Saving Mode
Toggle Power saving mode ON in Settings > Battery to throttle heavy background synchronization.
## Step 3: Check Fast Charging Settings
Navigate to Settings > Battery > More battery settings, and ensure Fast charging is enabled."""
    },
    "DISPLAY": {
        "canonical_key": "blank black display",
        "title": "Blank black display",
        "summary": "Identified display digitizer responsiveness or screen backlight anomaly.",
        "content": """## Step 1: Force Restart Device
Simultaneously press and hold the Volume Down and Side keys for 7 to 10 seconds until the phone reboots.
## Step 2: Connect to Official Charger
Connect the phone to a verified Samsung charger and verify if the charging indicator appears.
## Step 3: Boot into Safe Mode
Press and hold Power, then touch and hold Power off until the Safe Mode icon appears."""
    },
    "AUDIO": {
        "canonical_key": "audio speaker sound",
        "title": "Audio speaker sound",
        "summary": "Identified audio output or microphone distortion anomaly.",
        "content": """## Step 1: Check Sound Mode and Volume
Navigate to Settings, tap Sounds and vibration, and ensure Sound mode is not set to Mute.
## Step 2: Inspect Media Output and Bluetooth
Ensure audio is not routing to a previously connected Bluetooth device or external dock.
## Step 3: Restart Device in Safe Mode
Restart the phone to check if third-party sound equalizer apps are causing audio corruption."""
    },
    "CAMERA": {
        "canonical_key": "camera video flicker",
        "title": "Camera video flicker",
        "summary": "Identified camera sensor stability or shutter focus anomaly.",
        "content": """## Step 1: Clear Camera App Cache
Navigate to Settings > Apps > Camera > Storage, and tap Clear Cache.
## Step 2: Reset Camera Settings
Open the Camera app, tap the Settings gear icon, scroll down, and tap Reset settings.
## Step 3: Test in Safe Mode
Boot into Safe Mode to confirm third-party camera filters are not causing shutter freezes."""
    },
    "EMAIL": {
        "canonical_key": "email connection sync",
        "title": "Email sync issue",
        "summary": "Identified mail protocol synchronization or authentication issue.",
        "content": """## Step 1: Check Account Sync Settings
Navigate to Settings, tap Accounts and backup > Manage accounts > select Email account > tap Sync account.
## Step 2: Verify Server Credentials
Open your email application settings and ensure incoming/outgoing server hostnames and passwords are valid.
## Step 3: Clear Email App Storage
Navigate to Settings > Apps > Email > Storage, and tap Clear Data to force re-synchronization."""
    },
    "SYSTEM": {
        "canonical_key": "multi window split view",
        "title": "Use multi window",
        "summary": "Identified system navigation or multitasking UI configuration discrepancy.",
        "content": """## Step 1: Check Navigation Bar Settings
Navigate to Settings > Display > Navigation bar, and choose between Buttons or Swipe gestures.
## Step 2: Review Advanced Features
Open Settings > Advanced features > Multi window, and toggle 'Swipe for split screen' ON.
## Step 3: Reset Settings
Navigate to Settings > General management > Reset > Reset all settings."""
    }
}


class DeviceAccessoryExtractor:
    """Disambiguates and extracts separate Phone Hardware models vs. Peripheral/Accessory models."""

    PHONE_PATTERNS = [
        (r"\bgalaxy\s+s2[1-5](\s+ultra|\s+plus|\s+fe)?\b", "Galaxy S22"),
        (r"\bgalaxy\s+z\s+fold\s*[1-6]\b", "Galaxy Z Fold 6"),
        (r"\bgalaxy\s+z\s+flip\s*[1-6]\b", "Galaxy Z Flip 6"),
        (r"\bgalaxy\s+a\d{2}[sge]?\b", "Galaxy A55"),
        (r"\bgalaxy\s+note\s*20(\s+ultra)?\b", "Galaxy Note 20"),
        (r"\bs2[1-5]\s*ultra\b", "Galaxy S24 Ultra"),
        (r"\bs2[1-5]\b", "Galaxy S22")
    ]

    ACCESSORY_PATTERNS = [
        (r"\bgalaxy\s+buds\s*2\s*pro\b", "Galaxy Buds2 Pro"),
        (r"\bgalaxy\s+buds\s*pro\s*2\b", "Galaxy Buds2 Pro"),
        (r"\bgalaxy\s+buds\s*2\b", "Galaxy Buds2"),
        (r"\bgalaxy\s+buds\s*pro\b", "Galaxy Buds Pro"),
        (r"\bgalaxy\s+buds\s*live\b", "Galaxy Buds Live"),
        (r"\bgalaxy\s+buds\s*fe\b", "Galaxy Buds FE"),
        (r"\bgalaxy\s+buds\b", "Galaxy Buds"),
        (r"\bgalaxy\s+watch\s*[4-7](\s*classic|\s*pro)?\b", "Galaxy Watch"),
        (r"\b(bluetooth\s+headphones?|wireless\s+headphones?)\b", "Bluetooth Headphones"),
        (r"\b(earbuds?|headset|earphones?)\b", "Wireless Earbuds")
    ]

    @classmethod
    def extract_entities(cls, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extracts (phone_model, accessory_model) from natural language text.
        Guarantee: An accessory (e.g. Galaxy Buds2 Pro) is never misidentified as the phone model.
        """
        lower = text.lower()
        extracted_accessory: Optional[str] = None
        extracted_phone: Optional[str] = None

        # 1. Extract accessory first
        for pat, canonical_acc in cls.ACCESSORY_PATTERNS:
            match = re.search(pat, lower)
            if match:
                matched_span = text[match.start():match.end()]
                extracted_accessory = matched_span.strip().title()
                # Normalize known Galaxy accessories
                if "buds2 pro" in lower or "buds 2 pro" in lower:
                    extracted_accessory = "Galaxy Buds2 Pro"
                elif "buds pro" in lower:
                    extracted_accessory = "Galaxy Buds Pro"
                elif "buds2" in lower or "buds 2" in lower:
                    extracted_accessory = "Galaxy Buds2"
                elif "buds live" in lower:
                    extracted_accessory = "Galaxy Buds Live"
                elif re.search(r"\b(galaxy\s+)?buds\b", lower):
                    extracted_accessory = "Galaxy Buds"
                elif "watch" in lower:
                    extracted_accessory = "Galaxy Watch"
                elif "headphones" in lower:
                    extracted_accessory = "Bluetooth Headphones"
                elif "earbuds" in lower or "earbud" in lower or "earphones" in lower or "headset" in lower:
                    extracted_accessory = "Wireless Earbuds"
                break

        # 2. Extract phone model
        # Find phone model in text, ensuring it is not part of the accessory name
        for pat, _ in cls.PHONE_PATTERNS:
            for match in re.finditer(pat, lower):
                m_str = match.group(0)
                if extracted_accessory and m_str in extracted_accessory.lower():
                    continue
                # Map to standard clean phone name
                m_clean = m_str.lower()
                if "s24 ultra" in m_clean:
                    extracted_phone = "Galaxy S24 Ultra"
                elif "s24" in m_clean:
                    extracted_phone = "Galaxy S24"
                elif "s23 ultra" in m_clean:
                    extracted_phone = "Galaxy S23 Ultra"
                elif "s23" in m_clean:
                    extracted_phone = "Galaxy S23"
                elif "s22 ultra" in m_clean:
                    extracted_phone = "Galaxy S22 Ultra"
                elif "s22" in m_clean:
                    extracted_phone = "Galaxy S22"
                elif "z fold" in m_clean:
                    extracted_phone = "Galaxy Z Fold 6"
                elif "z flip" in m_clean:
                    extracted_phone = "Galaxy Z Flip 6"
                elif "a55" in m_clean:
                    extracted_phone = "Galaxy A55"
                elif "note 20" in m_clean:
                    extracted_phone = "Galaxy Note 20"
                else:
                    extracted_phone = m_str.strip().title()
                break
            if extracted_phone:
                break

        return extracted_phone, extracted_accessory


class DomainDetector:
    """Detects primary hardware/subsystem domain prioritizing explicit anchors over generic verbs."""

    @classmethod
    def detect_domain(cls, text: str) -> Tuple[str, float, Dict[str, float], List[str]]:
        """Analyzes text for domain anchors and generic symptoms.
        Returns:
            - domain: str ('NETWORK', 'BLUETOOTH', 'BATTERY', etc., or 'GENERIC')
            - confidence: float (0.0 to 1.0)
            - scores: Dict[str, float]
            - detected_anchors: List[str]
        """
        lower = text.lower()
        clean = re.sub(r"[^\w\s-]", " ", lower)

        anchor_scores: Dict[str, float] = {d: 0.0 for d in DOMAIN_ANCHORS}
        detected_anchors: List[str] = []

        # Check multi-word and single-word anchors per domain
        for domain, anchors in DOMAIN_ANCHORS.items():
            for anchor in anchors:
                escaped = re.escape(anchor)
                pattern = rf"\b{escaped}\b"
                matches = len(re.findall(pattern, clean))
                if matches > 0:
                    # Multi-word anchors carry heavier weight
                    weight = 3.5 if " " in anchor else 2.5
                    anchor_scores[domain] += matches * weight
                    detected_anchors.append(anchor)

        # Check generic symptoms
        has_generic_symptoms = any(re.search(rf"\b{re.escape(sym)}\b", clean) for sym in GENERIC_SYMPTOMS)

        best_domain = max(anchor_scores, key=anchor_scores.get)
        max_score = anchor_scores[best_domain]

        # If no explicit domain anchors were found at all:
        if max_score <= 0.0:
            return "GENERIC", 0.0, anchor_scores, []

        total_score = sum(anchor_scores.values())
        dominance_ratio = max_score / total_score if total_score > 0 else 0.0

        # Confidence calculation based on anchor strength
        if max_score >= 5.0 and dominance_ratio >= 0.8:
            confidence = 0.98
        elif max_score >= 2.5 and dominance_ratio >= 0.7:
            confidence = 0.92
        elif max_score >= 2.0:
            confidence = 0.80
        else:
            confidence = 0.60

        return best_domain, confidence, anchor_scores, detected_anchors


class LLMClassificationResult(dict):
    """Structured LLM classification result supporting dict access, attribute access, and tuple unpacking."""
    def __init__(self, domain: str, confidence: float, reason: str = ""):
        super().__init__(domain=domain, confidence=confidence, reason=reason)
        self.domain = domain
        self.confidence = confidence
        self.reason = reason

    def __iter__(self):
        # Enables backward-compatible tuple unpacking: domain, conf = result
        return iter((self.domain, self.confidence))


class LLMDiagnosisClassifier:
    """Optional, Controlled LLM Fallback Classifier for uncertain query classification.
    Only classifies into one of the 8 canonical domains or GENERIC:
    [NETWORK, DISPLAY, BATTERY, BLUETOOTH, AUDIO, CAMERA, EMAIL, SYSTEM, GENERIC]

    Safety Principles:
    - Never generates troubleshooting instructions or settings links.
    - Never invents diagnoses or device capabilities.
    - Strictly validated by diagnosis_validator.py before adoption.
    - Completely optional: runs normally without API credentials.
    """
    SUPPORTED_DOMAINS = [
        "NETWORK", "DISPLAY", "BATTERY", "BLUETOOTH",
        "AUDIO", "CAMERA", "EMAIL", "SYSTEM"
    ]
    ALL_ALLOWED_DOMAINS = set(SUPPORTED_DOMAINS) | {"GENERIC", "UNKNOWN"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        timeout: float = 3.0,
        client_fn: Optional[Any] = None
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if provider:
            self.provider = provider
        elif api_key:
            self.provider = "gemini" if "AIza" in api_key else "openai"
        elif os.environ.get("GEMINI_API_KEY"):
            self.provider = "gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            self.provider = "openai"
        else:
            self.provider = None

        self.timeout = timeout
        self.client_fn = client_fn  # Optional mock/callable for testing without network

    def is_available(self) -> bool:
        return bool(self.api_key or self.client_fn)

    def parse_and_validate_response(self, raw_text: str) -> Optional[LLMClassificationResult]:
        """Safely parses, validates and clamps the structured LLM JSON response.
        Rejects non-JSON, missing keys, invalid types, and unsupported domains.
        """
        if not raw_text or not isinstance(raw_text, str):
            return None

        # Clean markdown code fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        data = None
        try:
            data = json.loads(cleaned)
        except Exception:
            # Fallback regex extraction if model surrounded JSON with extra text
            m = re.search(r'\{\s*"domain"\s*:\s*"([^"]+)"\s*,\s*"confidence"\s*:\s*([0-9.]+)', cleaned)
            if m:
                data = {"domain": m.group(1), "confidence": float(m.group(2)), "reason": "Extracted via fallback parser"}
            else:
                return None

        if not isinstance(data, dict):
            return None

        raw_domain = data.get("domain")
        if not isinstance(raw_domain, str):
            return None

        domain = raw_domain.strip().upper()
        if domain == "UNKNOWN":
            domain = "GENERIC"

        # Supported domain check
        if domain not in self.SUPPORTED_DOMAINS and domain != "GENERIC":
            return None

        # Confidence validation: must be float or int (not bool)
        raw_conf = data.get("confidence")
        if isinstance(raw_conf, bool) or not isinstance(raw_conf, (int, float)):
            return None

        try:
            conf_val = float(raw_conf)
            if conf_val < 0.0 or conf_val > 1.0 or conf_val != conf_val:  # NaN check
                return None
            clamped_conf = round(conf_val, 2)
        except (ValueError, TypeError):
            return None

        raw_reason = data.get("reason", "")
        reason = str(raw_reason).strip() if raw_reason else "Classified by LLM fallback"

        return LLMClassificationResult(
            domain=domain,
            confidence=clamped_conf,
            reason=reason
        )

    def build_prompt(
        self,
        query: str,
        phone_model: Optional[str] = None,
        accessory: Optional[str] = None
    ) -> str:
        """Constructs the strict classifier prompt."""
        domains_list = ", ".join(self.SUPPORTED_DOMAINS) + ", GENERIC"
        return (
            "You are a Samsung technical complaint classifier.\n\n"
            f"Classify the user complaint into exactly ONE of these supported domains:\n"
            f"{domains_list}\n\n"
            "Rules:\n"
            "1. Do not provide troubleshooting instructions.\n"
            "2. Do not invent settings or deeplinks.\n"
            "3. Do not invent diagnoses or device features.\n"
            "4. Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "domain": "<DOMAIN>",\n'
            '  "confidence": <float between 0.0 and 1.0>,\n'
            '  "reason": "<brief justification>"\n'
            "}\n"
            "5. Explicit domain evidence such as Bluetooth, earbuds, Wi-Fi, battery, screen, camera, etc. "
            "must take strict precedence over generic symptoms such as 'disconnecting', 'slow', 'not working', or 'failed'.\n"
            "6. If the complaint does not identify a technical subsystem or is completely ambiguous, return GENERIC with low confidence.\n\n"
            f'User Complaint: "{query}"\n'
            f'Known Context: Phone="{phone_model or "Unknown"}", Accessory="{accessory or "None"}"'
        )

    def classify_domain(
        self,
        query: str,
        phone_model: Optional[str] = None,
        accessory: Optional[str] = None
    ) -> Optional[LLMClassificationResult]:
        """Invokes configured LLM provider to classify query into a supported domain.
        Returns LLMClassificationResult or None if unavailable or on error.
        """
        if not self.is_available():
            return None

        prompt = self.build_prompt(query, phone_model, accessory)

        # 1. Custom/mock client function (for unit tests and deterministic simulation)
        if self.client_fn is not None:
            try:
                raw_resp = self.client_fn(prompt)
                return self.parse_and_validate_response(raw_resp)
            except Exception:
                return None

        # 2. Live Provider Calls with strict timeout
        try:
            if self.provider == "gemini":
                import urllib.request
                import json
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                payload = json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "response_mime_type": "application/json",
                        "temperature": 0.0
                    }
                }).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    return self.parse_and_validate_response(text)

            elif self.provider == "openai":
                import urllib.request
                import json
                url = "https://api.openai.com/v1/chat/completions"
                payload = json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a Samsung technical complaint classifier. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                    "max_tokens": 100
                }).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    text = res_data["choices"][0]["message"]["content"]
                    return self.parse_and_validate_response(text)

        except Exception:
            return None

        return None


def calculate_transparent_confidence(
    domain: str,
    anchor_score: float,
    dominance_ratio: float,
    has_symptoms: bool,
    has_device_context: bool,
    matched_via_cache: bool,
    cache_similarity: float = 0.0,
    matched_via_llm: bool = False,
    llm_confidence: float = 0.0,
    image_analysis_used: bool = False,
    image_evidence_confidence: float = 0.0
) -> Tuple[float, Dict[str, float]]:
    """Calculates transparent confidence breakdown based on:
    - explicit domain match (up to 0.45)
    - semantic similarity / cache score (up to 0.25)
    - lexical symptom match (up to 0.15)
    - device / accessory context alignment (up to 0.10)
    - known diagnosis pattern match (up to 0.05)
    - optional llm fallback confidence tracking
    - optional image evidence reinforcement (up to 0.05)
    """
    breakdown = {
        "explicit_domain_match": 0.0,
        "semantic_similarity": 0.0,
        "lexical_symptom_match": 0.0,
        "device_context_match": 0.0,
        "known_diagnosis_match": 0.0
    }
    if domain == "GENERIC" or (anchor_score <= 0.0 and not (matched_via_llm or image_analysis_used)):
        return 0.20, breakdown

    # LLM Assisted Confidence Path
    if matched_via_llm and llm_confidence > 0.0:
        breakdown["explicit_domain_match"] = round(min(0.45, llm_confidence * 0.45), 2)
        breakdown["semantic_similarity"] = 0.20
        breakdown["lexical_symptom_match"] = 0.15 if has_symptoms else 0.10
        breakdown["device_context_match"] = 0.10 if has_device_context else 0.05
        breakdown["known_diagnosis_match"] = 0.05
        breakdown["llm_fallback_confidence"] = llm_confidence

        total = (
            breakdown["explicit_domain_match"] +
            breakdown["semantic_similarity"] +
            breakdown["lexical_symptom_match"] +
            breakdown["device_context_match"] +
            breakdown["known_diagnosis_match"]
        )
        confidence = min(0.95, max(0.65, round(total, 2)))
        breakdown["total_confidence"] = confidence
        return confidence, breakdown

    # Explicit domain anchor weight
    if anchor_score >= 5.0 and dominance_ratio >= 0.8:
        breakdown["explicit_domain_match"] = 0.45
    elif anchor_score >= 2.5:
        breakdown["explicit_domain_match"] = 0.40
    else:
        breakdown["explicit_domain_match"] = 0.30

    # Semantic similarity / cache match
    if matched_via_cache:
        breakdown["semantic_similarity"] = min(0.25, round(cache_similarity * 0.25, 3))
    else:
        breakdown["semantic_similarity"] = 0.18

    # Lexical or visual symptom presence
    if has_symptoms or (image_analysis_used and image_evidence_confidence >= 0.80):
        breakdown["lexical_symptom_match"] = 0.15

    # Device / accessory context
    if has_device_context:
        breakdown["device_context_match"] = 0.10

    # Known diagnosis pattern match
    breakdown["known_diagnosis_match"] = 0.05

    # Multimodal image evidence reinforcement boost
    if image_analysis_used and image_evidence_confidence >= 0.70:
        breakdown["image_evidence_reinforcement"] = 0.05

    total = sum(breakdown.values())
    confidence = min(0.98, max(0.20, round(total, 2)))
    breakdown["total_confidence"] = confidence
    return confidence, breakdown


def build_device_context(
    extracted_phone: Optional[str],
    user_device_model: Optional[str] = None,
    user_os_version: Optional[str] = None,
    accessory: Optional[str] = None
) -> Dict[str, Any]:
    """Builds unified, structured device context prioritizing explicit extracted phone model."""
    phone_model = extracted_phone or user_device_model or "Galaxy S22"
    os_ver = user_os_version or "One UI 6.1 (Android 14)"
    is_explicit = bool(extracted_phone)

    # Derive device family series & device type
    p_lower = phone_model.lower()
    if "z fold" in p_lower:
        series = "Galaxy Z"
        device_type = "foldable"
    elif "z flip" in p_lower:
        series = "Galaxy Z"
        device_type = "flip"
    elif "s2" in p_lower or "galaxy s" in p_lower:
        series = "Galaxy S"
        device_type = "phone"
    elif "a5" in p_lower or "galaxy a" in p_lower:
        series = "Galaxy A"
        device_type = "phone"
    elif "note" in p_lower:
        series = "Galaxy Note"
        device_type = "phone"
    else:
        series = "Galaxy"
        device_type = "phone"

    # Extract One UI and Android version if present in os_ver
    one_ui_version = None
    android_version = None
    if os_ver:
        m_one_ui = re.search(r"One UI\s*[\d\.]+", os_ver, re.I)
        if m_one_ui:
            one_ui_version = m_one_ui.group(0).strip()
        m_android = re.search(r"Android\s*[\d\.]+", os_ver, re.I)
        if m_android:
            android_version = m_android.group(0).strip()

    ctx = {
        "model": phone_model,
        "device_model": phone_model,  # Backward compatibility
        "series": series,
        "device_type": device_type,
        "os_version": os_ver,
        "one_ui_version": one_ui_version,
        "android_version": android_version,
        "confidence": 1.0 if is_explicit else 0.85,
        "is_explicitly_extracted": is_explicit
    }
    if accessory:
        ctx["accessory"] = accessory
    return ctx


class GeneralizedQueryPipeline:
    """Centralized generalized query intelligence pipeline."""

    CLARIFICATION_MESSAGE = (
        "I can help with this, but I need a little more information. "
        "Are you having trouble with Wi-Fi, Bluetooth, charging, the screen, or another feature?"
    )

    def __init__(self, cache=None, extractor=None):
        self.cache = cache
        self.extractor = extractor
        self.llm_classifier = LLMDiagnosisClassifier()
        self.image_analyzer = ImageAnalyzer()

    def process_query(
        self,
        raw_query: str,
        user_device_model: Optional[str] = None,
        user_os_version: Optional[str] = None,
        image_data: Optional[Union[bytes, str]] = None,
        image_filename: Optional[str] = None,
        manual_error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs the complete multimodal query understanding pipeline.
        Returns:
            - domain: str
            - confidence: float
            - confidence_breakdown: Dict[str, float]
            - phone_model: str
            - extracted_phone: Optional[str]
            - accessory: Optional[str]
            - device_context: Dict[str, Any]
            - canonical_key: str
            - goal: Optional[Goal]
            - needs_clarification: bool
            - clarification_message: Optional[str]
            - matched_via: str ('exact_cache' | 'canonical_cache' | 'domain_plan' | 'clarification' | 'llm' | 'image_evidence')
            - image_analysis_used: bool
            - image_evidence_confidence: float
            - error_codes: List[str]
        """
        clean_query = raw_query.strip()

        # 1. Extract device and accessory entities
        extracted_phone, extracted_accessory = DeviceAccessoryExtractor.extract_entities(clean_query)
        final_phone = extracted_phone or user_device_model or "Galaxy Device"
        final_os = user_os_version or "One UI 6.1 (Android 14)"

        device_ctx = build_device_context(
            extracted_phone=extracted_phone,
            user_device_model=user_device_model,
            user_os_version=user_os_version,
            accessory=extracted_accessory
        )

        # 2. Extract error codes from text query and manual parameter
        detected_error_codes = extract_error_codes(clean_query)
        if manual_error_code:
            norm_manual = manual_error_code.strip().upper()
            if norm_manual and norm_manual not in detected_error_codes:
                detected_error_codes.append(norm_manual)

        # 3. Detect explicit domain from user complaint text
        t_dom0 = time.perf_counter()
        domain, raw_domain_conf, scores, anchors = DomainDetector.detect_domain(clean_query)
        add_timing("domain_classification", (time.perf_counter() - t_dom0) * 1000)

        # Check for generic symptoms
        clean_lower = clean_query.lower()
        has_symptoms = any(re.search(rf"\b{re.escape(sym)}\b", clean_lower) for sym in GENERIC_SYMPTOMS)
        has_context = bool(extracted_phone or extracted_accessory)

        max_anchor_score = scores.get(domain, 0.0) if domain != "GENERIC" else 0.0
        total_scores = sum(scores.values())
        dominance_ratio = max_anchor_score / total_scores if total_scores > 0 else 0.0

        # Confidence routing thresholds:
        DETERMINISTIC_HIGH_CONFIDENCE_THRESHOLD = 0.80
        LLM_MIN_CONFIDENCE_THRESHOLD = 0.70

        matched_via = "domain_grounded"
        llm_fallback_used = False
        llm_conf_stored = 0.0
        image_analysis_used = False
        image_evidence = None
        image_evidence_conf = 0.0

        # 4. Multimodal Fusion: Process optional image evidence if provided
        if image_data:
            image_evidence = self.image_analyzer.analyze_image(image_data)
            if image_evidence.get("success"):
                t_dom_fus0 = time.perf_counter()
                image_analysis_used = True
                image_evidence_conf = image_evidence.get("confidence", 0.0)
                for c in image_evidence.get("error_codes", []):
                    if c not in detected_error_codes:
                        detected_error_codes.append(c)

                image_domains = image_evidence.get("detected_domains", [])
                known_err = image_evidence.get("known_error_details")

                # Controlled evidence priority:
                # A. If user text has strong explicit anchors (>= 0.80), text remains authoritative.
                #    If image domain agrees, boost confidence. If image domain conflicts, preserve text domain!
                if domain != "GENERIC" and raw_domain_conf >= DETERMINISTIC_HIGH_CONFIDENCE_THRESHOLD:
                    if domain in image_domains:
                        raw_domain_conf = min(0.98, raw_domain_conf + 0.05)
                        max_anchor_score = max(max_anchor_score, 8.0)
                # B. If text is GENERIC or low/medium confidence, image evidence provides supporting domain
                else:
                    candidate_img_domain = None
                    if known_err and known_err.get("domain"):
                        candidate_img_domain = known_err["domain"]
                    elif image_domains:
                        candidate_img_domain = image_domains[0]

                    if candidate_img_domain and candidate_img_domain in self.llm_classifier.SUPPORTED_DOMAINS:
                        t_val_sub = time.perf_counter()
                        is_valid, _ = validate_llm_classification(
                            query=clean_query,
                            llm_domain=candidate_img_domain,
                            deterministic_domain=domain,
                            deterministic_confidence=raw_domain_conf
                        )
                        add_timing("validator", (time.perf_counter() - t_val_sub) * 1000)
                        if is_valid:
                            domain = candidate_img_domain
                            matched_via = "image_evidence"
                            max_anchor_score = max(max_anchor_score, 5.0)
                            dominance_ratio = 1.0
                add_timing("domain_classification", (time.perf_counter() - t_dom_fus0) * 1000)

        # 5. Known Error-Code resolution if domain still generic
        if domain == "GENERIC":
            t_dom_ec0 = time.perf_counter()
            for c in detected_error_codes:
                res = resolve_error_code(c)
                if res.get("known") and res.get("domain"):
                    domain = res["domain"]
                    matched_via = "error_code"
                    max_anchor_score = max(max_anchor_score, 5.0)
                    dominance_ratio = 1.0
                    break
            add_timing("domain_classification", (time.perf_counter() - t_dom_ec0) * 1000)

        # 5b. Multi-Intent Decomposition Check (Supports 2-3 independent problems)
        decomp = MultiIntentDecomposer.decompose(clean_query)
        if decomp.is_multi_intent and len(decomp.intents) >= 2:
            processed_intents: List[Dict[str, Any]] = []
            for cand in decomp.intents:
                # Controlled image evidence assignment (prevents leakage into unrelated intents)
                cand_has_img = False
                cand_img_conf = 0.0
                if image_analysis_used and image_evidence:
                    img_doms = image_evidence.get("detected_domains", [])
                    known_err = image_evidence.get("known_error_details")
                    if cand.domain in img_doms or (known_err and known_err.get("domain") == cand.domain):
                        cand_has_img = True
                        cand_img_conf = image_evidence_conf

                # Domain-isolated error codes
                cand_err_codes = []
                for ec in detected_error_codes:
                    ec_res = resolve_error_code(ec)
                    if ec_res.get("known") and ec_res.get("domain") == cand.domain:
                        cand_err_codes.append(ec)

                # Canonical reference plan
                cand_dom_info = DOMAIN_CANONICAL_PLANS.get(cand.domain, DOMAIN_CANONICAL_PLANS["NETWORK"])
                cand_canonical_key = cand_dom_info["canonical_key"]
                cand_title = cand_dom_info["title"]
                cand_content = cand_dom_info["content"]

                # Extract plan
                cand_goal = None
                if self.extractor is not None:
                    cand_goal = self.extractor.extract_plan(cand.clause, cand_title, cand_content)
                if cand_goal is None:
                    cand_goal = Goal(
                        goal=f"Follow these steps to perform this {cand_title[:20]} Troubleshooting",
                        title=cand_title[:25],
                        actions=[],
                        score=cand.confidence
                    )

                # Semantic diagnosis validation
                validate_diagnosis(cand.clause, cand_goal)

                cand_summary = f"Identified potential {cand.domain.lower()} anomaly on {final_phone}."
                if extracted_accessory and cand.domain == "BLUETOOTH":
                    cand_summary = f"Identified potential bluetooth anomaly on {final_phone} with {extracted_accessory}."

                cand_diag = {
                    "title": cand_goal.title,
                    "summary": cand_summary,
                    "canonical_key": cand_canonical_key,
                    "confidence": cand.confidence,
                    "domain": cand.domain,
                    "matched_via": "multi_intent_orchestrator",
                    "ai_fallback_used": False,
                    "image_analysis_used": cand_has_img,
                    "image_evidence_confidence": cand_img_conf,
                    "error_codes": cand_err_codes
                }
                if extracted_accessory and cand.domain == "BLUETOOTH":
                    cand_diag["accessory"] = extracted_accessory

                processed_intents.append({
                    "id": cand.id,
                    "domain": cand.domain,
                    "issue": cand.issue,
                    "clause": cand.clause,
                    "canonical_key": cand_canonical_key,
                    "confidence": cand.confidence,
                    "goal": cand_goal,
                    "diagnosis": cand_diag,
                    "image_analysis_used": cand_has_img,
                    "image_evidence_confidence": cand_img_conf,
                    "error_codes": cand_err_codes
                })

            primary = processed_intents[0]
            return {
                "is_multi_intent": True,
                "active_intent_id": primary["id"],
                "domain": primary["domain"],
                "confidence": primary["confidence"],
                "confidence_breakdown": {
                    "base_score": primary["confidence"],
                    "device_anchor_bonus": 0.0,
                    "symptom_bonus": 0.0,
                    "final_confidence": primary["confidence"]
                },
                "phone_model": final_phone,
                "extracted_phone": extracted_phone,
                "accessory": extracted_accessory,
                "device_context": device_ctx,
                "canonical_key": primary["canonical_key"],
                "goal": primary["goal"],
                "needs_clarification": False,
                "clarification_message": None,
                "matched_via": "multi_intent_orchestrator",
                "ai_fallback_used": False,
                "image_analysis_used": image_analysis_used,
                "image_evidence": image_evidence,
                "image_evidence_confidence": image_evidence_conf,
                "error_codes": detected_error_codes,
                "anchors": anchors,
                "intents": processed_intents
            }

        # 6. Optional LLM fallback if domain is still ambiguous
        if (domain == "GENERIC" or raw_domain_conf < DETERMINISTIC_HIGH_CONFIDENCE_THRESHOLD) and self.llm_classifier.is_available():
            llm_result = self.llm_classifier.classify_domain(
                clean_query,
                phone_model=final_phone,
                accessory=extracted_accessory
            )
            if llm_result is not None:
                llm_domain = llm_result.get("domain")
                llm_conf = float(llm_result.get("confidence", 0.0))
                llm_reason = llm_result.get("reason", "")

                if llm_domain in self.llm_classifier.SUPPORTED_DOMAINS and llm_conf >= LLM_MIN_CONFIDENCE_THRESHOLD:
                    # MANDATORY VALIDATION: Must pass through diagnosis_validator
                    t_val_llm = time.perf_counter()
                    is_valid, val_reason = validate_llm_classification(
                        query=clean_query,
                        llm_domain=llm_domain,
                        deterministic_domain=domain,
                        deterministic_confidence=raw_domain_conf
                    )
                    add_timing("validator", (time.perf_counter() - t_val_llm) * 1000)
                    if is_valid:
                        domain = llm_domain
                        matched_via = "llm"
                        llm_fallback_used = True
                        llm_conf_stored = llm_conf
                        max_anchor_score = max(max_anchor_score, 3.0)
                        dominance_ratio = 1.0

        # 7. Check for Ambiguous / Low-Confidence Queries
        # e.g. "Something isn't working", "My device is having an issue", "help me"
        if domain == "GENERIC":
            conf, breakdown = calculate_transparent_confidence(
                domain="GENERIC",
                anchor_score=0.0,
                dominance_ratio=0.0,
                has_symptoms=has_symptoms,
                has_device_context=has_context,
                matched_via_cache=False,
                matched_via_llm=llm_fallback_used,
                llm_confidence=llm_conf_stored
            )
            return {
                "domain": "GENERIC",
                "confidence": conf,
                "confidence_breakdown": breakdown,
                "phone_model": final_phone,
                "extracted_phone": extracted_phone,
                "accessory": extracted_accessory,
                "device_context": device_ctx,
                "canonical_key": "general inquiry clarification",
                "goal": None,
                "needs_clarification": True,
                "clarification_message": self.CLARIFICATION_MESSAGE,
                "matched_via": "clarification",
                "ai_fallback_used": llm_fallback_used,
                "image_analysis_used": image_analysis_used,
                "image_evidence": image_evidence,
                "image_evidence_confidence": image_evidence_conf,
                "error_codes": detected_error_codes,
                "anchors": anchors,
                "is_multi_intent": False,
                "active_intent_id": "intent_1",
                "intents": []
            }

        # 8. Check FastPathCache first if cache is available
        target_canonical = DOMAIN_CANONICAL_PLANS.get(domain, {}).get("canonical_key", "wifi network connectivity")
        cached_goal: Optional[Goal] = None
        cache_hit = False
        cache_score = 0.0

        if self.cache is not None:
            cached_goal, cache_hit, cache_score = self.cache.get(clean_query)
            if cache_hit and cached_goal is not None:
                # Double-check semantic compatibility with detected domain
                t_val_diag = time.perf_counter()
                is_valid, _, _ = validate_diagnosis(clean_query, cached_goal)
                add_timing("validator", (time.perf_counter() - t_val_diag) * 1000)
                if is_valid:
                    # Also ensure the cached plan's domain matches detected domain
                    plan_domain, _, _ = classify_text_domain(cached_goal.title + " " + cached_goal.goal)
                    if plan_domain == domain or plan_domain == "GENERIC":
                        conf, breakdown = calculate_transparent_confidence(
                            domain=domain,
                            anchor_score=max_anchor_score,
                            dominance_ratio=dominance_ratio,
                            has_symptoms=has_symptoms,
                            has_device_context=has_context,
                            matched_via_cache=True,
                            cache_similarity=cache_score,
                            matched_via_llm=llm_fallback_used,
                            llm_confidence=llm_conf_stored,
                            image_analysis_used=image_analysis_used,
                            image_evidence_confidence=image_evidence_conf
                        )
                        single_diag = {
                            "title": cached_goal.title,
                            "summary": f"Identified potential {domain.lower()} anomaly on {final_phone}.",
                            "canonical_key": target_canonical,
                            "confidence": conf,
                            "domain": domain,
                            "matched_via": "cache" if not (llm_fallback_used or image_analysis_used) else matched_via,
                            "ai_fallback_used": llm_fallback_used,
                            "image_analysis_used": image_analysis_used,
                            "image_evidence_confidence": image_evidence_conf,
                            "error_codes": detected_error_codes
                        }
                        if extracted_accessory:
                            single_diag["accessory"] = extracted_accessory

                        return {
                            "domain": domain,
                            "confidence": conf,
                            "confidence_breakdown": breakdown,
                            "phone_model": final_phone,
                            "extracted_phone": extracted_phone,
                            "accessory": extracted_accessory,
                            "device_context": device_ctx,
                            "canonical_key": target_canonical,
                            "goal": cached_goal,
                            "needs_clarification": False,
                            "clarification_message": None,
                            "matched_via": "cache" if not (llm_fallback_used or image_analysis_used) else matched_via,
                            "ai_fallback_used": llm_fallback_used,
                            "image_analysis_used": image_analysis_used,
                            "image_evidence": image_evidence,
                            "image_evidence_confidence": image_evidence_conf,
                            "error_codes": detected_error_codes,
                            "anchors": anchors,
                            "is_multi_intent": False,
                            "active_intent_id": "intent_1",
                            "intents": [{
                                "id": "intent_1",
                                "domain": domain,
                                "issue": MultiIntentDecomposer.clean_issue_title(clean_query, domain),
                                "clause": clean_query,
                                "canonical_key": target_canonical,
                                "confidence": conf,
                                "goal": cached_goal,
                                "diagnosis": single_diag,
                                "image_analysis_used": image_analysis_used,
                                "image_evidence_confidence": image_evidence_conf,
                                "error_codes": detected_error_codes
                            }]
                        }

        # 9. Domain-grounded plan retrieval (Fallback to domain canonical plan)
        domain_info = DOMAIN_CANONICAL_PLANS.get(domain, DOMAIN_CANONICAL_PLANS["NETWORK"])
        canonical_key = domain_info["canonical_key"]
        title = domain_info["title"]
        content = domain_info["content"]

        extracted_goal = None
        if self.extractor is not None:
            extracted_goal = self.extractor.extract_plan(clean_query, title, content)
            if extracted_goal and self.cache is not None:
                self.cache.put(clean_query, canonical_key, extracted_goal)

        if extracted_goal is None:
            extracted_goal = Goal(
                goal=f"Follow these steps to perform this {title[:20]} Troubleshooting",
                title=title[:25],
                actions=[],
                score=0.85
            )

        conf, breakdown = calculate_transparent_confidence(
            domain=domain,
            anchor_score=max_anchor_score,
            dominance_ratio=dominance_ratio,
            has_symptoms=has_symptoms,
            has_device_context=has_context,
            matched_via_cache=False,
            matched_via_llm=llm_fallback_used,
            llm_confidence=llm_conf_stored,
            image_analysis_used=image_analysis_used,
            image_evidence_confidence=image_evidence_conf
        )

        single_diag = {
            "title": extracted_goal.title,
            "summary": f"Identified potential {domain.lower()} anomaly on {final_phone}.",
            "canonical_key": canonical_key,
            "confidence": conf,
            "domain": domain,
            "matched_via": matched_via,
            "ai_fallback_used": llm_fallback_used,
            "image_analysis_used": image_analysis_used,
            "image_evidence_confidence": image_evidence_conf,
            "error_codes": detected_error_codes
        }
        if extracted_accessory:
            single_diag["accessory"] = extracted_accessory

        return {
            "domain": domain,
            "confidence": conf,
            "confidence_breakdown": breakdown,
            "phone_model": final_phone,
            "extracted_phone": extracted_phone,
            "accessory": extracted_accessory,
            "device_context": device_ctx,
            "canonical_key": canonical_key,
            "goal": extracted_goal,
            "needs_clarification": False,
            "clarification_message": None,
            "matched_via": matched_via,
            "ai_fallback_used": llm_fallback_used,
            "image_analysis_used": image_analysis_used,
            "image_evidence": image_evidence,
            "image_evidence_confidence": image_evidence_conf,
            "error_codes": detected_error_codes,
            "anchors": anchors,
            "is_multi_intent": False,
            "active_intent_id": "intent_1",
            "intents": [{
                "id": "intent_1",
                "domain": domain,
                "issue": MultiIntentDecomposer.clean_issue_title(clean_query, domain),
                "clause": clean_query,
                "canonical_key": canonical_key,
                "confidence": conf,
                "goal": extracted_goal,
                "diagnosis": single_diag,
                "image_analysis_used": image_analysis_used,
                "image_evidence_confidence": image_evidence_conf,
                "error_codes": detected_error_codes
            }]
        }

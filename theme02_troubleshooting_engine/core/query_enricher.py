"""Query Enrichment module.
Transforms raw, colloquial customer complaints into normalized technical queries,
derives canonical cache keys, and generates 8-10 distinct paraphrases across multiple registers.
"""
import re
from typing import List, Dict, Tuple

TECH_MAPPINGS = {
    r"\b(battery dies fast|drains quickly|low battery life|battery running down|battery fast drain|battery draining|battery drain|won't charge|wont charge)\b": "battery fast drain",
    r"\b(flickers when using the camera|video flickering|camera flicker)\b": "camera video flicker",
    r"\b(screen flickers|flickering display|screen flashes|flashes extremely quickly|flicker|flashing screen)\b": "screen flicker glitch",
    r"\b(goes blank|turns completely blank|black screen|screen went black|no display|dark screen|pitch dark|dead display|screen is dark|screen stays dark|wont turn on|won't turn on|blue screen|half black|white screen|wont start up|black display)\b": "blank black display",
    r"\b(cracked|screen crack|cracked right where it folds|broken glass|crack|shattered|bleeding screen)\b": "screen physical crack",
    r"\b(swipe gesture(s)?|navigation bar|gestures? go the wrong way|swipe sideways|navigation type|gesture bar)\b": "swipe gesture navigation",
    r"\b(touch (lag|laggy|delayed|delay|not working|unresponsive|responsiveness|response|issues?)|delayed touch|sluggish touch|touchscreen)\b": "touchscreen response delay",
    r"\b(floating circle|circle hovering|shortcuts on screen|assistant menu)\b": "assistant menu shortcut",
    r"\b(smart switch|transfer data|transferring data|scan qr code)\b": "smart switch data transfer",
    r"\b(email server|email not responding|cant get email|gmail blank|open an email in gmail|email error|email|mail sync)\b": "email connection sync",
    r"\b(bluetooth|wireless headphones|galaxy buds|pairing|paired|earbuds|headphones|headset|earphones|buds2|buds pro|buds live|buds fe)\b": "bluetooth connection pairing",
    r"\b(wi-?fi|internet|network|data connection|hotspot|router|cannot load web|dns|ssid|wlan|webpages?|websites?)\b": "wifi network connectivity",
    r"\b(speaker|volume|microphone|mic|distortion|no sound|audio|crackling sound)\b": "audio speaker sound",
    r"\b(multi window|split screen|pop-up view|app pair|edge panel|multitasking)\b": "multi window split view",
    r"\b(screen mirroring|smart view|cast to tv|project to tv|mirroring|mirror phone display|smart tv)\b": "screen mirror smart view",
    r"\b(screen rotate|auto rotate|wont rotate|rotation)\b": "screen auto rotate"
}

TYPO_RULES = [
    ("screen", "scren"),
    ("battery", "batry"),
    ("display", "disply"),
    ("switch", "swtch"),
    ("phone", "fone"),
    ("settings", "setings"),
    ("gestures", "gesturs")
]


class QueryEnricher:
    def __init__(self):
        pass

    def normalize(self, raw_query: str) -> str:
        """Normalizes colloquial phrasing into a structured technical query."""
        from theme02_troubleshooting_engine.core.query_pipeline import DomainDetector

        text = re.sub(r"^\d+[\.\)]\s*", "", raw_query.strip())
        text = re.sub(r"^\"|\"$", "", text).strip()
        text_lower = text.lower()
        
        # 1. Exact regex mappings
        for pattern, tech_rep in TECH_MAPPINGS.items():
            if re.search(pattern, text_lower):
                return tech_rep

        # 2. Check explicit domain detector (prioritizes domain anchors over generic symptoms)
        domain, conf, _, _ = DomainDetector.detect_domain(text)
        if conf >= 0.5:
            if domain == "BLUETOOTH":
                return "bluetooth connection pairing"
            elif domain == "NETWORK":
                return "wifi network connectivity"
            elif domain == "BATTERY":
                return "battery fast drain"
            elif domain == "AUDIO":
                return "audio speaker sound"
            elif domain == "CAMERA":
                return "camera video flicker"
            elif domain == "EMAIL":
                return "email connection sync"
            elif domain == "DISPLAY":
                if any(w in text_lower for w in ["flicker", "flashing", "glitch"]):
                    return "screen flicker glitch"
                elif any(w in text_lower for w in ["crack", "broken", "shattered"]):
                    return "screen physical crack"
                elif any(w in text_lower for w in ["touch", "tap", "digitizer", "responsive"]):
                    return "touchscreen response delay"
                return "blank black display"
                
        # Clean fallback
        cleaned = re.sub(r"[^\w\s]", " ", text_lower)
        words = [w for w in cleaned.split() if w not in {"my", "the", "and", "is", "a", "an", "to", "in", "it"}]
        return " ".join(words[:5])

    def generate_variations(self, raw_query: str, canonical: str) -> List[str]:
        """Generates 8 to 10 distinct paraphrases across varied registers:
        formal, casual, keyword-only, frustrated, typo-inclusive.
        """
        clean_raw = re.sub(r"^\d+[\.\)]\s*", "", raw_query.strip()).strip('"')
        
        # Formal register
        v1 = f"Technical inquiry: User device experiencing {canonical} anomaly."
        v2 = f"Galaxy device report regarding {canonical} malfunction."
        
        # Casual / conversational register
        v3 = f"Hey, my {canonical} seems completely messed up on my Samsung phone."
        v4 = f"Having trouble with {canonical} after recent system usage."
        
        # Keyword-only register
        v5 = f"samsung galaxy {canonical} issue fix"
        v6 = f"{canonical} settings troubleshooting"
        
        # Frustrated register
        v7 = f"Why is my {canonical} failing again? This is so frustrating!"
        v8 = f"Urgent: {canonical} is not working at all, need help ASAP."
        
        # Typo-inclusive register
        typo_text = f"galaxy {canonical} not wrking"
        for orig, typ in TYPO_RULES:
            if orig in typo_text:
                typo_text = typo_text.replace(orig, typ)
                break
        v9 = typo_text
        v10 = f"samsng phne {canonical} glich"
        
        variations = [v1, v2, v3, v4, v5, v6, v7, v8, v9, v10]
        # Guarantee 8-10 variations
        return variations[:10]

"""Programmatic guardrails and validators for the Samsung Smart Guided Troubleshooting Engine.
Enforces 100% compliance with all schema rules, phrasing constraints, zero-leak rules, and category ordering.
"""
import re
from typing import List, Optional, Tuple, Set
from theme02_troubleshooting_engine.core.schema import (
    Goal,
    Action,
    StepGroup,
    Deeplink,
    actionCategory,
    ContextDeeplinkResponse
)

# Regex to match any web URLs, email addresses, or markdown links
URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-.]*?(?:\.com|\.org|\.net|\.edu|\.gov|\.io|\.ai|\.co)\S*|\b[a-zA-Z0-9.-]+\.(?:com|org|net|edu|gov|io|ai|co)\b[/\S]*|(?:\.com|\.org|\.net|\.edu|\.gov|\.io|\.ai|\.co)\b|\[.*?\]\(.*?\))",
    re.IGNORECASE
)

# Known critical keywords representing disruptive operations
CRITICAL_KEYWORDS = {
    "factory reset", "hard reset", "wipe", "master reset", "safe mode",
    "reboot", "restart", "recovery menu", "firmware", "software update"
}

# Known manual keywords representing physical interventions
MANUAL_KEYWORDS = {
    "service center", "repair", "replace", "technician", "clean",
    "charging port", "moisture", "liquid damage", "eject", "flashlight",
    "sim tray", "inspection", "cable", "mouse", "keyboard", "adapter"
}

DUMMY_POSITIVE_URI = "bixby://dummy_positive"


def sanitize_text(text: str, preserve_newlines: bool = False) -> str:
    """Removes all web URLs, markdown links, and extraneous whitespace."""
    if not text:
        return ""
    cleaned = URL_PATTERN.sub("", text)
    if preserve_newlines:
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned).strip()
    else:
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Strip any trailing punctuation residue left by removed links
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned


STOPWORDS_FOR_TITLE = {
    "on", "a", "an", "the", "to", "or", "in", "for", "with", "your",
    "phone", "tablet", "samsung", "galaxy", "device", "some", "things", "first"
}


def normalize_title(title: str, fallback_topic: str = "Device issue") -> str:
    """Enforces 2 to 3 words, sentence case (e.g., 'Swipe navigation settings', 'Screen display damage')."""
    raw_words = sanitize_text(title).split()
    if not raw_words:
        raw_words = fallback_topic.split()

    # Filter out weak filler words while preserving key diagnostic terms
    filtered = [w for w in raw_words if w.lower() not in STOPWORDS_FOR_TITLE]
    if len(filtered) < 2:
        filtered = raw_words

    if len(filtered) < 2:
        filtered.append("settings")
    elif len(filtered) > 3:
        filtered = filtered[:3]

    title_str = " ".join(filtered)
    # Sentence case: First letter capitalized, rest lowercase
    title_sentence_case = title_str[0].upper() + title_str[1:].lower()
    return title_sentence_case


def normalize_goal(goal_or_topic: str) -> str:
    """Enforces exact syntax: 'Follow these steps to perform this <Topic> Troubleshooting'."""
    goal_or_topic = sanitize_text(goal_or_topic)
    
    # Check if already follows format
    m = re.match(r"^Follow these steps to perform this (.+?) (Troubleshooting|Configuration)$", goal_or_topic, re.IGNORECASE)
    if m:
        topic = m.group(1).strip()
        kind = m.group(2).capitalize()
        return f"Follow these steps to perform this {topic} {kind}"
    
    # If it has "Troubleshooting" or "Configuration" at the end
    topic = goal_or_topic
    kind = "Troubleshooting"
    if topic.lower().endswith("troubleshooting"):
        topic = topic[:-15].strip()
        kind = "Troubleshooting"
    elif topic.lower().endswith("configuration"):
        topic = topic[:-13].strip()
        kind = "Configuration"
    
    # Remove phrases like "Follow these steps to perform this"
    topic = re.sub(r"^follow\s+these\s+steps\s+(to\s+perform\s+this\s+)?", "", topic, flags=re.IGNORECASE).strip()
    if not topic:
        topic = "Screen Display"
    
    # Format topic title case
    topic = " ".join(w.capitalize() for w in topic.split())
    return f"Follow these steps to perform this {topic} {kind}"


def normalize_description(desc: str, fallback_action: str = "resolve issue") -> str:
    """Enforces: Exactly 5 to 7 words, starting with 'It will'."""
    desc = sanitize_text(desc)
    words = desc.split()
    
    # Ensure it starts with "It will"
    if len(words) >= 2 and words[0].lower() == "it" and words[1].lower() == "will":
        pass
    else:
        # Prepend "It will"
        # If starts with "It" or "Will", clean up
        if words and words[0].lower() in {"it", "will", "this", "to"}:
            words = words[1:]
        words = ["It", "will"] + words
    
    words[0] = "It"
    words[1] = "will"
    
    # Enforce exactly 5 to 7 words
    if len(words) < 5:
        padding = ["help", "optimize", "device", "performance", "settings"]
        for p in padding:
            if len(words) >= 5:
                break
            if p not in [w.lower() for w in words]:
                words.append(p)
    elif len(words) > 7:
        words = words[:7]
    
    # Final word formatting
    result = " ".join(words)
    # Ensure clean ending (no trailing punctuation that breaks words)
    result = result.rstrip(".,;:!?")
    return result


def determine_category(
    action_name: str,
    steps: List[str],
    has_actionable_deeplink: bool
) -> actionCategory:
    """Determines action category: auto, manual, or critical."""
    full_text = f"{action_name} " + " ".join(steps)
    name_lower = action_name.lower()
    full_lower = full_text.lower()
    
    # 1. Critical operations: disruptive or irreversible operations (must be ordered last)
    if any(kw in name_lower for kw in CRITICAL_KEYWORDS):
        return actionCategory.critical

    # 2. Manual operations: physical interventions (cannot carry actionable deeplink)
    if any(kw in name_lower for kw in MANUAL_KEYWORDS):
        return actionCategory.manual

    # 3. If actionable deeplink is present -> auto
    if has_actionable_deeplink:
        return actionCategory.auto

    # 4. Secondary checks in steps if name was generic
    if any(kw in full_lower for kw in CRITICAL_KEYWORDS):
        return actionCategory.critical
        
    return actionCategory.manual


def order_actions(actions: List[Action]) -> List[Action]:
    """Orders actions by disruption hierarchy:
    1. auto (safe settings toggles)
    2. manual (physical inspection / external actions)
    3. critical (restarts, safe mode, resets - MUST be ordered last)
    """
    category_order = {
        actionCategory.auto: 0,
        actionCategory.manual: 1,
        actionCategory.critical: 2
    }
    return sorted(actions, key=lambda a: category_order.get(a.category, 1))


def validate_and_sanitize_goal(
    goal_obj: Goal,
    valid_deeplink_catalog_uris: Optional[Set[str]] = None
) -> Goal:
    """Applies end-to-end programmatic guardrails to a Goal object."""
    # 1. Goal syntax
    goal_obj.goal = normalize_goal(goal_obj.goal)
    
    # 2. Title (2-3 words sentence case)
    goal_obj.title = normalize_title(goal_obj.title)
    
    # 3. Score bounded 0.0 - 1.0
    goal_obj.score = max(0.0, min(1.0, float(goal_obj.score)))
    
    sanitized_actions: List[Action] = []
    
    for action in goal_obj.actions:
        # Title case action name
        name_clean = sanitize_text(action.actionName)
        action_name = " ".join(w.capitalize() for w in name_clean.split())
        
        # 5-7 words description starting with "It will"
        description = normalize_description(action.description, fallback_action=action_name)
        
        sanitized_step_groups: List[StepGroup] = []
        has_actionable_deeplink = False
        
        for sg in action.stepGroups:
            cleaned_steps: List[str] = []
            for st in sg.steps:
                cleaned_st = sanitize_text(st)
                if cleaned_st:
                    cleaned_steps.append(cleaned_st)
            
            if not cleaned_steps:
                continue
                
            # Validate actionable deeplink
            actionable = sg.actionableDeeplink
            if actionable is not None:
                uri = actionable.deeplink.strip()
                # Check against catalog if provided
                if valid_deeplink_catalog_uris:
                    if uri not in valid_deeplink_catalog_uris and uri != DUMMY_POSITIVE_URI:
                        # Fallback to dummy positive
                        actionable.deeplink = DUMMY_POSITIVE_URI
                
                # Sanitize text fields
                actionable.description = sanitize_text(actionable.description)
                if actionable.message:
                    actionable.message = sanitize_text(actionable.message)
                has_actionable_deeplink = True
                
            validation = sg.validationDeeplink
            if validation is not None:
                if valid_deeplink_catalog_uris and validation.deeplink not in valid_deeplink_catalog_uris:
                    validation = None
            
            sanitized_step_groups.append(
                StepGroup(
                    steps=cleaned_steps,
                    validationDeeplink=validation,
                    actionableDeeplink=actionable
                )
            )
            
        if not sanitized_step_groups:
            continue
            
        all_steps = [s for sg in sanitized_step_groups for s in sg.steps]
        category = determine_category(action_name, all_steps, has_actionable_deeplink)
        
        # Non-negotiable constraint: manual actions CANNOT carry an actionable deeplink
        if category == actionCategory.manual:
            for sg in sanitized_step_groups:
                sg.actionableDeeplink = None
                sg.validationDeeplink = None
        
        sanitized_actions.append(
            Action(
                actionName=action_name,
                description=description,
                stepGroups=sanitized_step_groups,
                category=category
            )
        )
        
    # Order actions: auto first -> manual -> critical last
    ordered_actions = order_actions(sanitized_actions)
    goal_obj.actions = ordered_actions
    
    return goal_obj

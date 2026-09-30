"""Structured Knowledge Extractor.
Parses unstructured SIIS customer-care articles into atomic, screen-specific actions
grounded purely in the provided source text (no hallucination), attaches deeplinks,
and formats them into validated Goal models.
"""
import re
from typing import Dict, List, Optional, Any
from theme02_troubleshooting_engine.core.schema import (
    Goal,
    Action,
    StepGroup,
    actionCategory,
    Deeplink,
    ValidationDeepLink
)
from theme02_troubleshooting_engine.core.deeplink_retriever import DeeplinkRetriever
from theme02_troubleshooting_engine.core.guardrails import (
    validate_and_sanitize_goal,
    sanitize_text,
    normalize_title,
    normalize_goal,
    normalize_description,
    CRITICAL_KEYWORDS,
    MANUAL_KEYWORDS
)


class StructuredExtractor:
    def __init__(self, deeplink_retriever: DeeplinkRetriever):
        self.retriever = deeplink_retriever

    def parse_siis_sections(self, content: str) -> List[Dict[str, Any]]:
        """Splits SIIS content into logical step sections based on markdown headers or numbered steps."""
        # Clean content while preserving newlines for markdown header parsing
        clean_content = sanitize_text(content, preserve_newlines=True)
        # Also clean metadata prefixes like "Smartphone,Others Mobile...): "
        clean_content = re.sub(r"^[^\n#]+?\):\s*", "", clean_content)
        
        # 1. Try markdown headers (## Step 1, ### 1., ## Heading)
        matches = list(re.finditer(r"(?:^|\n)#{1,4}\s+([^\n]+)", clean_content))
        
        # 2. If no markdown headers, try numbered steps
        if not matches:
            matches = list(re.finditer(r"(?:^|\n)(?:Step\s*\d+[:.]?|\d+[\.\)])\s+([^\n]+)", clean_content))

        sections = []
        if not matches:
            # Fallback: Split by double newlines into paragraphs
            paras = [p.strip() for p in clean_content.split("\n\n") if len(p.strip()) > 30]
            for i, p in enumerate(paras[:5], 1):
                first_sentence = p.split(".")[0].strip()
                sections.append({
                    "title": first_sentence[:45],
                    "body": p
                })
            return sections

        for i, match in enumerate(matches):
            header = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(clean_content)
            body = clean_content[start:end].strip()

            # Skip metadata or glossary headers
            if any(skip_kw in header.lower() for skip_kw in ["glossary", "important notes", "requirements", "troubleshooting email connection issues"]):
                continue

            if body:
                sections.append({
                    "title": header,
                    "body": body
                })

        return sections

    def extract_atomic_steps(self, body: str) -> List[str]:
        """Deconstructs section body into clear, atomic UI instructions (one interaction per step)."""
        raw_lines = body.split("\n")
        steps = []
        for line in raw_lines:
            line_clean = line.strip(" -*#\t")
            if not line_clean:
                continue
            # Remove leading numbers like "1. ", "2. "
            line_clean = re.sub(r"^\d+[\.\)]\s*", "", line_clean).strip()
            
            # Split compound lines with semicolons or sentences if describing multiple actions
            sub_sentences = re.split(r"(?<=[.!?])\s+", line_clean)
            for s in sub_sentences:
                s_stripped = s.strip()
                s_lower = s_stripped.lower()
                # Skip conversational commentary or image captions
                if (
                    len(s_stripped) > 8
                    and not s_lower.startswith("note:")
                    and not s_lower.startswith("glossary")
                    and not s_lower.startswith("hello!")
                    and not s_lower.startswith("normal ldis")
                    and not s_lower.startswith("an ldi exposed")
                ):
                    steps.append(s_stripped)

        # Dedup while preserving order
        unique_steps = []
        for s in steps:
            if s not in unique_steps:
                unique_steps.append(s)

        # Return granular steps (up to 5 per action screen)
        return unique_steps[:5]

    def _generate_benefit_description(self, action_name: str) -> str:
        """Generates a plain language benefit starting with 'It will' strictly 5 to 7 words."""
        name_lower = action_name.lower()
        if "cache" in name_lower or "storage" in name_lower:
            return "It will clear cached application temporary data"
        if "restart" in name_lower or "reboot" in name_lower:
            return "It will restart your mobile device safely"
        if "safe mode" in name_lower:
            return "It will isolate third party application conflicts"
        if "wi-fi" in name_lower or "internet" in name_lower or "network" in name_lower:
            return "It will verify active internet network connectivity"
        if "damage" in name_lower or "physical" in name_lower or "inspect" in name_lower:
            return "It will inspect device hardware for damage"
        if "charge" in name_lower or "battery" in name_lower:
            return "It will restore optimal battery charge level"
        if "smart switch" in name_lower or "transfer" in name_lower:
            return "It will facilitate secure wireless data transfer"
        if "rotate" in name_lower or "orientation" in name_lower:
            return "It will adjust device screen orientation settings"
        if "multi window" in name_lower or "split" in name_lower:
            return "It will enable multitasking split screen view"
        if "mirror" in name_lower or "cast" in name_lower or "smart view" in name_lower:
            return "It will mirror screen to smart display"
        if "service" in name_lower or "repair" in name_lower or "support" in name_lower:
            return "It will connect with authorized service technicians"
            
        return normalize_description(f"It will help you configure {action_name.lower()}")

    def extract_plan(
        self,
        query: str,
        siis_title: str,
        siis_content: str
    ) -> Optional[Goal]:
        """Extracts and validates a full Goal object from SIIS text."""
        if not siis_content or len(siis_content.strip()) < 20:
            return None

        sections = self.parse_siis_sections(siis_content)
        if not sections:
            return None

        actions: List[Action] = []

        for sec in sections:
            sec_title = sec["title"]
            # Clean title e.g. "Step 1: Check Email Access on a PC" -> "Check Email Access on a PC"
            clean_name = re.sub(r"^(Step\s*\d+[:.]?|\d+[\.\)]\s*)", "", sec_title, flags=re.IGNORECASE).strip()
            clean_name = " ".join(w.capitalize() for w in clean_name.split())
            if not clean_name or len(clean_name) < 3:
                clean_name = "Device Configuration Screen"

            steps = self.extract_atomic_steps(sec["body"])
            if not steps:
                continue

            # Resolve deeplink for this specific screen/action
            combined_step_text = " ".join(steps[:3])
            
            # Check if this action is inherently manual or critical
            is_manual = any(kw in f"{clean_name} {combined_step_text}".lower() for kw in MANUAL_KEYWORDS)
            is_critical = any(kw in f"{clean_name} {combined_step_text}".lower() for kw in CRITICAL_KEYWORDS)

            if is_manual:
                actionable_dl = None
                validation_dl = None
                category = actionCategory.manual
            elif is_critical:
                actionable_dl, validation_dl = self.retriever.resolve_step_deeplink(
                    clean_name,
                    combined_step_text,
                    context_hints=siis_title
                )
                category = actionCategory.critical
            else:
                actionable_dl, validation_dl = self.retriever.resolve_step_deeplink(
                    clean_name,
                    combined_step_text,
                    context_hints=siis_title
                )
                category = actionCategory.auto if actionable_dl is not None else actionCategory.manual

            action_desc = self._generate_benefit_description(clean_name)

            step_group = StepGroup(
                steps=steps,
                actionableDeeplink=actionable_dl,
                validationDeeplink=validation_dl
            )

            actions.append(
                Action(
                    actionName=clean_name,
                    description=action_desc,
                    stepGroups=[step_group],
                    category=category
                )
            )

        if not actions:
            return None

        topic = normalize_title(siis_title)
        goal_text = f"Follow these steps to perform this {topic} Troubleshooting"

        raw_goal = Goal(
            goal=goal_text,
            title=topic,
            actions=actions,
            score=0.94
        )

        # Run through end-to-end programmatic guardrails
        validated_goal = validate_and_sanitize_goal(
            raw_goal,
            valid_deeplink_catalog_uris=self.retriever.valid_uris
        )

        return validated_goal

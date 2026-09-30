"""Multi-Intent Decomposition and Orchestration Engine.
Decomposes compound troubleshooting queries containing multiple independent problems
(e.g., 'My Wi-Fi keeps disconnecting and my Bluetooth earbuds won't connect') into
discrete, domain-grounded intent candidates while reusing trusted canonical diagnostic flows.
"""
import re
from typing import Dict, List, Optional, Tuple, Any, Set
from pydantic import BaseModel, Field

from theme02_troubleshooting_engine.core.error_code_resolver import extract_error_codes, resolve_error_code


class IntentCandidate(BaseModel):
    """Represents a discrete troubleshooting intent decomposed from a compound user query."""
    id: str
    clause: str
    domain: str
    confidence: float
    issue: str
    anchor_score: float
    canonical_key: Optional[str] = None
    detected_anchors: List[str] = Field(default_factory=list)


class MultiIntentResult(BaseModel):
    """Result of multi-intent analysis for a query."""
    is_multi_intent: bool
    intents: List[IntentCandidate] = Field(default_factory=list)
    raw_query: str


class MultiIntentDecomposer:
    """Decomposes multi-problem complaints into distinct domain-isolated intent candidates.
    Guarantees:
    1. Maximum 3 intents returned.
    2. Same-domain issues merged into a single intent (never duplicated).
    3. Never invents a domain when evidence is insufficient.
    4. Sub-clauses without domain anchors are merged with adjacent clauses.
    """

    # Clause boundary delimiters and coordinating conjunctions
    SPLIT_PATTERN = re.compile(
        r"(?:;\s*|\.\s+|\n+)"  # Semicolons, periods, newlines
        r"|(?:\s*,\s*(?:and\s+also|as\s+well\s+as|additionally|meanwhile|plus|and|also)\s*)"
        r"|(?:\s+(?:and\s+also|as\s+well\s+as|additionally|meanwhile|plus|and|also)\s+)"
        r"|(?:\s*,\s*)",  # Commas
        re.IGNORECASE
    )

    # Lead-in filler words to clean from issue summaries
    LEAD_IN_PATTERN = re.compile(
        r"^(?:my|the|also|and|plus|additionally|meanwhile|help(?:\s+me)?(?:\s+with)?|please|having\s+trouble\s+with|issue\s+with)\s+",
        re.IGNORECASE
    )

    # Domain to friendly default issue name
    DOMAIN_DEFAULT_ISSUES = {
        "NETWORK": "Wi-Fi disconnecting",
        "BLUETOOTH": "Bluetooth connection failure",
        "BATTERY": "Battery fast drain",
        "DISPLAY": "Screen display anomaly",
        "AUDIO": "Audio speaker sound issue",
        "CAMERA": "Camera malfunction",
        "EMAIL": "Email synchronization error",
        "SYSTEM": "System navigation gesture issue"
    }

    @classmethod
    def clean_issue_title(cls, clause: str, domain: str) -> str:
        """Derives a concise, human-friendly issue summary from a clause."""
        cleaned = clause.strip()
        # Remove lead-in fillers
        for _ in range(3):
            cleaned = cls.LEAD_IN_PATTERN.sub("", cleaned).strip()

        # Remove trailing punctuation
        cleaned = re.sub(r"[\.,;!?]+$", "", cleaned).strip()

        if len(cleaned) < 4 or cleaned.lower() in {"wifi", "wi-fi", "bluetooth", "battery", "screen", "camera"}:
            return cls.DOMAIN_DEFAULT_ISSUES.get(domain, f"{domain.capitalize()} issue")

        # Capitalize first character
        return cleaned[0].upper() + cleaned[1:]

    @classmethod
    def decompose(cls, query: str) -> MultiIntentResult:
        """Analyzes and decomposes query into candidate intents.
        Returns MultiIntentResult with is_multi_intent = True only if at least 2
        confidently distinct domains are found.
        """
        from theme02_troubleshooting_engine.core.query_pipeline import (
            DomainDetector,
            DOMAIN_CANONICAL_PLANS,
            DOMAIN_ANCHORS
        )

        clean_query = query.strip()
        if not clean_query:
            return MultiIntentResult(is_multi_intent=False, intents=[], raw_query=query)

        # 1. Split raw text into candidate raw fragments
        raw_parts = [p.strip() for p in cls.SPLIT_PATTERN.split(clean_query) if p and p.strip()]

        if not raw_parts:
            raw_parts = [clean_query]

        # 2. Score each fragment for domain anchors
        fragment_data: List[Dict[str, Any]] = []
        for part in raw_parts:
            dom, conf, scores, anchors = DomainDetector.detect_domain(part)
            max_score = scores.get(dom, 0.0) if dom != "GENERIC" else 0.0
            
            # Check for error codes in this part
            ecodes = extract_error_codes(part)
            ec_domain = None
            if ecodes:
                for ec in ecodes:
                    ec_res = resolve_error_code(ec)
                    if ec_res.get("known") and ec_res.get("domain"):
                        ec_domain = ec_res["domain"]
                        break
            
            if ec_domain and dom == "GENERIC":
                dom = ec_domain
                conf = 0.95
                max_score = 5.0
                anchors.append(ecodes[0])

            fragment_data.append({
                "clause": part,
                "domain": dom,
                "confidence": conf,
                "anchor_score": max_score,
                "anchors": anchors
            })

        # 3. Merge orphan fragments (fragments without domain anchors) into adjacent anchored fragments
        merged_fragments: List[Dict[str, Any]] = []
        for item in fragment_data:
            if item["domain"] != "GENERIC" and item["anchor_score"] >= 2.0:
                merged_fragments.append(item)
            else:
                # Orphan fragment without domain anchor
                if merged_fragments:
                    # Append to previous anchored fragment
                    merged_fragments[-1]["clause"] += " and " + item["clause"]
                else:
                    # Keep as initial fragment, might be merged with next
                    merged_fragments.append(item)

        # If initial fragment was GENERIC and subsequent fragment had anchor, merge forward
        if len(merged_fragments) > 1 and merged_fragments[0]["domain"] == "GENERIC":
            first = merged_fragments.pop(0)
            merged_fragments[0]["clause"] = first["clause"] + ", " + merged_fragments[0]["clause"]

        # 4. Group by domain to enforce same-domain deduplication
        # e.g., "Wi-Fi is slow and Wi-Fi disconnects" must merge into ONE NETWORK intent
        domain_groups: Dict[str, Dict[str, Any]] = {}
        for item in merged_fragments:
            dom = item["domain"]
            if dom == "GENERIC":
                continue
            if dom not in domain_groups:
                domain_groups[dom] = {
                    "clauses": [item["clause"]],
                    "domain": dom,
                    "confidence": item["confidence"],
                    "anchor_score": item["anchor_score"],
                    "anchors": list(item["anchors"])
                }
            else:
                # Merge same-domain clauses
                domain_groups[dom]["clauses"].append(item["clause"])
                domain_groups[dom]["confidence"] = max(domain_groups[dom]["confidence"], item["confidence"])
                domain_groups[dom]["anchor_score"] += item["anchor_score"]
                domain_groups[dom]["anchors"].extend(item["anchors"])

        # 5. Check if we have at least 2 distinct domains
        if len(domain_groups) < 2:
            # Single intent or generic
            # Re-check whole query domain to be safe
            w_dom, w_conf, w_scores, w_anchors = DomainDetector.detect_domain(clean_query)
            # Check whole-query error codes
            w_ecodes = extract_error_codes(clean_query)
            if w_dom == "GENERIC" and w_ecodes:
                for ec in w_ecodes:
                    res = resolve_error_code(ec)
                    if res.get("known") and res.get("domain"):
                        w_dom = res["domain"]
                        w_conf = 0.95
                        break

            if w_dom != "GENERIC":
                issue_title = cls.clean_issue_title(clean_query, w_dom)
                target_can = DOMAIN_CANONICAL_PLANS.get(w_dom, {}).get("canonical_key", "device issue")
                single_cand = IntentCandidate(
                    id="intent_1",
                    clause=clean_query,
                    domain=w_dom,
                    confidence=round(w_conf, 2),
                    issue=issue_title,
                    anchor_score=w_scores.get(w_dom, 0.0),
                    canonical_key=target_can,
                    detected_anchors=w_anchors
                )
                return MultiIntentResult(
                    is_multi_intent=False,
                    intents=[single_cand],
                    raw_query=query
                )
            else:
                return MultiIntentResult(
                    is_multi_intent=False,
                    intents=[],
                    raw_query=query
                )

        # 6. We have 2 or more distinct domains!
        # Select top domains by anchor score (cap at 3)
        top_by_score = sorted(
            domain_groups.values(),
            key=lambda x: x["anchor_score"],
            reverse=True
        )[:3]

        # Order the selected intents by their first appearance in the original query
        def get_pos(g):
            dom_name = g["domain"].lower()
            idx = clean_query.lower().find(dom_name)
            if idx == -1:
                # check anchor strings
                for a in g.get("anchors", []):
                    a_idx = clean_query.lower().find(a.lower())
                    if a_idx != -1:
                        return a_idx
                return 9999
            return idx

        sorted_domains = sorted(top_by_score, key=get_pos)

        intents: List[IntentCandidate] = []
        for idx, g in enumerate(sorted_domains, start=1):
            dom = g["domain"]
            combined_clause = " and ".join(g["clauses"])
            issue_title = cls.clean_issue_title(combined_clause, dom)
            target_can = DOMAIN_CANONICAL_PLANS.get(dom, {}).get("canonical_key", "device issue")

            intents.append(IntentCandidate(
                id=f"intent_{idx}",
                clause=combined_clause,
                domain=dom,
                confidence=round(min(0.98, max(0.85, g["confidence"])), 2),
                issue=issue_title,
                anchor_score=g["anchor_score"],
                canonical_key=target_can,
                detected_anchors=list(set(g["anchors"]))
            ))

        return MultiIntentResult(
            is_multi_intent=True,
            intents=intents,
            raw_query=query
        )

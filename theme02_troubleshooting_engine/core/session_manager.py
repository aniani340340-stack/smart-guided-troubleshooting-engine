"""Thread-Safe In-Memory Session Manager for Interactive Guided Troubleshooting.
Tracks session state, execution history, dynamic branching, resolution, and escalation.
Supports single-intent and multi-intent troubleshooting orchestration with strict isolation.
"""
import time
import uuid
import threading
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from theme02_troubleshooting_engine.core.schema import Goal
from theme02_troubleshooting_engine.core.diagnostic_flow import DiagnosticFlow, DiagnosticStepNode, build_flow_from_goal


class IntentSessionState(BaseModel):
    """Tracks state and diagnostic flow for an individual intent in a multi-intent session."""
    id: str
    domain: str
    issue: str
    title: str
    canonical_key: str
    confidence: float = 0.95
    diagnosis: Dict[str, Any] = Field(default_factory=dict)
    flow: Optional[DiagnosticFlow] = None
    status: str = "ACTIVE"  # ACTIVE, PENDING, RESOLVED, ESCALATED
    completed_steps: List[Dict[str, Any]] = Field(default_factory=list)
    failed_steps: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_summary: Optional[Dict[str, Any]] = None
    escalation_summary: Optional[Dict[str, Any]] = None
    image_analysis_used: bool = False
    image_evidence_confidence: float = 0.0
    error_codes: List[str] = Field(default_factory=list)

    def get_progress(self) -> Dict[str, int]:
        total = self.flow.total_main_steps if self.flow else 1
        current = len(self.completed_steps) + len(self.failed_steps) + 1
        current = min(current, total) if self.status in {"ACTIVE", "PENDING"} else total
        return {"current": current, "total": total}

    def get_current_step(self) -> Optional[Dict[str, Any]]:
        if self.status in {"RESOLVED", "ESCALATED"} or not self.flow:
            return None
        node = self.flow.get_current_node()
        if not node:
            return None
        return node.model_dump()


class TroubleshootingSession(BaseModel):
    session_id: str
    query: str
    device_context: Optional[Dict[str, Any]] = None
    current_goal: Optional[Dict[str, Any]] = None
    current_action_index: int = 0
    current_step_index: int = 0
    completed_steps: List[Dict[str, Any]] = Field(default_factory=list)
    failed_steps: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE, RESOLVED, ESCALATED, FAILED
    diagnosis: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    flow: Optional[DiagnosticFlow] = None
    resolution_summary: Optional[Dict[str, Any]] = None
    escalation_summary: Optional[Dict[str, Any]] = None
    is_multi_intent: bool = False
    active_intent_id: Optional[str] = None
    intents: List[IntentSessionState] = Field(default_factory=list)

    def get_active_intent(self) -> Optional[IntentSessionState]:
        if not self.intents:
            return None
        if self.active_intent_id:
            for it in self.intents:
                if it.id == self.active_intent_id:
                    return it
        return self.intents[0]

    def get_progress(self) -> Dict[str, int]:
        if self.is_multi_intent and self.intents:
            active = self.get_active_intent()
            if active:
                return active.get_progress()
        total = self.flow.total_main_steps if self.flow else 1
        current = len(self.completed_steps) + len(self.failed_steps) + 1
        current = min(current, total) if self.status == "ACTIVE" else total
        return {"current": current, "total": total}

    def get_current_step(self) -> Optional[Dict[str, Any]]:
        if self.is_multi_intent and self.intents:
            if self.status in {"RESOLVED", "ESCALATED"}:
                return None
            active = self.get_active_intent()
            if active:
                return active.get_current_step()
            return None
        if self.status != "ACTIVE" or not self.flow:
            return None
        node = self.flow.get_current_node()
        if not node:
            return None
        return node.model_dump()

    def get_intents_summary(self) -> List[Dict[str, Any]]:
        res = []
        for it in self.intents:
            res.append({
                "id": it.id,
                "domain": it.domain,
                "issue": it.issue,
                "title": it.title,
                "canonical_key": it.canonical_key,
                "confidence": it.confidence,
                "status": it.status,
                "progress": it.get_progress(),
                "current_step": it.get_current_step(),
                "diagnosis": it.diagnosis,
                "completed_steps": it.completed_steps,
                "failed_steps": it.failed_steps,
                "resolved": (it.status == "RESOLVED"),
                "escalated": (it.status == "ESCALATED"),
                "resolution_summary": it.resolution_summary,
                "escalation_summary": it.escalation_summary,
                "image_analysis_used": it.image_analysis_used,
                "image_evidence_confidence": it.image_evidence_confidence,
                "error_codes": it.error_codes
            })
        return res


class SessionManager:
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(SessionManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._lock = threading.RLock()
        self._sessions: Dict[str, TroubleshootingSession] = {}
        self._initialized = True

    def create_session(
        self,
        query: str,
        diagnosis: Dict[str, Any],
        goal: Optional[Goal] = None,
        device_context: Optional[Dict[str, Any]] = None,
        flow: Optional[DiagnosticFlow] = None,
        is_multi_intent: bool = False,
        active_intent_id: Optional[str] = None,
        intents: Optional[List[Dict[str, Any]]] = None
    ) -> TroubleshootingSession:
        """Creates a new thread-safe diagnostic session (single or multi-intent)."""
        session_id = str(uuid.uuid4())
        canonical_key = diagnosis.get("canonical_key", "device issue")
        now = time.time()

        if is_multi_intent and intents:
            intent_states: List[IntentSessionState] = []
            for idx, item in enumerate(intents):
                cand_goal = item.get("goal")
                cand_flow = build_flow_from_goal(
                    cand_goal,
                    item.get("clause", query),
                    item.get("canonical_key", "device issue")
                ) if cand_goal else None

                init_status = "ACTIVE" if idx == 0 else "PENDING"
                it_state = IntentSessionState(
                    id=item["id"],
                    domain=item["domain"],
                    issue=item.get("issue", f"{item['domain']} issue"),
                    title=cand_goal.title if cand_goal else item.get("issue", "Issue"),
                    canonical_key=item.get("canonical_key", "device issue"),
                    confidence=item.get("confidence", 0.95),
                    diagnosis=item.get("diagnosis", {}),
                    flow=cand_flow,
                    status=init_status,
                    image_analysis_used=item.get("image_analysis_used", False),
                    image_evidence_confidence=item.get("image_evidence_confidence", 0.0),
                    error_codes=item.get("error_codes", [])
                )
                intent_states.append(it_state)

            primary_intent = intent_states[0] if intent_states else None
            active_id = active_intent_id or (primary_intent.id if primary_intent else "intent_1")

            session = TroubleshootingSession(
                session_id=session_id,
                query=query,
                device_context=device_context or {},
                current_goal=primary_intent.diagnosis if primary_intent else (goal.model_dump() if goal else None),
                current_action_index=0,
                current_step_index=0,
                completed_steps=[],
                failed_steps=[],
                status="ACTIVE",
                diagnosis=primary_intent.diagnosis if primary_intent else diagnosis,
                created_at=now,
                updated_at=now,
                flow=primary_intent.flow if primary_intent else flow,
                is_multi_intent=True,
                active_intent_id=active_id,
                intents=intent_states
            )
            with self._lock:
                self._sessions[session_id] = session
                return session

        # Single-intent flow creation
        if flow is None and goal is not None:
            flow = build_flow_from_goal(goal, query, canonical_key)

        goal_dict = goal.model_dump() if goal is not None else None

        single_intent_state = None
        if diagnosis:
            single_intent_state = IntentSessionState(
                id="intent_1",
                domain=diagnosis.get("domain", "DEVICE"),
                issue=diagnosis.get("title", "Device Issue"),
                title=diagnosis.get("title", "Device Issue"),
                canonical_key=canonical_key,
                confidence=diagnosis.get("confidence", 0.95),
                diagnosis=diagnosis,
                flow=flow,
                status="ACTIVE"
            )

        session = TroubleshootingSession(
            session_id=session_id,
            query=query,
            device_context=device_context or {},
            current_goal=goal_dict,
            current_action_index=0,
            current_step_index=0,
            completed_steps=[],
            failed_steps=[],
            status="ACTIVE",
            diagnosis=diagnosis,
            created_at=now,
            updated_at=now,
            flow=flow,
            is_multi_intent=False,
            active_intent_id="intent_1",
            intents=[single_intent_state] if single_intent_state else []
        )

        with self._lock:
            self._sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[TroubleshootingSession]:
        """Retrieves a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def advance_session(
        self,
        session_id: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
        intent_id: Optional[str] = None
    ) -> Optional[TroubleshootingSession]:
        """Advances the session to the next diagnostic branch based on result ('passed', 'failed', 'skipped')."""
        return self.record_feedback(session_id, result, details, intent_id=intent_id)

    def switch_active_intent(
        self,
        session_id: str,
        intent_id: str
    ) -> TroubleshootingSession:
        """Switches the active intent view in a multi-intent session without resetting state."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise KeyError(f"Session '{session_id}' not found.")

            if not session.is_multi_intent or not session.intents:
                return session

            target_intent = next((it for it in session.intents if it.id == intent_id), None)
            if not target_intent:
                raise KeyError(f"Intent '{intent_id}' not found in session '{session_id}'.")

            session.active_intent_id = intent_id
            if target_intent.status == "PENDING":
                target_intent.status = "ACTIVE"

            session.flow = target_intent.flow
            session.diagnosis = target_intent.diagnosis
            session.updated_at = time.time()
            return session

    def record_feedback(
        self,
        session_id: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
        intent_id: Optional[str] = None
    ) -> TroubleshootingSession:
        """Records feedback on the current diagnostic step and executes branching."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise KeyError(f"Session '{session_id}' not found.")

            if session.status != "ACTIVE":
                return session

            # Multi-intent branch: feedback isolation per intent
            if session.is_multi_intent and session.intents:
                target_intent = None
                if intent_id:
                    target_intent = next((it for it in session.intents if it.id == intent_id), None)
                if not target_intent:
                    target_intent = session.get_active_intent()

                if not target_intent or target_intent.status in {"RESOLVED", "ESCALATED"}:
                    return session

                target_flow = target_intent.flow
                if not target_flow:
                    target_intent.status = "RESOLVED"
                    return session

                current_node = target_flow.get_current_node()
                step_record = {
                    "step_id": current_node.step_id if current_node else "step_unknown",
                    "action_name": current_node.action_name if current_node else "Step",
                    "instruction": current_node.instruction if current_node else "",
                    "result": result,
                    "timestamp": time.time(),
                    "details": details or {}
                }

                if result in {"passed", "skipped"}:
                    target_intent.completed_steps.append(step_record)
                elif result == "failed":
                    target_intent.failed_steps.append(step_record)

                is_explicit_resolve = details and (details.get("resolved") is True or details.get("fixed") is True)
                if is_explicit_resolve:
                    target_intent.status = "RESOLVED"
                else:
                    next_node, next_status = target_flow.transition(result)
                    target_intent.status = next_status

                now = time.time()
                if target_intent.status == "RESOLVED":
                    actions_taken = [s["action_name"] for s in target_intent.completed_steps]
                    target_intent.resolution_summary = {
                        "resolved": True,
                        "problem": target_intent.title,
                        "steps_completed": len(target_intent.completed_steps),
                        "total_steps": target_flow.total_main_steps,
                        "actions_taken": actions_taken,
                        "notes": "Issue resolved successfully."
                    }
                    # Automatically select next pending intent if available
                    next_pending = next((it for it in session.intents if it.status == "PENDING"), None)
                    if next_pending:
                        session.active_intent_id = next_pending.id
                        next_pending.status = "ACTIVE"
                        session.flow = next_pending.flow
                        session.diagnosis = next_pending.diagnosis

                elif target_intent.status == "ESCALATED":
                    target_intent.escalation_summary = {
                        "escalated": True,
                        "title": f"Escalation for {target_intent.domain}",
                        "message": f"Diagnostics exhausted for {target_intent.title}.",
                        "recommended_action": "Contact Samsung Support."
                    }
                    next_pending = next((it for it in session.intents if it.status == "PENDING"), None)
                    if next_pending:
                        session.active_intent_id = next_pending.id
                        next_pending.status = "ACTIVE"
                        session.flow = next_pending.flow
                        session.diagnosis = next_pending.diagnosis

                # Check global session completion: RESOLVED only when all intents are resolved
                all_resolved = all(it.status == "RESOLVED" for it in session.intents)
                all_done = all(it.status in {"RESOLVED", "ESCALATED"} for it in session.intents)
                if all_resolved:
                    session.status = "RESOLVED"
                    session.resolution_summary = {
                        "resolved": True,
                        "problem": "All reported issues resolved",
                        "steps_completed": sum(len(it.completed_steps) for it in session.intents),
                        "intents_resolved": [it.title for it in session.intents],
                        "actions_taken": [s["action_name"] for it in session.intents for s in it.completed_steps],
                        "notes": "All troubleshooting intents resolved successfully."
                    }
                elif all_done:
                    session.status = "ESCALATED"
                    session.escalation_summary = {
                        "escalated": True,
                        "title": "Escalation Recommended",
                        "message": "One or more issues could not be resolved with standard diagnostics.",
                        "recommended_action": "Contact Samsung Support."
                    }
                else:
                    session.status = "ACTIVE"

                session.updated_at = now
                return session

            # Single-intent flow (backward-compatible)
            flow = session.flow
            if not flow:
                session.status = "RESOLVED"
                session.updated_at = time.time()
                return session

            current_node = flow.get_current_node()
            step_record = {
                "step_id": current_node.step_id if current_node else "step_unknown",
                "action_name": current_node.action_name if current_node else "Step",
                "instruction": current_node.instruction if current_node else "",
                "result": result,
                "timestamp": time.time(),
                "details": details or {}
            }

            if result == "passed":
                session.completed_steps.append(step_record)
            elif result == "failed":
                session.failed_steps.append(step_record)
            elif result == "skipped":
                session.completed_steps.append(step_record)

            if details and (details.get("resolved") is True or details.get("fixed") is True):
                session.status = "RESOLVED"
                session.updated_at = time.time()
                self.resolve_session(session_id, notes="Problem confirmed resolved by the user.")
                return session

            next_node, next_status = flow.transition(result)
            session.status = next_status
            session.updated_at = time.time()

            if next_status == "RESOLVED":
                self.resolve_session(session_id, notes="Problem confirmed resolved by the user.")
            elif next_status == "ESCALATED":
                self.escalate_session(session_id, reason="All available safe diagnostic steps exhausted.")

            return session

    def resolve_session(
        self,
        session_id: str,
        notes: Optional[str] = None
    ) -> TroubleshootingSession:
        """Marks the session as successfully RESOLVED."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise KeyError(f"Session '{session_id}' not found.")

            session.status = "RESOLVED"
            now = time.time()
            elapsed_sec = int(round(now - session.created_at))

            actions_taken = [s["action_name"] for s in session.completed_steps]
            if not actions_taken and session.flow and session.flow.get_current_node():
                actions_taken.append(session.flow.get_current_node().action_name)

            session.resolution_summary = {
                "resolved": True,
                "problem": session.diagnosis.get("title", session.query[:40]),
                "steps_completed": len(session.completed_steps),
                "total_steps": session.flow.total_main_steps if session.flow else len(session.completed_steps),
                "elapsed_seconds": elapsed_sec,
                "actions_taken": actions_taken,
                "notes": notes or "Issue resolved successfully."
            }
            session.updated_at = now
            return session

    def escalate_session(
        self,
        session_id: str,
        reason: Optional[str] = None
    ) -> TroubleshootingSession:
        """Marks the session as ESCALATED with cautious, professional guidance."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise KeyError(f"Session '{session_id}' not found.")

            session.status = "ESCALATED"
            now = time.time()
            session.escalation_summary = {
                "escalated": True,
                "title": "Escalation Recommended",
                "message": "We could not resolve the issue using available software diagnostics. Further assistance may be required.",
                "recommended_action": "Contact Samsung Support or visit an authorized Samsung Service Center for hardware diagnostics.",
                "reason": reason or "Software diagnostics exhausted.",
                "diagnostic_report": {
                    "query": session.query,
                    "device": session.device_context,
                    "completed_steps": len(session.completed_steps),
                    "failed_steps": len(session.failed_steps)
                }
            }
            session.updated_at = now
            return session

    def clear_all(self):
        """Clears all sessions (useful for test isolation)."""
        with self._lock:
            self._sessions.clear()

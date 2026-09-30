"""FastAPI Microservice for the Smart Guided Troubleshooting Engine.
Exposes POST /v1/troubleshoot and GET /health strictly complying with the API contract,
Pydantic data models, latency monitoring, and fallback conventions.
"""
import os
import sys
import time
from typing import Dict, List, Optional, Any, Union
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field

from theme02_troubleshooting_engine.api.ui import DASHBOARD_HTML

# Ensure project root is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from theme02_troubleshooting_engine.core.schema import (
    Goal,
    ContextDeeplinkResponse,
    BaseDeeplink,
    Deeplink,
    ValidationDeepLink,
    StepGroup,
    Action,
    actionCategory
)
from theme02_troubleshooting_engine.core.guardrails import validate_and_sanitize_goal, sanitize_text
from theme02_troubleshooting_engine.core.deeplink_retriever import DeeplinkRetriever
from theme02_troubleshooting_engine.core.extractor import StructuredExtractor
from theme02_troubleshooting_engine.core.query_enricher import QueryEnricher
from theme02_troubleshooting_engine.core.cache_manager import FastPathCache
from theme02_troubleshooting_engine.core.session_manager import SessionManager, TroubleshootingSession
from theme02_troubleshooting_engine.core.validation_simulator import ValidationSimulator, ValidationResult, DEFAULT_SIMULATED_STATE
from theme02_troubleshooting_engine.core.diagnostic_flow import build_flow_from_goal
from theme02_troubleshooting_engine.core.query_pipeline import GeneralizedQueryPipeline
from theme02_troubleshooting_engine.core.profiler import reset_timings, record_timing, print_pipeline_report


# --- API Models ---
class TroubleshootRequest(BaseModel):
    query: str
    siis_response: Optional[Union[str, Dict[str, Any]]] = None


class SessionStartRequest(BaseModel):
    query: str
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    image_data: Optional[str] = None
    image_filename: Optional[str] = None
    error_code: Optional[str] = None


class SessionStartResponse(BaseModel):
    session_id: str
    status: str
    diagnosis: Dict[str, Any]
    current_step: Optional[Dict[str, Any]]
    progress: Dict[str, int]
    device_context: Optional[Dict[str, Any]] = None
    accessory: Optional[str] = None
    matched_via: Optional[str] = None
    ai_fallback_used: Optional[bool] = False
    image_analysis_used: Optional[bool] = False
    image_evidence_confidence: Optional[float] = None
    error_codes: Optional[List[str]] = None
    is_multi_intent: Optional[bool] = False
    active_intent_id: Optional[str] = None
    intents: Optional[List[Dict[str, Any]]] = None


class SessionFeedbackRequest(BaseModel):
    result: str  # passed, failed, skipped
    details: Optional[Dict[str, Any]] = None
    intent_id: Optional[str] = None


class SwitchIntentRequest(BaseModel):
    intent_id: str


class SessionFeedbackResponse(BaseModel):
    session_id: str
    status: str
    current_step: Optional[Dict[str, Any]] = None
    progress: Dict[str, int]
    resolved: bool
    escalated: bool
    completed_steps: List[Dict[str, Any]] = []
    failed_steps: List[Dict[str, Any]] = []
    resolution_summary: Optional[Dict[str, Any]] = None
    escalation_summary: Optional[Dict[str, Any]] = None
    is_multi_intent: Optional[bool] = False
    active_intent_id: Optional[str] = None
    intents: Optional[List[Dict[str, Any]]] = None


class SimulateValidationRequest(BaseModel):
    state_overrides: Optional[Dict[str, Any]] = None



class OperationalMeta(BaseModel):
    latency_ms: int
    cache_hit: bool
    model: str = "hybrid-bm25-dense-retriever"
    cost_usd: float = 0.0
    fallback: Optional[str] = None


class TroubleshootResponse(BaseModel):
    query: str
    query_variations: List[str]
    response: ContextDeeplinkResponse
    meta: OperationalMeta


# --- Initialize Engine Components ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEEPLINKS_PATH = os.path.join(DATA_DIR, "deeplinks.json")
CACHE_PATH = os.path.join(DATA_DIR, "cache_store.json")

print("[Engine] Initializing Deeplink Retriever...")
retriever = DeeplinkRetriever(DEEPLINKS_PATH)

print("[Engine] Initializing Knowledge Extractor and Enricher...")
extractor = StructuredExtractor(retriever)
enricher = QueryEnricher()

print("[Engine] Initializing Fast-Path Semantic Cache...")
cache = FastPathCache(cache_file_path=CACHE_PATH)

print("[Engine] Initializing Session Manager & Validation Simulator...")
session_manager = SessionManager()
simulator = ValidationSimulator()

print("[Engine] Initializing Generalized Query Intelligence Pipeline...")
query_pipeline = GeneralizedQueryPipeline(cache=cache, extractor=extractor)


from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan context manager for startup and shutdown tasks.
    Pre-warms the PaddleOCR engine once during application startup so the first
    multimodal user request does not incur cold model initialization overhead.
    """
    try:
        t0 = time.perf_counter()
        from theme02_troubleshooting_engine.core.image_analyzer import _get_paddle_ocr
        ocr_engine = _get_paddle_ocr()
        duration_ms = (time.perf_counter() - t0) * 1000
        if ocr_engine is not None:
            print(f"[Engine] PaddleOCR pre-warmed successfully at startup in {duration_ms:.2f} ms.")
        else:
            print("[Engine] PaddleOCR pre-warming skipped (engine returned None). Proceeding with graceful fallback.")
    except Exception as e:
        print(f"[Engine] Non-fatal PaddleOCR pre-warming notice: {e}. Proceeding with graceful fallback.")
    yield


app = FastAPI(
    title="Smart Guided Troubleshooting Engine",
    description="Transforms vague Galaxy device complaints into machine-actionable, deeplinked troubleshooting plans.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for React frontend (Vite dev server on localhost:5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/", response_class=HTMLResponse)
def index():
    """Serves interactive visual dashboard for live testing and demonstration."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/health")
def health_check():
    """Health check endpoint.
    Returns HTTP 200 {"status": "ok"} when cache, vector indexes, and models are fully initialized.
    """
    if retriever.bm25 is None or cache is None:
        raise HTTPException(status_code=503, detail="Engine initializing")
    return {"status": "ok"}


@app.post("/v1/troubleshoot", response_model=TroubleshootResponse)
def troubleshoot(payload: TroubleshootRequest):
    """Processes a customer complaint and returns an actionable, validated troubleshooting plan."""
    start_time = time.perf_counter()
    raw_query = payload.query.strip()
    if not raw_query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    canonical_key = enricher.normalize(raw_query)
    query_variations = enricher.generate_variations(raw_query, canonical_key)

    # 1. Fast-Path Semantic Cache Lookup
    cached_goal, cache_hit, similarity = cache.get(raw_query)
    if cache_hit and cached_goal is not None:
        elapsed_ms = int(round((time.perf_counter() - start_time) * 1000))
        return TroubleshootResponse(
            query=raw_query,
            query_variations=query_variations,
            response=ContextDeeplinkResponse(contexts=[cached_goal]),
            meta=OperationalMeta(
                latency_ms=elapsed_ms,
                cache_hit=True,
                cost_usd=0.0
            )
        )

    # 2. Cold-Path: Process with SIIS context if provided
    siis_context = payload.siis_response
    if siis_context is not None:
        title = "Device Troubleshooting"
        content = ""
        
        if isinstance(siis_context, dict):
            title = siis_context.get("title", title)
            content = siis_context.get("content", "")
        elif isinstance(siis_context, str):
            content = siis_context
            title = canonical_key.title()

        extracted_goal = extractor.extract_plan(raw_query, title, content)
        if extracted_goal is not None:
            # Store newly resolved plan in cache for subsequent fast-path hits
            cache.put(raw_query, canonical_key, extracted_goal, variations=query_variations)
            
            elapsed_ms = int(round((time.perf_counter() - start_time) * 1000))
            return TroubleshootResponse(
                query=raw_query,
                query_variations=query_variations,
                response=ContextDeeplinkResponse(contexts=[extracted_goal]),
                meta=OperationalMeta(
                    latency_ms=elapsed_ms,
                    cache_hit=False,
                    cost_usd=0.0
                )
            )

    # 3. Fallback: No matching plan found in cache and no viable solution in context
    elapsed_ms = int(round((time.perf_counter() - start_time) * 1000))
    return TroubleshootResponse(
        query=raw_query,
        query_variations=query_variations,
        response=ContextDeeplinkResponse(contexts=[]),
        meta=OperationalMeta(
            latency_ms=elapsed_ms,
            cache_hit=False,
            cost_usd=0.0,
            fallback="no_match"
        )
    )


# --- Phase 2: Interactive Session Endpoints ---
@app.post("/v1/session/start", response_model=SessionStartResponse)
def start_session(payload: SessionStartRequest):
    """Starts a new interactive guided troubleshooting session."""
    reset_timings()
    t_req_start0 = time.perf_counter()
    raw_query = payload.query.strip()
    if not raw_query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    proc = query_pipeline.process_query(
        raw_query=raw_query,
        user_device_model=payload.device_model,
        user_os_version=payload.os_version,
        image_data=payload.image_data,
        image_filename=payload.image_filename,
        manual_error_code=payload.error_code
    )

    device_ctx = proc.get("device_context") or {
        "device_model": proc["phone_model"],
        "model": proc["phone_model"],
        "series": "Galaxy S",
        "device_type": "phone",
        "os_version": payload.os_version or "One UI 6.1 (Android 14)",
        "confidence": 1.0 if proc.get("extracted_phone") else 0.85
    }
    if proc.get("accessory"):
        device_ctx["accessory"] = proc["accessory"]

    image_analysis_used = proc.get("image_analysis_used", False)
    image_evidence_conf = proc.get("image_evidence_confidence", 0.0)
    error_codes = proc.get("error_codes", [])

    # Check for ambiguous query needing clarification
    if proc.get("needs_clarification"):
        clarification_msg = proc.get("clarification_message") or (
            "I can help with this, but I need a little more information. "
            "Are you having trouble with Wi-Fi, Bluetooth, charging, the screen, or another feature?"
        )
        ai_fallback_used = proc.get("ai_fallback_used", False) or (proc.get("matched_via") == "llm")
        diagnosis = {
            "title": "Clarification Needed",
            "summary": clarification_msg,
            "canonical_key": "clarification_request",
            "confidence": round(proc["confidence"], 2),
            "domain": "CLARIFICATION",
            "needs_clarification": True,
            "matched_via": "clarification",
            "ai_fallback_used": ai_fallback_used,
            "image_analysis_used": image_analysis_used,
            "image_evidence_confidence": image_evidence_conf,
            "error_codes": error_codes
        }
        clarification_goal = Goal(
            goal="Follow these steps to perform this Issue Clarification",
            title="Clarification Needed",
            actions=[
                Action(
                    actionName="Identify your Samsung Galaxy issue category",
                    category=actionCategory.manual,
                    stepGroups=[
                        StepGroup(
                            groupName="Clarify Issue Category",
                            steps=[
                                "Select or describe your problem category: Wi-Fi connection, Bluetooth pairing, Battery drain, Screen display, Audio/Sound, Camera, Email sync, or System gestures."
                            ]
                        )
                    ],
                    description="It will clarify your specific hardware or software symptom"
                )
            ],
            score=proc["confidence"]
        )
        session = session_manager.create_session(
            query=raw_query,
            diagnosis=diagnosis,
            goal=clarification_goal,
            device_context=device_ctx,
            is_multi_intent=False,
            active_intent_id="intent_1",
            intents=[]
        )
        tot_ms = (time.perf_counter() - t_req_start0) * 1000
        record_timing("total", tot_ms)
        req_num = getattr(start_session, '_count', 1)
        print_pipeline_report(f"REQUEST {req_num}")
        start_session._count = req_num + 1
        return SessionStartResponse(
            session_id=session.session_id,
            status=session.status,
            diagnosis=session.diagnosis,
            current_step=session.get_current_step(),
            progress=session.get_progress(),
            device_context=session.device_context,
            accessory=proc.get("accessory"),
            matched_via="clarification",
            ai_fallback_used=ai_fallback_used,
            image_analysis_used=image_analysis_used,
            image_evidence_confidence=image_evidence_conf,
            error_codes=error_codes,
            is_multi_intent=False,
            active_intent_id="intent_1",
            intents=[]
        )

    # Standard High/Medium Confidence Path
    goal = proc["goal"]
    domain = proc["domain"]
    phone_model = proc["phone_model"]
    accessory = proc.get("accessory")
    ai_fallback_used = proc.get("ai_fallback_used", False) or (proc.get("matched_via") == "llm")

    summary_text = f"Identified potential {domain.lower()} anomaly on {phone_model}"
    if accessory:
        summary_text += f" with {accessory}."
    else:
        summary_text += "."

    diagnosis = {
        "title": goal.title,
        "summary": summary_text,
        "canonical_key": proc["canonical_key"],
        "confidence": round(proc["confidence"], 2),
        "domain": domain,
        "matched_via": proc.get("matched_via", "domain_grounded"),
        "ai_fallback_used": ai_fallback_used,
        "image_analysis_used": image_analysis_used,
        "image_evidence_confidence": image_evidence_conf,
        "error_codes": error_codes
    }
    if accessory:
        diagnosis["accessory"] = accessory

    session = session_manager.create_session(
        query=raw_query,
        diagnosis=diagnosis,
        goal=goal,
        device_context=device_ctx,
        is_multi_intent=proc.get("is_multi_intent", False),
        active_intent_id=proc.get("active_intent_id"),
        intents=proc.get("intents")
    )

    tot_ms = (time.perf_counter() - t_req_start0) * 1000
    record_timing("total", tot_ms)
    req_num = getattr(start_session, '_count', 1)
    print_pipeline_report(f"REQUEST {req_num}")
    start_session._count = req_num + 1

    return SessionStartResponse(
        session_id=session.session_id,
        status=session.status,
        diagnosis=session.diagnosis,
        current_step=session.get_current_step(),
        progress=session.get_progress(),
        device_context=session.device_context,
        accessory=proc.get("accessory"),
        matched_via=proc.get("matched_via"),
        ai_fallback_used=ai_fallback_used,
        image_analysis_used=image_analysis_used,
        image_evidence_confidence=image_evidence_conf,
        error_codes=error_codes,
        is_multi_intent=session.is_multi_intent,
        active_intent_id=session.active_intent_id,
        intents=session.get_intents_summary()
    )


@app.post("/v1/session/{session_id}/feedback", response_model=SessionFeedbackResponse)
def session_feedback(session_id: str, payload: SessionFeedbackRequest):
    """Records user feedback ('passed', 'failed', 'skipped') and triggers dynamic branching."""
    allowed_results = {"passed", "failed", "skipped"}
    res_clean = payload.result.strip().lower()
    if res_clean not in allowed_results:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid result '{payload.result}'. Allowed: {sorted(list(allowed_results))}"
        )

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    updated = session_manager.record_feedback(session_id, res_clean, payload.details, intent_id=payload.intent_id)

    return SessionFeedbackResponse(
        session_id=updated.session_id,
        status=updated.status,
        current_step=updated.get_current_step(),
        progress=updated.get_progress(),
        resolved=(updated.status == "RESOLVED"),
        escalated=(updated.status == "ESCALATED"),
        completed_steps=updated.completed_steps,
        failed_steps=updated.failed_steps,
        resolution_summary=updated.resolution_summary,
        escalation_summary=updated.escalation_summary,
        is_multi_intent=updated.is_multi_intent,
        active_intent_id=updated.active_intent_id,
        intents=updated.get_intents_summary()
    )


@app.post("/v1/session/{session_id}/switch-intent", response_model=SessionFeedbackResponse)
def switch_intent(session_id: str, payload: SwitchIntentRequest):
    """Switches the active intent tab in a multi-intent diagnostic session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    try:
        updated = session_manager.switch_active_intent(session_id, payload.intent_id)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return SessionFeedbackResponse(
        session_id=updated.session_id,
        status=updated.status,
        current_step=updated.get_current_step(),
        progress=updated.get_progress(),
        resolved=(updated.status == "RESOLVED"),
        escalated=(updated.status == "ESCALATED"),
        completed_steps=updated.completed_steps,
        failed_steps=updated.failed_steps,
        resolution_summary=updated.resolution_summary,
        escalation_summary=updated.escalation_summary,
        is_multi_intent=updated.is_multi_intent,
        active_intent_id=updated.active_intent_id,
        intents=updated.get_intents_summary()
    )


@app.get("/v1/session/{session_id}")
def get_session(session_id: str):
    """Retrieves current session state and diagnostic progress."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return {
        "session_id": session.session_id,
        "status": session.status,
        "query": session.query,
        "device_context": session.device_context,
        "accessory": session.device_context.get("accessory") if session.device_context else None,
        "diagnosis": session.diagnosis,
        "current_step": session.get_current_step(),
        "progress": session.get_progress(),
        "completed_steps": session.completed_steps,
        "failed_steps": session.failed_steps,
        "resolved": (session.status == "RESOLVED"),
        "escalated": (session.status == "ESCALATED"),
        "resolution_summary": session.resolution_summary,
        "escalation_summary": session.escalation_summary,
        "is_multi_intent": session.is_multi_intent,
        "active_intent_id": session.active_intent_id,
        "intents": session.get_intents_summary(),
        "created_at": session.created_at,
        "updated_at": session.updated_at
    }


@app.post("/v1/session/{session_id}/simulate-validation")
def simulate_validation(session_id: str, payload: Optional[SimulateValidationRequest] = None):
    """Deterministically simulates device telemetry validation check for the current step."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    curr_step = session.get_current_step()
    if not curr_step:
        raise HTTPException(status_code=400, detail="No active step in session to validate")

    val_dl = curr_step.get("validation_deeplink")
    if not val_dl:
        return {
            "is_valid": True,
            "key": "Manual User Inspection",
            "message": "Step requires manual user verification (no automated telemetry deeplink).",
            "simulated_telemetry": simulator.get_state()
        }

    overrides = payload.state_overrides if payload else None
    val_obj = ValidationDeepLink(**val_dl)
    result = simulator.evaluate_validation(val_obj, state_overrides=overrides)
    return result.model_dump()


@app.get("/v1/telemetry/state")
def get_telemetry_state():
    """Returns current simulated device state."""
    return simulator.get_state()


@app.post("/v1/telemetry/state")
def update_telemetry_state(state: Dict[str, Any]):
    """Updates simulated device state deterministically."""
    simulator.update_state(state)
    return {"status": "updated", "current_state": simulator.get_state()}


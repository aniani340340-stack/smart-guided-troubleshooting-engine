"""Temporary profiling instrumentation module for Phase 6 Performance Investigation.
Captures sub-millisecond timings across all image pipeline stages without altering architecture.
"""
import time
from typing import Dict, Any, Optional
from contextlib import contextmanager

_CURRENT_PROFILING: Dict[str, Any] = {
    "image_decode": 0.0,
    "image_validation": 0.0,
    "image_preprocessing": 0.0,
    "ocr_initialization": 0.0,
    "ocr_inference": 0.0,
    "ocr_postprocessing": 0.0,
    "error_resolver": 0.0,
    "gemini_request": 0.0,
    "domain_classification": 0.0,
    "validator": 0.0,
    "total": 0.0,
    "original_width": 0,
    "original_height": 0,
    "file_size": 0,
    "processed_width": 0,
    "processed_height": 0
}


def reset_timings():
    """Resets all recorded pipeline timings."""
    global _CURRENT_PROFILING
    _CURRENT_PROFILING = {
        "image_decode": 0.0,
        "image_validation": 0.0,
        "image_preprocessing": 0.0,
        "ocr_initialization": 0.0,
        "ocr_inference": 0.0,
        "ocr_postprocessing": 0.0,
        "error_resolver": 0.0,
        "gemini_request": 0.0,
        "domain_classification": 0.0,
        "validator": 0.0,
        "total": 0.0,
        "original_width": 0,
        "original_height": 0,
        "file_size": 0,
        "processed_width": 0,
        "processed_height": 0
    }


def record_timing(stage: str, duration_ms: float):
    """Records duration in milliseconds for a pipeline stage."""
    _CURRENT_PROFILING[stage] = round(duration_ms, 2)


def add_timing(stage: str, duration_ms: float):
    """Adds duration in milliseconds to an existing pipeline stage."""
    _CURRENT_PROFILING[stage] = round(_CURRENT_PROFILING.get(stage, 0.0) + duration_ms, 2)


def set_image_info(orig_w: int, orig_h: int, file_size: int, proc_w: int, proc_h: int):
    """Sets image dimension and size metrics."""
    _CURRENT_PROFILING["original_width"] = orig_w
    _CURRENT_PROFILING["original_height"] = orig_h
    _CURRENT_PROFILING["file_size"] = file_size
    _CURRENT_PROFILING["processed_width"] = proc_w
    _CURRENT_PROFILING["processed_height"] = proc_h


def get_timings() -> Dict[str, Any]:
    """Returns current timings snapshot."""
    return dict(_CURRENT_PROFILING)


@contextmanager
def time_stage(stage_name: str):
    """Context manager to record stage duration."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = (time.perf_counter() - t0) * 1000
        record_timing(stage_name, dt)


def print_pipeline_report(request_label: Optional[str] = None):
    """Prints timings strictly adhering to the requested Phase 6 format."""
    p = _CURRENT_PROFILING
    if request_label:
        print(f"\n==================== {request_label} ====================")
    else:
        print("\n==================== PIPELINE PROFILE ====================")
    
    print(f"[IMAGE] decode: {p['image_decode']:.2f} ms")
    print(f"[IMAGE] validation: {p['image_validation']:.2f} ms")
    print(f"[IMAGE] preprocessing: {p['image_preprocessing']:.2f} ms")
    print(f"[OCR] initialization: {p['ocr_initialization']:.2f} ms")
    print(f"[OCR] inference: {p['ocr_inference']:.2f} ms")
    print(f"[OCR] postprocessing: {p['ocr_postprocessing']:.2f} ms")
    print(f"[ERROR] resolver: {p['error_resolver']:.2f} ms")
    print(f"[GEMINI] request: {p['gemini_request']:.2f} ms")
    print(f"[DOMAIN] classification: {p['domain_classification']:.2f} ms")
    print(f"[VALIDATOR] {p['validator']:.2f} ms")
    print(f"[TOTAL] {p['total']:.2f} ms")
    
    print("\n[IMAGE SIZE]")
    print(f"- Original width: {p['original_width']}")
    print(f"- Original height: {p['original_height']}")
    print(f"- File size: {p['file_size']} bytes")
    print(f"- Processed width: {p['processed_width']}")
    print(f"- Processed height: {p['processed_height']}")
    print("=========================================================\n")

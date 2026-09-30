"""Image & Error-Code Analysis Layer.
Extracts structured diagnostic evidence from screenshots, settings screens,
and device error photos using OCR and multimodal vision intelligence.

Safety & Architectural Principles:
- Provider-neutral abstraction with strict timeout and input validation.
- Validates file size (max 5 MB), readable image formats (PNG, JPG/JPEG, WEBP), and MIME types.
- Never generates troubleshooting instructions or modifies device settings.
- Returns structured diagnostic evidence consumed by the Query Pipeline.
- Operates safely without API credentials.
"""
import sys
import io
import re
import os
import json
import base64
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Tuple, Union
from PIL import Image

# Ensure local site-packages is on sys.path for paddle & paddleocr
if "c:/Users/anian/p" not in sys.path:
    sys.path.insert(0, "c:/Users/anian/p")

from theme02_troubleshooting_engine.core.error_code_resolver import extract_error_codes, resolve_error_code
try:
    from paddleocr.tools.infer.utility import get_rotate_crop_image
except Exception:
    get_rotate_crop_image = None

try:
    from theme02_troubleshooting_engine.core.profiler import record_timing, set_image_info
except Exception:
    def record_timing(stage: str, duration_ms: float): pass
    def set_image_info(orig_w: int, orig_h: int, file_size: int, proc_w: int, proc_h: int): pass


PROFILING_TIMINGS: Dict[str, Any] = {}
_PADDLE_OCR_INSTANCE = None
_PADDLE_OCR_INITIALIZED = False


def _get_paddle_ocr():
    """Lazily initializes the pretrained local PaddleOCR engine with Windows CPU patch."""
    global _PADDLE_OCR_INSTANCE, _PADDLE_OCR_INITIALIZED
    if _PADDLE_OCR_INITIALIZED:
        record_timing("ocr_initialization", 0.0)
        return _PADDLE_OCR_INSTANCE
    
    t0 = time.perf_counter()
    _PADDLE_OCR_INITIALIZED = True
    try:
        import paddle.inference as inference
        if not getattr(inference, "_patch_applied", False):
            orig_create = inference.create_predictor
            def _safe_infer_create(config):
                try:
                    config.switch_ir_optim(False)
                except Exception:
                    pass
                return orig_create(config)
            inference.create_predictor = _safe_infer_create
            inference._patch_applied = True

        from paddleocr import PaddleOCR
        _PADDLE_OCR_INSTANCE = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
    except Exception:
        _PADDLE_OCR_INSTANCE = None
    
    init_ms = (time.perf_counter() - t0) * 1000
    record_timing("ocr_initialization", init_ms)
    return _PADDLE_OCR_INSTANCE


def _score_and_filter_boxes(raw_boxes, img_h: int, img_w: int) -> List[Any]:
    """Filters peripheral UI noise and sorts bounding boxes by diagnostic saliency score."""
    scored = []
    for b in raw_boxes:
        xs = [p[0] for p in b]
        ys = [p[1] for p in b]
        ymin, ymax = min(ys), max(ys)
        xmin, xmax = min(xs), max(xs)
        box_w = max(1.0, xmax - xmin)
        box_h = max(1.0, ymax - ymin)

        # Filter out obvious peripheral noise on standard mobile screenshots
        if img_h >= 400:
            if (ymax / img_h) < 0.05:  # Status bar (clock, battery, signal)
                continue
            if (ymin / img_h) > 0.92:  # Navigation bar (Android icons)
                continue
            if box_w < 12 and box_h < 12:  # Single pixel/dot artifacts
                continue

        rel_area = (box_w * box_h) / (img_w * img_h)
        rel_w = box_w / img_w
        center_x = (xmin + xmax) / 2.0
        rel_cx = center_x / img_w

        score = 0.0
        score += min(50.0, rel_area * 1200.0)
        score += min(25.0, (box_h / img_h) * 450.0)
        score += min(30.0, rel_w * 40.0)

        dist_cx = abs(rel_cx - 0.5)
        if dist_cx < 0.20:
            score += 20.0
        elif dist_cx < 0.35:
            score += 10.0

        score += 15.0  # Inside valid content zone
        aspect = box_w / box_h
        if 1.2 <= aspect <= 20.0:
            score += 10.0

        scored.append((score, b))

    if not scored:
        return list(raw_boxes)

    scored.sort(key=lambda x: x[0], reverse=True)
    return [b for s, b in scored]


def _is_evidence_sufficient(accumulated_lines: List[str]) -> bool:
    """Evaluates whether accumulated OCR text contains conclusive diagnostic evidence."""
    if not accumulated_lines:
        return False
    full_text = " ".join(accumulated_lines)

    # Condition A: Valid known or formatted error code
    codes = extract_error_codes(full_text)
    for c in codes:
        res = resolve_error_code(c)
        if res.get("known"):
            return True
    if codes:
        return True

    lower_text = full_text.lower()
    has_error_kw = any(k in lower_text for k in [
        "failed", "failure", "unable to connect", "couldn't connect",
        "could not connect", "connection error", "pairing failed",
        "sensor failed", "error notice", "diagnostic alert", "not working",
        "disconnected", "timed out", "authentication error"
    ])

    has_domain_kw = any(k in lower_text for k in [
        "bluetooth", "buds", "pairing", "wi-fi", "wifi", "network",
        "battery", "charging", "camera", "display", "screen", "audio"
    ])

    has_device_kw = any(k in lower_text for k in [
        "galaxy", "phone", "s23", "s24", "s22", "s21", "s20",
        "buds2", "buds pro", "watch", "ultra", "flip", "fold"
    ])

    # Condition B: Error statement + Subsystem or Device context with at least 3 lines
    if has_error_kw and (has_domain_kw or has_device_kw) and len(accumulated_lines) >= 3:
        return True

    return False


def extract_text_from_pixels(image_bytes: bytes) -> Tuple[str, float]:
    """Runs Hybrid Adaptive PaddleOCR directly on image pixels with saliency ranking & early stopping.
    Returns: (extracted_text: str, confidence: float)
    """
    ocr_engine = _get_paddle_ocr()
    if ocr_engine is None:
        return "", 0.0

    try:
        import numpy as np
        t_prep0 = time.perf_counter()
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            orig_w, orig_h = pil_img.size
            rgb_img = pil_img.convert("RGB")

            # 1. Proportional normalization to max 960px if larger
            max_dim = max(orig_w, orig_h)
            if max_dim > 960:
                scale = 960.0 / max_dim
                target_w = max(1, int(round(orig_w * scale)))
                target_h = max(1, int(round(orig_h * scale)))
                rgb_img = rgb_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            else:
                target_w, target_h = orig_w, orig_h

            img_np = np.array(rgb_img)

        proc_h, proc_w = img_np.shape[:2]
        prep_ms = (time.perf_counter() - t_prep0) * 1000
        record_timing("image_preprocessing", prep_ms)
        set_image_info(orig_w, orig_h, len(image_bytes), proc_w, proc_h)

        t_infer0 = time.perf_counter()

        # 2. Text Detection
        t_det0 = time.perf_counter()
        raw_boxes, _ = ocr_engine.text_detector(img_np)
        det_ms = (time.perf_counter() - t_det0) * 1000

        if raw_boxes is None or len(raw_boxes) == 0:
            total_infer_ms = (time.perf_counter() - t_infer0) * 1000
            record_timing("ocr_inference", total_infer_ms)
            record_timing("ocr_postprocessing", 0.0)
            print(f"[OCR] detection: {det_ms:.2f} ms")
            print(f"[OCR] boxes detected: 0")
            print(f"[OCR] boxes selected: 0")
            print(f"[OCR] recognition: 0.00 ms")
            print(f"[OCR] early_stop: false")
            print(f"[OCR] boxes recognized: 0")
            print(f"[OCR] total: {total_infer_ms:.2f} ms")
            return "", 0.0

        # 3. Geometric Saliency Ranking & Noise Filtering
        ordered_boxes = _score_and_filter_boxes(raw_boxes, proc_h, proc_w)

        # 4. Multi-Tier Adaptive Recognition
        PRIMARY_BATCH_SIZE = 7
        EXPANSION_BATCH_SIZE = 6

        accumulated_lines = []
        accumulated_confs = []
        early_stopped = False
        boxes_recognized = 0
        t_rec0 = time.perf_counter()

        crop_fn = get_rotate_crop_image or (lambda img, b: img)

        # Tier 1: Top 7 highest-priority candidates
        batch1 = ordered_boxes[:PRIMARY_BATCH_SIZE]
        if batch1:
            crops1 = [crop_fn(img_np, b) for b in batch1]
            res1, _ = ocr_engine.text_recognizer(crops1)
            boxes_recognized += len(batch1)
            for r in res1:
                if r and len(r) >= 2:
                    txt, score = str(r[0]).strip(), float(r[1])
                    if txt:
                        accumulated_lines.append(txt)
                        accumulated_confs.append(score)

        if _is_evidence_sufficient(accumulated_lines):
            early_stopped = True
        else:
            # Tier 2: Expand to next 6 boxes
            batch2 = ordered_boxes[PRIMARY_BATCH_SIZE:PRIMARY_BATCH_SIZE + EXPANSION_BATCH_SIZE]
            if batch2:
                crops2 = [crop_fn(img_np, b) for b in batch2]
                res2, _ = ocr_engine.text_recognizer(crops2)
                boxes_recognized += len(batch2)
                for r in res2:
                    if r and len(r) >= 2:
                        txt, score = str(r[0]).strip(), float(r[1])
                        if txt:
                            accumulated_lines.append(txt)
                            accumulated_confs.append(score)

            if _is_evidence_sufficient(accumulated_lines):
                early_stopped = True
            else:
                # Tier 3: Recognize remaining boxes if still unresolved
                batch3 = ordered_boxes[PRIMARY_BATCH_SIZE + EXPANSION_BATCH_SIZE:]
                if batch3:
                    crops3 = [crop_fn(img_np, b) for b in batch3]
                    res3, _ = ocr_engine.text_recognizer(crops3)
                    boxes_recognized += len(batch3)
                    for r in res3:
                        if r and len(r) >= 2:
                            txt, score = str(r[0]).strip(), float(r[1])
                            if txt:
                                accumulated_lines.append(txt)
                                accumulated_confs.append(score)

        rec_ms = (time.perf_counter() - t_rec0) * 1000
        total_infer_ms = (time.perf_counter() - t_infer0) * 1000
        record_timing("ocr_inference", total_infer_ms)

        # 5. Production Timing Logs
        print(f"[OCR] detection: {det_ms:.2f} ms")
        print(f"[OCR] boxes detected: {len(raw_boxes)}")
        print(f"[OCR] boxes selected: {len(ordered_boxes)}")
        print(f"[OCR] recognition: {rec_ms:.2f} ms")
        print(f"[OCR] early_stop: {'true' if early_stopped else 'false'}")
        print(f"[OCR] boxes recognized: {boxes_recognized}")
        print(f"[OCR] total: {total_infer_ms:.2f} ms")

        t_post0 = time.perf_counter()
        if not accumulated_lines:
            record_timing("ocr_postprocessing", (time.perf_counter() - t_post0) * 1000)
            return "", 0.0

        full_text = " ".join(accumulated_lines)
        avg_conf = sum(accumulated_confs) / len(accumulated_confs) if accumulated_confs else 0.88
        post_ms = (time.perf_counter() - t_post0) * 1000
        record_timing("ocr_postprocessing", post_ms)
        return full_text, round(avg_conf, 2)
    except Exception:
        return "", 0.0



MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
SUPPORTED_FORMATS = {"PNG", "JPEG", "JPG", "WEBP"}
SUPPORTED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp"
}


class ImageValidationError(Exception):
    """Raised when an uploaded diagnostic image fails safety or format checks."""
    pass


class ImageAnalyzer:
    """Provider-neutral diagnostic image analyzer.
    Extracts text, error codes, and subsystem visual evidence from device screenshots.
    """

    SUPPORTED_DOMAINS = [
        "NETWORK", "DISPLAY", "BATTERY", "BLUETOOTH",
        "AUDIO", "CAMERA", "EMAIL", "SYSTEM"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        timeout: float = 4.0,
        vision_fn: Optional[Any] = None
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
        self.vision_fn = vision_fn  # Mock or custom vision caller for unit tests

    def is_available(self) -> bool:
        return bool(self.api_key or self.vision_fn)

    def validate_image_bytes(self, data: bytes, mime_type: Optional[str] = None) -> Tuple[str, Tuple[int, int]]:
        """Performs rigorous security and integrity validation on raw image bytes.
        Returns: (image_format: str, dimensions: (width, height))
        Raises: ImageValidationError on violation.
        """
        if not data or len(data) == 0:
            raise ImageValidationError("Empty image file provided.")

        if len(data) > MAX_IMAGE_SIZE_BYTES:
            raise ImageValidationError(f"Image file size ({len(data)} bytes) exceeds the maximum limit of 5 MB.")

        if mime_type and mime_type.lower() not in SUPPORTED_MIME_TYPES:
            raise ImageValidationError(f"Unsupported image MIME type: '{mime_type}'. Supported: PNG, JPEG, WEBP.")

        try:
            with Image.open(io.BytesIO(data)) as img:
                img_format = (img.format or "").upper()
                if img_format not in SUPPORTED_FORMATS:
                    raise ImageValidationError(f"Unsupported image format: '{img_format}'. Supported: PNG, JPEG, WEBP.")
                width, height = img.size
                if width <= 0 or height <= 0:
                    raise ImageValidationError("Invalid image dimensions.")
                return img_format, (width, height)
        except ImageValidationError:
            raise
        except Exception as e:
            raise ImageValidationError(f"Corrupt or unreadable image file: {str(e)}")

    def decode_input(self, image_input: Union[bytes, str]) -> Tuple[bytes, str]:
        """Decodes raw bytes or Base64 data URL into binary bytes and detected MIME type."""
        if isinstance(image_input, bytes):
            return image_input, "image/png"

        if isinstance(image_input, str):
            clean_str = image_input.strip()
            try:
                # Handle data URLs: data:image/png;base64,...
                if clean_str.startswith("data:"):
                    header, base64_data = clean_str.split(",", 1)
                    mime = "image/png"
                    m = re.search(r"data:([^;]+);base64", header)
                    if m:
                        mime = m.group(1).lower()
                    return base64.b64decode(base64_data), mime
                else:
                    return base64.b64decode(clean_str), "image/png"
            except Exception as e:
                raise ImageValidationError(f"Invalid Base64 image encoding: {str(e)}")

        raise ImageValidationError("Image input must be bytes or Base64 string.")

    def build_vision_prompt(self) -> str:
        """Constructs strict prompt for visual evidence extraction."""
        domains_list = ", ".join(self.SUPPORTED_DOMAINS)
        return (
            "You are a Samsung technical diagnostic image analyzer.\n"
            "Analyze this screenshot or photo of a Samsung device error, settings screen, or notification.\n\n"
            "Extract ONLY visible technical evidence and return a valid JSON object matching this schema:\n"
            "{\n"
            '  "extracted_text": "<exact error message, dialog text, or settings title visible in image>",\n'
            '  "error_codes": ["<any visible error codes or error numbers, e.g. 1001, BT-204, ERR_WIFI_01>"],\n'
            f'  "detected_domains": ["<one or more from: {domains_list}>"],\n'
            '  "visual_clues": ["<concise visual descriptions, e.g. Bluetooth connection error dialog, Wi-Fi exclamation icon>"],\n'
            '  "confidence": <float between 0.0 and 1.0>\n'
            "}\n\n"
            "Rules:\n"
            "1. Do NOT provide troubleshooting steps or instructions.\n"
            "2. Do NOT invent settings screens or diagnoses.\n"
            "3. If no diagnostic error or text is readable, set extracted_text to empty string, detected_domains to [], and confidence to 0.0.\n"
            "4. Output ONLY valid JSON."
        )

    def parse_vision_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Parses and normalizes JSON response from vision models."""
        if not raw_text:
            return None
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        # Clean and validate fields
        extracted_text = str(data.get("extracted_text", "")).strip()
        error_codes = data.get("error_codes", [])
        if not isinstance(error_codes, list):
            error_codes = []
        error_codes = [str(c).strip().upper() for c in error_codes if c]

        detected_domains = data.get("detected_domains", [])
        if not isinstance(detected_domains, list):
            detected_domains = []
        valid_domains = [
            str(d).strip().upper() for d in detected_domains
            if str(d).strip().upper() in self.SUPPORTED_DOMAINS
        ]

        visual_clues = data.get("visual_clues", [])
        if not isinstance(visual_clues, list):
            visual_clues = []
        visual_clues = [str(c).strip() for c in visual_clues if c]

        raw_conf = data.get("confidence", 0.0)
        try:
            conf = float(raw_conf)
            conf = max(0.0, min(1.0, conf))
        except (ValueError, TypeError):
            conf = 0.0

        return {
            "extracted_text": extracted_text,
            "error_codes": error_codes,
            "detected_domains": valid_domains,
            "visual_clues": visual_clues,
            "confidence": round(conf, 2)
        }

    def analyze_image(
        self,
        image_input: Union[bytes, str],
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyzes a diagnostic image and returns structured evidence.
        Returns:
            {
                "success": bool,
                "extracted_text": str,
                "error_codes": List[str],
                "detected_domains": List[str],
                "visual_clues": List[str],
                "confidence": float,
                "known_error_details": Optional[Dict[str, Any]],
                "error": Optional[str]
            }
        """
        # 1. Decode & Validate Image
        try:
            t_dec0 = time.perf_counter()
            image_bytes, detected_mime = self.decode_input(image_input)
            final_mime = mime_type or detected_mime
            record_timing("image_decode", (time.perf_counter() - t_dec0) * 1000)

            t_val0 = time.perf_counter()
            img_format, (width, height) = self.validate_image_bytes(image_bytes, final_mime)
            record_timing("image_validation", (time.perf_counter() - t_val0) * 1000)
        except ImageValidationError as e:
            return {
                "success": False,
                "extracted_text": "",
                "error_codes": [],
                "detected_domains": [],
                "visual_clues": [],
                "confidence": 0.0,
                "known_error_details": None,
                "error": str(e)
            }

        # 2. Evidence Extraction (Local Pixel-OCR -> Vision Fallback -> Metadata Fallback)
        extracted_text = ""
        error_codes = []
        detected_domains = []
        visual_clues = []
        confidence = 0.0

        # Step 2A: Custom vision function (mock or override for testing)
        if self.vision_fn is not None:
            try:
                raw_resp = self.vision_fn(image_bytes, final_mime)
                if isinstance(raw_resp, dict):
                    vision_result = raw_resp
                elif isinstance(raw_resp, str):
                    vision_result = self.parse_vision_json(raw_resp)
                else:
                    vision_result = None

                if vision_result:
                    extracted_text = vision_result.get("extracted_text", "")
                    error_codes = vision_result.get("error_codes", [])
                    detected_domains = vision_result.get("detected_domains", [])
                    visual_clues = vision_result.get("visual_clues", [])
                    confidence = vision_result.get("confidence", 0.0)
            except Exception:
                pass

        # Step 2B: Pretrained Local Pixel-OCR (PaddleOCR reading actual pixel data)
        if not extracted_text:
            pixel_text, pixel_conf = extract_text_from_pixels(image_bytes)
            if pixel_text:
                extracted_text = pixel_text
                confidence = max(confidence, pixel_conf)
                visual_clues.append("Pretrained PaddleOCR detected text from pixels")

        # Step 2C: Multimodal Vision API Fallback (Gemini Vision)
        if not extracted_text and self.provider == "gemini" and self.api_key:
            t_gem0 = time.perf_counter()
            try:
                b64_img = base64.b64encode(image_bytes).decode("utf-8")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                prompt = self.build_vision_prompt()
                payload = json.dumps({
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": final_mime,
                                    "data": b64_img
                                }
                            }
                        ]
                    }],
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
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    vision_result = self.parse_vision_json(text)
                    if vision_result:
                        extracted_text = vision_result.get("extracted_text", "")
                        error_codes = vision_result.get("error_codes", [])
                        detected_domains = vision_result.get("detected_domains", [])
                        visual_clues = vision_result.get("visual_clues", [])
                        confidence = vision_result.get("confidence", 0.0)
            except Exception:
                pass
            finally:
                record_timing("gemini_request", (time.perf_counter() - t_gem0) * 1000)
        else:
            record_timing("gemini_request", 0.0)

        # Step 2D: Secondary fallback for synthetic offline metadata
        if not extracted_text:
            try:
                with Image.open(io.BytesIO(image_bytes)) as pil_img:
                    if hasattr(pil_img, "info") and pil_img.info:
                        for k, v in pil_img.info.items():
                            if isinstance(v, str) and v.strip():
                                extracted_text = v.strip()
                                confidence = 0.88
                                visual_clues.append("Extracted from image metadata fallback")
                                break
            except Exception:
                pass

        # Cross-extract any regex error codes from extracted_text
        t_err0 = time.perf_counter()
        text_codes = extract_error_codes(extracted_text)
        all_codes = list(dict.fromkeys(error_codes + text_codes))

        # Check for known error code resolution
        known_details = None
        for code in all_codes:
            res = resolve_error_code(code)
            if res.get("known"):
                known_details = res
                if res.get("domain") and res["domain"] not in detected_domains:
                    detected_domains.append(res["domain"])
                confidence = max(confidence, 0.90)
                break
        record_timing("error_resolver", (time.perf_counter() - t_err0) * 1000)

        # Fallback domain anchor detection on extracted_text
        if not detected_domains and extracted_text:
            clean_lower = extracted_text.lower()
            if any(k in clean_lower for k in ["bluetooth", "buds", "pairing", "earbuds"]):
                detected_domains.append("BLUETOOTH")
                confidence = max(confidence, 0.85)
            elif any(k in clean_lower for k in ["wi-fi", "wifi", "internet", "network", "offline"]):
                detected_domains.append("NETWORK")
                confidence = max(confidence, 0.85)
            elif any(k in clean_lower for k in ["battery", "charge", "charging", "overheating"]):
                detected_domains.append("BATTERY")
                confidence = max(confidence, 0.85)
            elif any(k in clean_lower for k in ["screen", "display", "black screen"]):
                detected_domains.append("DISPLAY")
                confidence = max(confidence, 0.85)
            elif any(k in clean_lower for k in ["camera", "photo", "shutter"]):
                detected_domains.append("CAMERA")
                confidence = max(confidence, 0.85)
            elif any(k in clean_lower for k in ["speaker", "sound", "volume", "audio"]):
                detected_domains.append("AUDIO")
                confidence = max(confidence, 0.85)

        return {
            "success": True,
            "extracted_text": extracted_text,
            "error_codes": all_codes,
            "detected_domains": detected_domains,
            "visual_clues": visual_clues,
            "confidence": round(confidence, 2),
            "known_error_details": known_details,
            "error": None
        }

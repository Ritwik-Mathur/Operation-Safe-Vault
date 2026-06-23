"""
Shadow Guard – Prompt Injection Protection Middleware
─────────────────────────────────────────────────────
Scans all incoming POST data for prompt injection patterns.
Blocks requests that try to manipulate the AI pipeline.
"""

import re
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


INJECTION_PATTERNS = [
    r"ignore (previous|all|prior|above) instructions",
    r"forget (everything|all|your instructions|your rules)",
    r"you are now",
    r"act as (a|an|if)",
    r"pretend (you are|to be)",
    r"disregard (your|all|previous)",
    r"new persona",
    r"jailbreak",
    r"dan mode",
    r"developer mode",
    r"(reveal|show|print|output) (your|the) (system|initial) prompt",
    r"<\|.*?\|>",
    r"\[INST\]",
    r"\[SYSTEM\]",
    r"###\s*(instruction|system|human|assistant)",
    r"ignore safety",
    r"bypass (filter|guard|safety|security)",
    r"do not (filter|censor|moderate|block)",
]

COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def detect_injection(text: str) -> Optional[str]:
    """Returns the matched pattern string or None."""
    for pattern in COMPILED:
        m = pattern.search(text)
        if m:
            return m.group()
    return None


def scrub_pii(text: str) -> str:
    """Remove PII (Personally Identifiable Information) from text."""
    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    # Remove phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    # Remove SSN
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    # Remove credit card numbers
    text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CC]', text)
    # Remove Aadhaar numbers
    text = re.sub(r'\b\d{4}\s\d{4}\s\d{4}\b', '[AADHAAR]', text)
    # Remove PAN numbers
    text = re.sub(r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN]', text)
    return text


class ShadowGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method != "POST":
            return await call_next(request)

        content_type = request.headers.get("content-type", "")

        if "multipart" in content_type:
            # Skip body scanning for multipart/form-data (file uploads).
            # Reading the body here consumes it and breaks FastAPI's UploadFile.
            # File content is binary — not a prompt injection surface.
            # Text fields in multipart are scanned by the route handler via Shadow Guard on extracted text.
            pass

        elif "application/x-www-form-urlencoded" in content_type:
            try:
                body_bytes = await request.body()
                from urllib.parse import parse_qs
                decoded = body_bytes.decode("utf-8", errors="ignore")
                params = parse_qs(decoded)
                for key, values in params.items():
                    for value in values:
                        match = detect_injection(value)
                        if match:
                            return JSONResponse(status_code=400, content={
                                "error": "Shadow Guard blocked this request.",
                                "reason": f"Prompt injection detected in '{key}': '{match}'",
                                "threat_level": "CRITICAL",
                            })
            except Exception:
                pass

        elif "json" in content_type:
            try:
                body = await request.json()
                flagged = _scan_json(body)
                if flagged:
                    return JSONResponse(status_code=400, content={
                        "error": "Shadow Guard blocked this request.",
                        "reason": f"Prompt injection detected at: {flagged}",
                        "threat_level": "CRITICAL",
                    })
            except Exception:
                pass

        return await call_next(request)


def _scan_json(obj, path="root") -> Optional[str]:
    if isinstance(obj, str):
        if detect_injection(obj):
            return path
    elif isinstance(obj, dict):
        for k, v in obj.items():
            result = _scan_json(v, f"{path}.{k}")
            if result:
                return result
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = _scan_json(item, f"{path}[{i}]")
            if result:
                return result
    return None

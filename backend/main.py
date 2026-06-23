"""
Fraud Shield AI – Unified Scam Detection API
═════════════════════════════════════════════
Best of Zora AI + Fraud Shield combined.
Multi-source input → Central Classifier → Risk Scoring → Human Feedback Loop
"""

import uuid
import json
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from fastapi import FastAPI, Request, UploadFile, File, Form, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from middleware.shadow_guard import ShadowGuardMiddleware
from middleware.dlp_guard import DLPGuardMiddleware
from core.vector_db import VectorDB
from core.classifier import CentralClassifier
from core.feedback import FeedbackStore
from core.threat_score import ThreatScore
from detectors.text_detector import TextDetector
from detectors.credential_detector import CredentialDetector
from detectors.url_detector import URLDetector
from detectors.voice_detector import VoiceDetector
from detectors.file_detector import FileDetector
from detectors.email_detector import EmailDetector, IMAPFetcher
from detectors.video_detector import VideoDetector
from core.live_call import process_chunk, end_call, get_detection_stats
from core.twilio_stream import get_or_create_handler, remove_handler
# Pre-import so matplotlib Agg backend + font cache load at startup, not on
# the first /analyze/voice request (eliminates ~1.7s first-call penalty).
from core import spectrogram_generator as _spec_warmup  # noqa: F401



# ── Startup ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.vector_db = VectorDB()
    app.state.vector_db.seed_known_scams()
    app.state.feedback = FeedbackStore()
    yield


# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Fraud Shield AI",
    description="Unified scam detection: SMS, Email, URL, Voice, Files — with deepfake detection, DLP, and human-in-the-loop feedback",
    version="2.0.0",
    lifespan=lifespan,
)

# Middleware stack (order matters – outermost first)
app.add_middleware(DLPGuardMiddleware)
app.add_middleware(ShadowGuardMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "Fraud Shield AI",
        "version": "2.0.0",
        "status": "running",
        "detectors": ["text", "credential", "url", "voice", "file", "email"],
        "middleware": ["shadow_guard", "dlp_guard"],
        "features": ["deepfake_detection", "ai_generated_text_detection", "human_feedback", "imap_integration"],
    }


# ── Individual Detectors ────────────────────────────────────────────────────

@app.post("/analyze/text")
async def analyze_text(
    message: str = Form(...),
    sender: str = Form(default="unknown"),
    channel: str = Form(default="sms"),
):
    """Analyze SMS or Email body for scam indicators."""
    detector = TextDetector(app.state.vector_db)
    text_result = detector.analyze(message, sender, channel)

    cred_detector = CredentialDetector()
    cred_result = cred_detector.analyze(message)

    combined = ThreatScore.combine({"text": text_result, "credential": cred_result})
    return {
        "analysis_id": str(uuid.uuid4())[:8],
        "components": {"text": text_result, "credential": cred_result},
        "combined": combined,
    }


@app.post("/analyze/url")
async def analyze_url(url: str = Form(...)):
    """Sandbox + SSL + WHOIS + heuristic URL analysis."""
    detector = URLDetector()
    result = await detector.analyze(url)
    result["analysis_id"] = str(uuid.uuid4())[:8]
    return result


@app.post("/analyze/voice")
async def analyze_voice(
    request: Request,
    audio: UploadFile = File(...),
    customer_id: Optional[str] = Form(default=None),
):
    """
    Acoustic + STT + deepfake voice analysis.

    Optional: pass `customer_id` (Form field) to also run speaker verification
    against the enrolled voice profile.  Response will include
    `speaker_match_score` (0–1) and `speaker_verified` (bool).
    """
    audio_bytes = await audio.read()
    detector = VoiceDetector(vector_db=request.app.state.vector_db)
    result = detector.analyze(audio_bytes, audio.filename, customer_id=customer_id)
    result["analysis_id"] = str(uuid.uuid4())[:8]

    # Promote speaker fields to the top-level response for convenience
    raw = result.get("raw", {})
    if customer_id is not None:
        result["speaker_match_score"] = raw.get("speaker_match_score")
        result["speaker_verified"] = raw.get("speaker_verified")

    return result


@app.post("/enroll-voice")
async def enroll_voice(
    customer_id: str = Form(...),
    audio: UploadFile = File(...),
):
    """
    Enroll a customer's voice for future speaker verification.

    Extracts a 192-dim speaker embedding via SpeechBrain ECAPA-TDNN and
    stores it under backend/data/voice_enrollments/<customer_id>.npy.

    On first call the model (~50 MB) is auto-downloaded from HuggingFace.
    Subsequent calls load instantly from the local cache.
    """
    try:
        from core.speaker_verification import enroll_speaker
        audio_bytes = await audio.read()
        result = enroll_speaker(customer_id, audio_bytes, audio.filename)
        result["analysis_id"] = str(uuid.uuid4())[:8]
        return result
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/analyze/video")
async def analyze_video(video: UploadFile = File(...)):
    """Video deepfake detection — temporal consistency + facial artifacts + AV sync."""
    video_bytes = await video.read()
    detector = VideoDetector()
    result = detector.analyze(video_bytes, video.filename)
    result["analysis_id"] = str(uuid.uuid4())[:8]
    return result


@app.post("/analyze/file")
async def analyze_file(attachment: UploadFile = File(...)):
    """YARA + ClamAV/VirusTotal file scan."""
    file_bytes = await attachment.read()
    detector = FileDetector()
    result = detector.analyze(file_bytes, attachment.filename)
    result["analysis_id"] = str(uuid.uuid4())[:8]
    return result


@app.post("/analyze/email")
async def analyze_email(
    raw_email: str = Form(default=""),
    body: str = Form(default=""),
    sender: str = Form(default="unknown"),
):
    """Analyze email headers (SPF/DKIM/DMARC) + body."""
    detector = EmailDetector()
    if raw_email:
        result = detector.analyze_raw(raw_email)
    else:
        result = detector.analyze_body(body, sender)
    result["analysis_id"] = str(uuid.uuid4())[:8]
    return result


# ── Full Analysis (Central Classifier) ──────────────────────────────────────

@app.post("/analyze/full")
async def analyze_full(
    message: str = Form(default=""),
    sender: str = Form(default="unknown"),
    channel: str = Form(default="sms"),
    url: str = Form(default=""),
    audio: UploadFile = File(default=None),
    attachment: UploadFile = File(default=None),
):
    """Run ALL available detectors and return a combined threat assessment."""
    classifier = CentralClassifier(app.state.vector_db)
    result = await classifier.classify(
        message=message,
        sender=sender,
        channel=channel,
        url=url,
        audio_bytes=(await audio.read()) if audio else None,
        audio_filename=audio.filename if audio else "",
        file_bytes=(await attachment.read()) if attachment else None,
        file_filename=attachment.filename if attachment else "",
    )
    result["analysis_id"] = str(uuid.uuid4())[:8]
    return result


# ── IMAP Email Scanning ─────────────────────────────────────────────────────

@app.post("/email/scan-inbox")
async def scan_inbox(
    imap_host: str = Form(...),
    email_addr: str = Form(...),
    password: str = Form(...),
    count: int = Form(default=10),
):
    """Connect to IMAP inbox and scan recent emails."""
    fetcher = IMAPFetcher(imap_host, email_addr, password)
    emails = fetcher.fetch_recent(count=count)
    detector = EmailDetector()
    text_det = TextDetector(app.state.vector_db)

    results = []
    for em in emails:
        if "error" in em:
            results.append(em)
            continue

        # Header analysis
        email_result = detector.analyze_raw(em.get("raw", ""))

        # Body text analysis
        body = em.get("body", "")
        text_result = text_det.analyze(body, em.get("from", "unknown"), "email") if body else None

        combined = ThreatScore.combine(
            {"email": email_result, **({"text": text_result} if text_result else {})}
        )

        results.append({
            "email_id": em.get("id"),
            "from": em.get("from"),
            "subject": em.get("subject"),
            "date": em.get("date"),
            "analysis": combined,
        })

    return {"emails_scanned": len(results), "results": results}


# ── Human-in-the-Loop Feedback ──────────────────────────────────────────────

@app.post("/feedback")
async def submit_feedback(
    analysis_id: str = Form(...),
    user_verdict: str = Form(...),  # "scam" | "safe" | "unsure"
    original_score: float = Form(default=0),
    original_verdict: str = Form(default=""),
    source: str = Form(default=""),
    original_input: str = Form(default=""),
    comment: str = Form(default=""),
):
    """Submit human feedback on an analysis result. Improves future accuracy."""
    entry = app.state.feedback.add_feedback(
        analysis_id=analysis_id,
        user_verdict=user_verdict,
        original_score=original_score,
        original_verdict=original_verdict,
        source=source,
        original_input=original_input,
        comment=comment,
    )

    # If user confirms it's a scam, add to vector DB for future matching
    if user_verdict == "scam" and original_input:
        app.state.vector_db.add_scam(original_input, reported_by="user_feedback")

    return {"status": "feedback recorded", "entry": entry}


@app.get("/feedback/stats")
async def feedback_stats():
    """Get accuracy statistics from user feedback."""
    return app.state.feedback.get_accuracy_stats()


@app.get("/feedback/recent")
async def recent_feedback(limit: int = Query(default=20)):
    """Get recent feedback entries."""
    return app.state.feedback.get_recent(limit=limit)


# ── Detection Timing Stats ───────────────────────────────────────────────────────────

@app.get("/detection-stats")
async def detection_stats():
    """
    Return aggregated timing stats for all completed live calls.

    Demonstrates the "flag within 10 seconds" checkpoint:
      - total_calls           – completed calls recorded in this session
      - total_flagged         – calls that crossed HIGH_RISK_THRESHOLD (70)
      - avg_time_to_alert     – mean seconds from call start to first HIGH-RISK flag
      - calls_flagged_under_10s – calls flagged in ≤ 10 seconds (the demo goal)
    """
    return get_detection_stats()


# ── Live Call WebSocket ──────────────────────────────────────────────────────

@app.websocket("/ws/live-call/{call_id}")
async def live_call_ws(websocket: WebSocket, call_id: str):
    """
    Real-time call analysis via WebSocket.

    Protocol:
      Client sends: binary audio chunks (5s WAV blobs)
      Server sends: JSON RiskState updates after each chunk
      Client sends: text "END" to close call and get final summary
    """
    await websocket.accept()
    vector_db = websocket.app.state.vector_db

    try:
        while True:
            message = await websocket.receive()

            # Text message — only "END" is supported
            if "text" in message:
                if message["text"].strip().upper() == "END":
                    state = end_call(call_id)
                    await websocket.send_text(json.dumps({
                        "type": "call_ended",
                        "final_score": round(state.current_score, 1) if state else 0,
                        "verdict": state.to_dict()["verdict"] if state else "UNKNOWN",
                        "full_transcript": state.transcript_so_far if state else "",
                        "intent_progression": state.intent_progression if state else [],
                    }))
                    break

            # Binary message — audio chunk
            elif "bytes" in message:
                audio_bytes = message["bytes"]
                if not audio_bytes:
                    continue

                result = process_chunk(call_id, audio_bytes, vector_db)
                result["type"] = "chunk_result"
                await websocket.send_text(json.dumps(result))

                # If alert threshold crossed (score ≥ 80) OR high-risk first-crossing
                # (score ≥ 70, first_alert_time just set), send a separate alert event.
                if result.get("alert") or result.get("high_risk_triggered"):
                    await websocket.send_text(json.dumps({
                        "type": "alert",
                        "call_id": call_id,
                        "score": result["current_score"],
                        "message": "HIGH RISK SCAM DETECTED — Advise caller to hang up immediately",
                        "intent_progression": result["intent_progression"],
                        # ── Timing instrumentation fields ────────────────────────
                        "elapsed_seconds": result.get("elapsed_seconds"),
                        "high_risk_triggered": result.get("high_risk_triggered", False),
                        "time_to_alert_seconds": result.get("time_to_alert_seconds"),
                    }))

    except WebSocketDisconnect:
        end_call(call_id)
    except RuntimeError as e:
        if "disconnect message" not in str(e):
            print(f"[WS ERROR] {call_id}: {e}")
        end_call(call_id)


# ── Twilio Media Stream WebSocket ────────────────────────────────────────────
# Frontend connects here to watch live scores
_frontend_sockets: dict[str, WebSocket] = {}

@app.websocket("/ws/dashboard/{call_id}")
async def dashboard_ws(websocket: WebSocket, call_id: str):
    """Frontend browser connects here to receive live score updates."""
    await websocket.accept()
    _frontend_sockets[call_id] = websocket
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        _frontend_sockets.pop(call_id, None)


@app.websocket("/ws/twilio-stream/{call_id}")
async def twilio_stream_ws(websocket: WebSocket, call_id: str):
    """
    Twilio Media Streams connects here.
    Configure this URL in Twilio console as the Stream URL.
    Format: wss://your-ngrok-url/ws/twilio-stream/{call_id}
    """
    await websocket.accept()
    vector_db = websocket.app.state.vector_db
    frontend_ws = _frontend_sockets.get(call_id)
    handler = get_or_create_handler(call_id, vector_db, frontend_ws)

    try:
        while True:
            message = await websocket.receive_text()
            result = await handler.handle_message(message)
            if result:
                print(f"[TWILIO STREAM] {call_id}: {result}")
    except WebSocketDisconnect:
        # Fix 5: Normal call end — not an error
        print(f"[TWILIO STREAM] {call_id}: call ended (WebSocket closed)")
        remove_handler(call_id)
        end_call(call_id)
    except Exception as e:
        err = str(e)
        # Fix 5: ABNORMAL_CLOSURE 1006 = Twilio hung up = normal
        if "1006" in err or "ABNORMAL_CLOSURE" in err or "going away" in err.lower():
            print(f"[TWILIO STREAM] {call_id}: call ended normally")
        else:
            print(f"[TWILIO STREAM ERROR] {call_id}: {e}")
        remove_handler(call_id)
        end_call(call_id)


@app.post("/twilio/voice-webhook")
async def twilio_voice_webhook(request: Request):
    """
    Twilio calls this HTTP endpoint when a call comes in.
    Returns TwiML that forks audio to our WebSocket stream.
    Set this as your Twilio phone number's Voice URL.
    """
    import os
    from urllib.parse import urlencode

    # Generate a unique call ID
    call_id = str(uuid.uuid4())[:8]
    ngrok_url = os.getenv("NGROK_URL", "").rstrip("/")

    if not ngrok_url:
        return {"error": "NGROK_URL not set in .env"}

    stream_url = f"wss://{ngrok_url.replace('https://', '').replace('http://', '')}/ws/twilio-stream/{call_id}"

    # TwiML response — tells Twilio to stream audio to us
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Start>
        <Stream url="{stream_url}" />
    </Start>
    <Say>This call is being monitored for fraud protection.</Say>
    <Pause length="60"/>
</Response>"""

    from fastapi.responses import Response
    return Response(content=twiml, media_type="application/xml")


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

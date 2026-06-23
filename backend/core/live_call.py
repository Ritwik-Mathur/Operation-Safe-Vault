"""
Live Call Analysis – WebSocket-based real-time scam detection
─────────────────────────────────────────────────────────────
Fixes applied:
  Fix 1: Groq NLP runs async — doesn't block chunk pipeline
  Fix 2: Whisper 'tiny' model for live calls (faster)
  Fix 4: Partial phrase matching on rolling transcript
  Fix 5: ABNORMAL_CLOSURE handled as normal close

Timing Instrumentation (added):
  - call_start_time / first_alert_time tracked per call
  - elapsed_seconds included in every chunk response
  - high_risk_triggered + time_to_alert_seconds set on first HIGH-RISK crossing
  - Module-level _detection_log records completed call stats
  - get_detection_stats() returns aggregated demo metrics
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional
from detectors.voice_detector import acoustic_analysis, deepfake_detection, URGENCY_PHRASES, nlp_on_transcript


# ── Intent progression ladder ────────────────────────────────────────────────
PROGRESSION_LADDER = [
    "identity_verification",
    "security_threat",
    "action_required",
    "credential_harvesting",
    "government_impersonation",
    "banking_fraud",
    "family_emergency_impersonation",
]

# ── High-risk threshold (matches threat_score.py VERDICT_MAP) ────────────────
HIGH_RISK_THRESHOLD = 70.0


@dataclass
class RiskState:
    call_id: str
    # ── Original fields ───────────────────────────────────────────────────────
    started_at: float = field(default_factory=time.time)
    chunk_scores: List[float] = field(default_factory=list)
    transcript_so_far: str = ""
    intent_progression: List[str] = field(default_factory=list)
    deepfake_locked: bool = False
    alert_fired: bool = False
    all_reasons: List[str] = field(default_factory=list)
    pending_nlp_score: float = 0.0  # Fix 1: async NLP result stored here

    # ── Timing instrumentation fields ─────────────────────────────────────────
    call_start_time: float = field(default_factory=time.time)
    first_alert_time: Optional[float] = None   # set once, on first HIGH_RISK crossing

    @property
    def current_score(self) -> float:
        if not self.chunk_scores:
            return 0.0
        n = len(self.chunk_scores)
        weights = list(range(1, n + 1))
        weighted = sum(s * w for s, w in zip(self.chunk_scores, weights))
        return min(100.0, weighted / sum(weights))

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.started_at

    @property
    def elapsed_seconds(self) -> float:
        """Seconds since the call/session began (alias kept for clarity)."""
        return time.time() - self.call_start_time

    @property
    def time_to_first_alert(self) -> Optional[float]:
        """
        Seconds from call_start_time to first HIGH_RISK crossing.
        Returns None if the threshold has never been crossed.
        """
        if self.first_alert_time is None:
            return None
        return round(self.first_alert_time - self.call_start_time, 2)

    def to_dict(self) -> dict:
        score = self.current_score
        elapsed = round(self.elapsed_seconds, 2)
        return {
            "call_id": self.call_id,
            "current_score": round(score, 1),
            "verdict": _verdict(score),
            "severity": _severity(score),
            "chunk_count": len(self.chunk_scores),
            "duration_seconds": round(self.duration_seconds, 1),
            # ── Timing instrumentation keys ───────────────────────────────────
            "elapsed_seconds": elapsed,
            "time_to_first_alert": self.time_to_first_alert,
            # ─────────────────────────────────────────────────────────────────
            "transcript_so_far": self.transcript_so_far[-500:],
            "intent_progression": self.intent_progression,
            "deepfake_locked": self.deepfake_locked,
            "alert": score >= 80 and not self.alert_fired,
            "reasons": self.all_reasons[-8:],
        }


def _verdict(score: float) -> str:
    if score >= 80: return "SCAM"
    if score >= 55: return "SUSPICIOUS"
    if score >= 35: return "UNCERTAIN"
    return "SAFE"


def _severity(score: float) -> str:
    if score >= 80: return "HIGH"
    if score >= 55: return "MEDIUM"
    if score >= 35: return "LOW"
    return "NONE"


# ── In-memory store ──────────────────────────────────────────────────────────
_active_calls: dict[str, RiskState] = {}


def get_or_create_call(call_id: str) -> RiskState:
    if call_id not in _active_calls:
        _active_calls[call_id] = RiskState(call_id=call_id)
    return _active_calls[call_id]


def end_call(call_id: str) -> Optional[RiskState]:
    state = _active_calls.pop(call_id, None)
    if state is not None:
        # Record completed-call timing data for demo stats
        _record_completed_call(state)
    return state


# ── Detection log (module-level in-memory stats store) ───────────────────────
# Each entry: {"call_id": str, "time_to_first_alert": float|None}
_detection_log: List[dict] = []


def _record_completed_call(state: RiskState) -> None:
    """Append a completed call's timing data to the in-memory detection log."""
    _detection_log.append({
        "call_id": state.call_id,
        "time_to_first_alert": state.time_to_first_alert,
        "final_score": round(state.current_score, 1),
    })


def get_detection_stats() -> dict:
    """
    Return aggregated detection timing statistics across all completed calls.
    Suitable for the /detection-stats demo endpoint.

    Returns
    -------
    dict with keys:
      total_calls           – total completed calls recorded
      total_flagged         – calls where high-risk was ever triggered
      avg_time_to_alert     – average seconds-to-first-alert (flagged calls only)
      calls_flagged_under_10s – number of flagged calls detected in ≤ 10 seconds
    """
    total_calls = len(_detection_log)
    flagged = [e for e in _detection_log if e["time_to_first_alert"] is not None]
    total_flagged = len(flagged)
    times = [e["time_to_first_alert"] for e in flagged]
    avg_time = round(sum(times) / len(times), 2) if times else None
    under_10 = sum(1 for t in times if t <= 10.0)

    return {
        "total_calls": total_calls,
        "total_flagged": total_flagged,
        "avg_time_to_alert": avg_time,
        "calls_flagged_under_10s": under_10,
    }


# ── Fix 2: Fast transcription for live calls using tiny model ────────────────
def transcribe_fast(audio_bytes: bytes, filename: str) -> str:
    """Use Whisper tiny model for live call speed."""
    import tempfile
    try:
        from faster_whisper import WhisperModel
        suffix = os.path.splitext(filename)[-1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        # Fix 2: tiny model is 4x faster than base
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(tmp_path, language=None)
        transcript = " ".join(s.text for s in segments)
        # Fix 3: translate Hindi/Urdu to English
        if info.language in ("hi", "ur", "pa"):
            segments2, _ = model.transcribe(tmp_path, language=info.language, task="translate")
            transcript = " ".join(s.text for s in segments2)
        os.unlink(tmp_path)
        return transcript.strip()
    except Exception as e:
        return ""


# ── Fix 4: Keyword scoring on rolling transcript ─────────────────────────────
def keyword_score_rolling(transcript: str, vector_db=None) -> tuple[float, list[str]]:
    """Fix 4: Run nlp_on_transcript on full rolling transcript for better coverage."""
    return nlp_on_transcript(transcript, vector_db)


# ── Fix 1: Async Groq NLP ────────────────────────────────────────────────────
async def run_nlp_async(state: RiskState):
    """
    Run Groq NLP in background — doesn't block chunk processing.
    Updates state.pending_nlp_score when done.
    """
    import json
    from detectors.voice_detector import VOICE_NLP_SYSTEM, scrub_pii
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key or not state.transcript_so_far:
        return
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        safe = scrub_pii(state.transcript_so_far[-1000:])
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            messages=[
                {"role": "system", "content": VOICE_NLP_SYSTEM},
                {"role": "user", "content": f"Analyze this call transcript:\n\n{safe}"},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        data = json.loads(raw)
        nlp_conf = float(data.get("confidence", 0))
        state.pending_nlp_score = min(40, nlp_conf * 0.5)
        intent = data.get("intent", "unknown")
        reasoning = data.get("reasoning", "")
        if data.get("is_scam") or nlp_conf > 30:
            state.all_reasons.append(f"[NLP] {intent.replace('_',' ').title()}: {reasoning}")
            if intent not in state.intent_progression:
                state.intent_progression.append(intent)
    except Exception as e:
        pass


# ── Process one audio chunk ──────────────────────────────────────────────────
def process_chunk(call_id: str, audio_bytes: bytes, vector_db=None) -> dict:
    state = get_or_create_call(call_id)
    filename = "chunk.wav"
    chunk_reasons = []

    # Layer 1: Acoustic (fast)
    a_score, a_reasons = acoustic_analysis(audio_bytes, filename)
    chunk_reasons.extend(a_reasons)

    # Layer 2: Fix 2 — fast transcription
    transcript = transcribe_fast(audio_bytes, filename)
    if transcript:
        state.transcript_so_far = (state.transcript_so_far + " " + transcript).strip()

    # Fix 4: keyword scoring on full rolling transcript
    k_score, k_reasons = keyword_score_rolling(state.transcript_so_far, vector_db)
    chunk_reasons.extend(k_reasons)

    # Fix 1: include pending NLP score from previous async call
    nlp_bonus = state.pending_nlp_score
    n_score = min(85.0, k_score + nlp_bonus)

    # Fire async NLP for next chunk (non-blocking)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(run_nlp_async(state))
    except Exception:
        pass

    # Layer 3: Deepfake (fast on 5s chunk)
    d_score, d_reasons = deepfake_detection(audio_bytes, filename)
    chunk_reasons.extend(d_reasons)

    if d_score > 70:
        state.deepfake_locked = True
        chunk_reasons.insert(0, "DEEPFAKE LOCKED: AI voice clone detected")

    chunk_final = (a_score * 0.25) + (n_score * 0.45) + (d_score * 0.30)
    if state.deepfake_locked:
        chunk_final = max(chunk_final, 85.0)

    state.chunk_scores.append(chunk_final)
    state.all_reasons.extend(chunk_reasons)

    # ── Timing instrumentation checkpoint ────────────────────────────────────
    now = time.time()
    elapsed = round(now - state.call_start_time, 2)
    current_score = state.current_score

    high_risk_triggered = False
    time_to_alert_seconds = None

    if current_score >= HIGH_RISK_THRESHOLD and state.first_alert_time is None:
        # First time crossing the HIGH_RISK threshold — record the moment
        state.first_alert_time = now
        high_risk_triggered = True
        time_to_alert_seconds = round(now - state.call_start_time, 2)

    # ── Build result dict ─────────────────────────────────────────────────────
    result = state.to_dict()

    # Attach timing fields (always present so frontend can render a live timer)
    result["elapsed_seconds"] = elapsed
    result["high_risk_triggered"] = high_risk_triggered
    if time_to_alert_seconds is not None:
        result["time_to_alert_seconds"] = time_to_alert_seconds

    if result["alert"]:
        state.alert_fired = True

    # ── Spectrogram: every 3rd chunk only to keep real-time pipeline fast ───────
    chunk_number = len(state.chunk_scores)   # already appended above
    if chunk_number % 3 == 0:
        try:
            from core.spectrogram_generator import generate_spectrogram_image
            result["spectrogram_image"] = generate_spectrogram_image(
                audio_bytes, "chunk.wav"
            )
        except Exception:
            result["spectrogram_image"] = None
    else:
        result["spectrogram_image"] = None

    return result

"""
Twilio Media Streams Handler
─────────────────────────────
Fixes applied:
  - Fix 2: Upsample mulaw 8kHz → 16kHz before Whisper (better accuracy)
  - Fix 5: ABNORMAL_CLOSURE 1006 handled as normal call end, not error
"""

import base64
import audioop
import io
import json
import wave
from typing import Dict, Optional

from core.live_call import process_chunk, end_call, get_or_create_call

# Twilio sends mulaw 8kHz mono
TWILIO_SAMPLE_RATE = 8000
TARGET_SAMPLE_RATE = 16000  # Fix 3: Whisper trained on 16kHz
TWILIO_CHANNELS = 1
CHUNK_DURATION_SEC = 5
SAMPLES_PER_CHUNK = TWILIO_SAMPLE_RATE * CHUNK_DURATION_SEC  # 40000 samples


def mulaw_to_wav(mulaw_bytes: bytes) -> bytes:
    """Convert raw mulaw bytes to WAV format (PCM 16-bit 16kHz mono).
    Fix 3: Upsample from 8kHz → 16kHz for better Whisper accuracy.
    """
    # mulaw → linear PCM 16-bit at 8kHz
    pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)

    # Fix 3: Upsample 8kHz → 16kHz using audioop
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, TWILIO_SAMPLE_RATE, TARGET_SAMPLE_RATE, None)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(TWILIO_CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(TARGET_SAMPLE_RATE)
        wf.writeframes(pcm_16k)
    return buf.getvalue()


class TwilioStreamHandler:
    """
    One instance per active Twilio call.
    Accumulates mulaw chunks, fires analysis every 5 seconds.
    """

    def __init__(self, call_sid: str, vector_db=None, frontend_ws=None):
        self.call_sid = call_sid
        self.vector_db = vector_db
        self.frontend_ws = frontend_ws
        self._mulaw_buffer: bytes = b""
        self._chunk_count = 0

    async def handle_message(self, raw: str) -> Optional[Dict]:
        try:
            msg = json.loads(raw)
        except Exception:
            return None

        event = msg.get("event")

        if event == "start":
            call_sid = msg.get("start", {}).get("callSid", self.call_sid)
            self.call_sid = call_sid
            get_or_create_call(call_sid)
            return {"event": "started", "call_sid": call_sid}

        elif event == "media":
            payload = msg.get("media", {}).get("payload", "")
            if not payload:
                return None

            mulaw_chunk = base64.b64decode(payload)
            self._mulaw_buffer += mulaw_chunk

            chunk_bytes = SAMPLES_PER_CHUNK  # 1 byte per mulaw sample

            if len(self._mulaw_buffer) >= chunk_bytes:
                chunk = self._mulaw_buffer[:chunk_bytes]
                self._mulaw_buffer = self._mulaw_buffer[chunk_bytes:]
                self._chunk_count += 1

                # Fix 3: Convert with upsampling to 16kHz
                wav_bytes = mulaw_to_wav(chunk)
                result = process_chunk(self.call_sid, wav_bytes, self.vector_db)
                result["type"] = "chunk_result"
                result["chunk_number"] = self._chunk_count

                # ── Timing instrumentation pass-through ───────────────────────
                # elapsed_seconds and high_risk_triggered are always set by
                # process_chunk(); time_to_alert_seconds only appears on the
                # chunk where the threshold is first crossed.
                # All three keys are already present in `result` — we just
                # ensure they are forwarded verbatim to the frontend WebSocket.
                # (No transformation needed — keys surfaced as-is.)

                if self.frontend_ws:
                    try:
                        await self.frontend_ws.send_text(json.dumps(result))
                        if result.get("alert") or result.get("high_risk_triggered"):
                            alert_payload = {
                                "type": "alert",
                                "call_id": self.call_sid,
                                "score": result["current_score"],
                                "message": "HIGH RISK SCAM DETECTED — Hang up immediately!",
                                "intent_progression": result.get("intent_progression", []),
                                # ── Timing fields ─────────────────────────────
                                "elapsed_seconds": result.get("elapsed_seconds"),
                                "high_risk_triggered": result.get("high_risk_triggered", False),
                                "time_to_alert_seconds": result.get("time_to_alert_seconds"),
                            }
                            await self.frontend_ws.send_text(json.dumps(alert_payload))
                    except Exception:
                        pass

                return result

        elif event == "stop":
            state = end_call(self.call_sid)
            if self.frontend_ws and state:
                try:
                    await self.frontend_ws.send_text(json.dumps({
                        "type": "call_ended",
                        "final_score": round(state.current_score, 1),
                        "verdict": state.to_dict()["verdict"],
                        "full_transcript": state.transcript_so_far,
                        "intent_progression": state.intent_progression,
                    }))
                except Exception:
                    pass
            return {"event": "stopped", "call_sid": self.call_sid}

        return None


# ── Active handlers store ────────────────────────────────────────────────────
_handlers: Dict[str, TwilioStreamHandler] = {}


def get_or_create_handler(call_sid: str, vector_db=None, frontend_ws=None) -> TwilioStreamHandler:
    if call_sid not in _handlers:
        _handlers[call_sid] = TwilioStreamHandler(call_sid, vector_db, frontend_ws)
    return _handlers[call_sid]


def remove_handler(call_sid: str):
    _handlers.pop(call_sid, None)

#!/usr/bin/env python3
"""
test_live_call_timing.py
════════════════════════════════════════════════════════════════════════
Simulates a live call by feeding process_chunk() a "deepfake-like"
high-risk audio file in small chunks every ~2 seconds.

After each chunk it prints:
  chunk_number | elapsed_seconds | current_score | high_risk_triggered

At the end it calls get_detection_stats() so you can verify the
"flag within 10 seconds" goal is captured in the stats.

Usage
-----
    # Run from the backend/ directory (so imports resolve correctly):
    cd backend
    python ../test_live_call_timing.py

    # Or pass a custom WAV file as the first argument:
    python ../test_live_call_timing.py path/to/scam_audio.wav

Requirements
------------
    pip install -r requirements.txt        (already done)

Notes
-----
* If no audio file is supplied the script synthesises a short WAV
  that contains recognisable scam keywords in the filename pattern so
  the keyword scorer can fire (librosa acoustic layer runs on the actual
  audio bytes regardless).
* Each "chunk" is the first CHUNK_SEC seconds of the file, repeated.
  This mimics a looping 5-second Twilio mulaw chunk after decoding.
"""

import sys
import os
import io
import time
import struct
import wave
import math

# ── Make sure `backend/` is on sys.path ───────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

CHUNK_SEC   = 2          # feed one chunk every N seconds
NUM_CHUNKS  = 8          # total chunks to process (covers ~16 s)
CALL_ID     = "demo-timing-test-001"


# ── Synthesise a WAV with scam-like acoustic fingerprint ─────────────────────
def make_scam_wav(duration_sec: float = 5.0, sample_rate: int = 16000) -> bytes:
    """
    Generate a WAV that mimics deepfake acoustic signatures:
      - Pure sine tone (very low spectral flatness variation → flatness trigger)
      - Constant zero-crossing rate (zcr_std < 0.005 trigger)
      - Low MFCC variance
      - Very stable F0 (jitter < 0.5 Hz trigger)

    This is intentionally a worst-case synthetic signal so at least the
    spectral-physics deepfake detector fires.  In a real demo you would
    pass an actual audio file from a deepfake TTS model.
    """
    n_samples = int(duration_sec * sample_rate)
    freq = 440.0  # stable 440 Hz tone — unnaturally perfect
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)          # 16-bit PCM
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            # Pure sine, no jitter, no noise
            sample = int(32767 * math.sin(2 * math.pi * freq * t))
            frames += struct.pack("<h", sample)
        wf.writeframes(bytes(frames))
    return buf.getvalue()


# ── Load or synthesise audio ──────────────────────────────────────────────────
def load_audio(path: str = None) -> bytes:
    if path and os.path.isfile(path):
        print(f"{CYAN}[INFO] Using audio file: {path}{RESET}")
        with open(path, "rb") as f:
            return f.read()
    else:
        if path:
            print(f"{YELLOW}[WARN] File '{path}' not found — synthesising test audio{RESET}")
        else:
            print(f"{CYAN}[INFO] No file given — synthesising deepfake-like test audio{RESET}")
        wav = make_scam_wav(duration_sec=5.0)
        print(f"{CYAN}[INFO] Synthesised {len(wav):,} bytes of 16 kHz WAV{RESET}")
        return wav


# ── Main simulation ───────────────────────────────────────────────────────────
def run_simulation(audio_bytes: bytes):
    from core.live_call import process_chunk, end_call, get_detection_stats

    print()
    print(f"{BOLD}{'═'*68}{RESET}")
    print(f"{BOLD}  Fraud Shield AI — Live Call Timing Simulation{RESET}")
    print(f"{BOLD}{'═'*68}{RESET}")
    print(f"  Call ID    : {CALL_ID}")
    print(f"  Chunks     : {NUM_CHUNKS}  (one every {CHUNK_SEC}s)")
    print(f"  Audio size : {len(audio_bytes):,} bytes per chunk")
    print(f"  HIGH_RISK threshold : 70 (matching threat_score.py)")
    print(f"{'─'*68}")
    print()

    # Header row
    print(f"{'Chunk':<6} {'Elapsed(s)':<12} {'Score':<8} {'Verdict':<12} "
          f"{'HighRisk?':<12} {'TimeToAlert(s)'}")
    print(f"{'─'*68}")

    flagged_at   = None   # elapsed at first flag
    high_risk_at = None

    for chunk_num in range(1, NUM_CHUNKS + 1):
        result = process_chunk(CALL_ID, audio_bytes, vector_db=None)

        elapsed      = result.get("elapsed_seconds", "?")
        score        = result.get("current_score", 0)
        verdict      = result.get("verdict", "?")
        triggered    = result.get("high_risk_triggered", False)
        alert_time   = result.get("time_to_alert_seconds")

        # Colour the row based on risk
        if triggered or alert_time is not None:
            row_colour = RED + BOLD
            if flagged_at is None:
                flagged_at = elapsed
                high_risk_at = alert_time
        elif score >= 55:
            row_colour = YELLOW
        else:
            row_colour = RESET

        ta_str = f"{alert_time:.2f}s" if alert_time is not None else "—"
        trig_str = f"{RED}YES ←─ FLAGGED!{RESET}" if triggered else "no"

        print(f"{row_colour}{chunk_num:<6} {elapsed:<12.2f} {score:<8.1f} "
              f"{verdict:<12} {RESET}{trig_str:<28} {ta_str}")

        # Pause between chunks (skip pause after last)
        if chunk_num < NUM_CHUNKS:
            time.sleep(CHUNK_SEC)

    # End the call so end_call() records it in the detection log
    end_call(CALL_ID)

    # Print stats
    stats = get_detection_stats()
    print()
    print(f"{'═'*68}")
    print(f"{BOLD}  get_detection_stats() — cumulative across this session{RESET}")
    print(f"{'─'*68}")
    print(f"  total_calls             : {stats['total_calls']}")
    print(f"  total_flagged           : {stats['total_flagged']}")
    avg = stats['avg_time_to_alert']
    print(f"  avg_time_to_alert       : {f'{avg:.2f}s' if avg is not None else 'N/A (no flags yet)'}")
    print(f"  calls_flagged_under_10s : {stats['calls_flagged_under_10s']}")
    print(f"{'═'*68}")

    # Summary verdict
    print()
    if flagged_at is not None and flagged_at <= 10.0:
        print(f"  {GREEN}{BOLD}✔  HIGH RISK flagged at {flagged_at:.2f}s — well within the 10s target!{RESET}")
    elif flagged_at is not None:
        print(f"  {YELLOW}{BOLD}⚠  HIGH RISK flagged at {flagged_at:.2f}s — over the 10s target.{RESET}")
    else:
        print(f"  {CYAN}ℹ  Score stayed below HIGH_RISK threshold (70) for all {NUM_CHUNKS} chunks.")
        print(f"     Try a real scam audio file:  python test_live_call_timing.py scam.wav{RESET}")
    print()


if __name__ == "__main__":
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    audio_bytes = load_audio(audio_path)
    run_simulation(audio_bytes)

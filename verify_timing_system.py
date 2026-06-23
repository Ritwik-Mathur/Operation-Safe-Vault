#!/usr/bin/env python3
"""
verify_timing_system.py
═══════════════════════════════════════════════════════════════════════════
THOROUGH VERIFICATION of the "flag within 10 seconds" timing system.

Tests:
  A) Deepfake-like audio  → expects current_score ≥ 70,
                            high_risk_triggered fires ONCE,
                            time_to_alert_seconds ≤ 10
  B) Safe/clean audio     → expects high_risk_triggered NEVER fires,
                            time_to_alert_seconds stays None throughout
  C) detection_stats      → confirms total_calls=2, real numbers

Run from project root:
    cd "Fraud-Shield-AI-main (2)\\Fraud-Shield-AI-main"
    python verify_timing_system.py
"""

import sys, os, io, wave, math, struct, time

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# ── ANSI colours ─────────────────────────────────────────────────────────────
G  = "\033[92m";  Y = "\033[93m";  R = "\033[91m"
C  = "\033[96m";  B = "\033[1m";   RESET = "\033[0m"
OK = f"{G}{B}PASS{RESET}"; FAIL = f"{R}{B}FAIL{RESET}"

CHUNK_INTERVAL = 2   # seconds between chunks (keeps elapsed honest)
NUM_CHUNKS     = 6   # feed 6 chunks per call → up to ~12 s elapsed

# ─────────────────────────────────────────────────────────────────────────────
# Audio generators
# ─────────────────────────────────────────────────────────────────────────────

def make_pure_sine_wav(duration=5.0, sr=16000, freq=440.0) -> bytes:
    """
    Pure stable 440 Hz tone – designed to maximise deepfake_detection score:
      • Spectral flatness ~ 0      (narrow-band  → may skip flatness trigger)
      • ZCR very consistent        → zcr_std < 0.005       → +20
      • MFCC variance very low     → mfcc_var  < 3         → +20
      • F0 perfectly stable        → jitter   < 0.5 Hz     → +20
      • Spectral centroid constant → centroid_std < 80 Hz  → +15
    Expected d_score ≈ 75 → triggers deepfake_locked → chunk_final capped at 85
    """
    n = int(duration * sr)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            s = int(32767 * math.sin(2 * math.pi * freq * i / sr))
            frames += struct.pack("<h", s)
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def make_safe_wav(duration=5.0, sr=16000) -> bytes:
    """
    Frequency-sweeping chirp + pink-ish noise – mimics natural speech variation:
      • Sweeping frequency    → large centroid_std  → NO centroid trigger
      • Varying ZCR           → zcr_std > 0.005     → NO ZCR trigger
      • High MFCC variance    → mfcc_var > 3        → NO MFCC trigger
      • F0 shifts constantly  → jitter > 0.5 Hz     → NO jitter trigger
    Expected d_score < 40 → deepfake_locked stays False → low final score
    """
    import random
    rng = random.Random(42)
    n = int(duration * sr)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            t = i / sr
            # chirp: 80 Hz → 2800 Hz over duration
            f = 80 + (2720 * t / duration)
            # add noise overtones and pink-ish randomness
            signal = (
                0.5 * math.sin(2 * math.pi * f * t)
                + 0.25 * math.sin(2 * math.pi * f * 2.0 * t + 0.5)
                + 0.15 * math.sin(2 * math.pi * f * 3.1 * t + 1.2)
                + 0.10 * (rng.random() * 2 - 1)   # white noise component
            )
            s = int(16000 * signal)
            frames += struct.pack("<h", max(-32767, min(32767, s)))
        wf.writeframes(bytes(frames))
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def print_banner(title: str):
    print(f"\n{B}{'═'*70}{RESET}")
    print(f"{B}  {title}{RESET}")
    print(f"{B}{'═'*70}{RESET}\n")

def print_table_header():
    print(f"  {'Chunk':<6} {'Elapsed':>10}  {'Score':>7}  {'Verdict':<12} "
          f"{'HighRiskTriggered':<20} {'TimeToAlert'}")
    print(f"  {'─'*6} {'─'*10}  {'─'*7}  {'─'*12} {'─'*20} {'─'*12}")

def colour_row(score, triggered):
    if triggered:         return R + B
    if score >= 70:       return R
    if score >= 55:       return Y
    return RESET

def verdict_for(p, label, detail=""):
    mark = OK if p else FAIL
    print(f"  {mark}  {label}{('  ← ' + detail) if detail else ''}")
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Single call runner – returns summary dict
# ─────────────────────────────────────────────────────────────────────────────

def run_call(call_id: str, audio_bytes: bytes, label: str) -> dict:
    from core.live_call import process_chunk, end_call

    print_banner(f"TEST {label}")
    print(f"  call_id   : {call_id}")
    print(f"  audio     : {len(audio_bytes):,} bytes per chunk")
    print(f"  chunks    : {NUM_CHUNKS} × {CHUNK_INTERVAL}s = up to {NUM_CHUNKS*CHUNK_INTERVAL}s elapsed\n")
    print_table_header()

    results         = []
    trigger_count   = 0
    trigger_chunks  = []
    max_score       = 0.0
    all_elapsed     = []

    for i in range(1, NUM_CHUNKS + 1):
        r = process_chunk(call_id, audio_bytes, vector_db=None)

        elapsed   = r.get("elapsed_seconds")
        score     = r.get("current_score", 0.0)
        verdict   = r.get("verdict", "?")
        triggered = r.get("high_risk_triggered", False)
        tta       = r.get("time_to_alert_seconds")

        results.append(r)
        all_elapsed.append(elapsed)
        max_score = max(max_score, score)

        if triggered:
            trigger_count += 1
            trigger_chunks.append(i)

        c = colour_row(score, triggered)
        tta_str = f"{tta:.2f}s" if tta is not None else "None"
        trig_str = f"{R}{B}YES ← FIRST CROSSING{RESET}" if triggered else "no"

        print(f"{c}  {i:<6} {elapsed:>10.2f}  {score:>7.1f}  {verdict:<12} {RESET}"
              f"{trig_str:<38} {tta_str}")

        # pause between chunks so elapsed_seconds advances realistically
        if i < NUM_CHUNKS:
            time.sleep(CHUNK_INTERVAL)

    state = end_call(call_id)

    # ── Did elapsed actually grow? ────────────────────────────────────────────
    elapsed_grew = (all_elapsed[-1] - all_elapsed[0]) >= (CHUNK_INTERVAL * (NUM_CHUNKS - 1) * 0.8)

    # ── time_to_alert from stored state (definitive source) ──────────────────
    tta_final = state.time_to_first_alert if state else None

    # Find the chunk result that had triggered=True
    trigger_tta = next(
        (r.get("time_to_alert_seconds") for r in results if r.get("high_risk_triggered")),
        None
    )

    return {
        "results":        results,
        "trigger_count":  trigger_count,
        "trigger_chunks": trigger_chunks,
        "max_score":      max_score,
        "elapsed_start":  all_elapsed[0],
        "elapsed_end":    all_elapsed[-1],
        "elapsed_grew":   elapsed_grew,
        "tta_final":      tta_final,
        "trigger_tta":    trigger_tta,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SHOW CODE EXCERPTS (Requirement 1)
# ─────────────────────────────────────────────────────────────────────────────

def show_code_excerpts():
    print_banner("1. CODE REVIEW — Key sections")
    live_call_path = os.path.join(BACKEND, "core", "live_call.py")
    with open(live_call_path) as f:
        lines = f.readlines()

    sections = {
        "RiskState class (fields + properties)": (41, 105),
        "get_detection_stats()":                 (154, 179),
        "process_chunk() timing block":          (252, 325),
    }
    for title, (start, end) in sections.items():
        print(f"  {C}{B}── {title} (lines {start}–{end}) ──{RESET}")
        for i, ln in enumerate(lines[start-1:end], start=start):
            print(f"  {i:4d}: {ln}", end="")
        print()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    from core.live_call import get_detection_stats

    # 1. Show code
    show_code_excerpts()

    # ── Generate audio ────────────────────────────────────────────────────────
    print_banner("Generating test audio")
    deepfake_wav = make_pure_sine_wav(duration=5.0, sr=16000, freq=440.0)
    safe_wav     = make_safe_wav(duration=5.0, sr=16000)
    print(f"  deepfake_wav : {len(deepfake_wav):,} bytes  (pure 440 Hz sine → stable spectral signature)")
    print(f"  safe_wav     : {len(safe_wav):,}  bytes  (chirp + noise → natural-speech variation)")

    # ── Test A: deepfake audio ────────────────────────────────────────────────
    A = run_call("verify-deepfake-001", deepfake_wav, "A — DEEPFAKE-LIKE AUDIO")

    # ── Test B: safe audio ────────────────────────────────────────────────────
    B = run_call("verify-safe-001",     safe_wav,    "B — SAFE / CLEAN AUDIO")

    # ── Detection stats ───────────────────────────────────────────────────────
    stats = get_detection_stats()

    # ─────────────────────────────────────────────────────────────────────────
    # VERDICTS
    # ─────────────────────────────────────────────────────────────────────────
    print_banner("PASS / FAIL VERDICTS")

    all_pass = True

    # ── TEST A verdicts ───────────────────────────────────────────────────────
    print(f"  {B}{C}── Test A (deepfake audio) ──{RESET}\n")

    # A1: score crossed 70?
    p = A["max_score"] >= 70.0
    all_pass &= p
    verdict_for(p, f"A1  current_score crossed 70",
                f"highest score = {A['max_score']:.1f}")

    # A2: high_risk_triggered fired at least once?
    p = A["trigger_count"] >= 1
    all_pass &= p
    verdict_for(p, f"A2  high_risk_triggered fired",
                f"fired {A['trigger_count']} time(s) on chunk(s) {A['trigger_chunks']}")

    # A3: high_risk_triggered fired EXACTLY once (no re-fire)?
    p = A["trigger_count"] == 1
    all_pass &= p
    verdict_for(p, "A3  fired exactly once (no re-fire)",
                f"fired on chunks: {A['trigger_chunks']}")

    # A4: time_to_alert ≤ 10 s?
    tta = A["tta_final"]
    p = tta is not None and tta <= 10.0
    all_pass &= p
    verdict_for(p, "A4  time_to_alert_seconds ≤ 10 s",
                f"time_to_alert = {tta}")

    # A4b: time_to_alert_seconds in result dict matches state.time_to_first_alert?
    p = (A["trigger_tta"] is not None) and (
        A["tta_final"] is not None) and (
        abs(A["trigger_tta"] - A["tta_final"]) < 0.05)
    all_pass &= p
    verdict_for(p, "A4b result dict time_to_alert matches state.time_to_first_alert",
                f"result={A['trigger_tta']}, state={A['tta_final']}")

    # A5: elapsed_seconds increases monotonically and matches real time?
    p = A["elapsed_grew"]
    all_pass &= p
    verdict_for(p, "A5  elapsed_seconds grew across chunks",
                f"chunk1={A['elapsed_start']:.2f}s → chunk{NUM_CHUNKS}={A['elapsed_end']:.2f}s")

    print()

    # ── TEST B verdicts ───────────────────────────────────────────────────────
    print(f"  {B}{C}── Test B (safe audio) ──{RESET}\n")

    # B1: high_risk_triggered never fired
    p = B["trigger_count"] == 0
    all_pass &= p
    verdict_for(p, "B1  high_risk_triggered never fired (negative case)",
                f"fired {B['trigger_count']} times, max_score={B['max_score']:.1f}")

    # B2: time_to_alert_seconds stayed None throughout
    p = B["tta_final"] is None
    all_pass &= p
    verdict_for(p, "B2  time_to_alert_seconds stayed None throughout call",
                f"tta_final={B['tta_final']}")

    # B3: elapsed_seconds still grew (timer works in both modes)
    p = B["elapsed_grew"]
    all_pass &= p
    verdict_for(p, "B3  elapsed_seconds grew even in safe call",
                f"chunk1={B['elapsed_start']:.2f}s → chunk{NUM_CHUNKS}={B['elapsed_end']:.2f}s")

    print()

    # ── Detection stats verdicts ──────────────────────────────────────────────
    print(f"  {B}{C}── Detection Stats (GET /detection-stats) ──{RESET}\n")
    print(f"  Raw JSON: {stats}\n")

    p = stats["total_calls"] == 2
    all_pass &= p
    verdict_for(p, "C1  total_calls == 2 (both calls recorded)",
                f"total_calls={stats['total_calls']}")

    p = stats["total_flagged"] >= 1
    all_pass &= p
    verdict_for(p, "C2  total_flagged ≥ 1 (at least deepfake call counted)",
                f"total_flagged={stats['total_flagged']}")

    p = stats["avg_time_to_alert"] is not None
    all_pass &= p
    verdict_for(p, "C3  avg_time_to_alert is a real number (not None/null)",
                f"avg_time_to_alert={stats['avg_time_to_alert']}")

    p = stats["calls_flagged_under_10s"] >= 1
    all_pass &= p
    verdict_for(p, "C4  calls_flagged_under_10s ≥ 1",
                f"calls_flagged_under_10s={stats['calls_flagged_under_10s']}")

    # ── Overall verdict ───────────────────────────────────────────────────────
    print(f"\n  {'─'*60}")
    if all_pass:
        print(f"  {G}{B}✔  ALL CHECKS PASSED — timing system is fully functional{RESET}")
    else:
        print(f"  {R}{B}✘  ONE OR MORE CHECKS FAILED — see FAIL items above{RESET}")
    print(f"  {'─'*60}\n")

    # ── Honest diagnostic if A1 failed (score never reached 70) ──────────────
    if A["max_score"] < 70.0:
        print(f"\n{Y}{B}DIAGNOSTIC: Deepfake audio did NOT cross score 70.{RESET}")
        print(f"  Highest score reached: {A['max_score']:.1f}")
        print(f"  Why: process_chunk() uses a weighted blend:")
        print(f"       chunk_final = (a_score*0.25) + (n_score*0.45) + (d_score*0.30)")
        print(f"       Only deepfake_locked (d_score>70) forces chunk_final ≥ 85.")
        print(f"  The pure-sine WAV may not have crossed all spectral thresholds.")
        print(f"  Layer breakdown per chunk is shown in reasons[] in each result.")
        print(f"\n  Reason chains from last chunk:")
        if A["results"]:
            for r in A["results"][-1].get("reasons", []):
                print(f"    • {r}")
        print(f"\n  Action needed: supply a real deepfake TTS audio file, e.g.:")
        print(f"    python verify_timing_system.py path/to/deepfake.wav\n")


if __name__ == "__main__":
    main()

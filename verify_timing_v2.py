#!/usr/bin/env python3
"""
verify_timing_v2.py
═══════════════════════════════════════════════════════════════════════════
Second-pass verification using a "spectral comb" signal that reliably
triggers ALL five deepfake_detection markers (d_score → 80 → deepfake_locked
→ chunk_final capped at 85 → current_score 85 → HIGH_RISK_THRESHOLD 70 crossed).

WHY the pure-sine failed:
  The pure 440 Hz tone hit only 3/5 markers (ZCR, F0-jitter, centroid-std)
  producing d_score = 55.  Without deepfake_locked the blend
    chunk_final = 0*0.25 + 0*0.45 + 55*0.30 = 16.5
  never reached HIGH_RISK_THRESHOLD (70).

  Missing markers on pure sine:
    flatness  = ~0.0001  (below 0.35 threshold) – pure tone, almost no flatness
    mfcc_var  = ~70+     (above 3 threshold)    – wide MFCC spread across 13 coefs

  Comb signal fix:
    • Many equal-energy harmonics (200, 400, ..., 4000 Hz) → flatness > 0.35 → +25
    • Harmonics stable over time → mfcc_var < 3 → +20
    • Single base F0 stable → jitter < 0.5 Hz → +20
    • Consistent ZCR → zcr_std < 0.005 → +20
    • Centroid constant → centroid_std < 80 Hz → +15
    Total d_score = 100 → capped at 80 → deepfake_locked → chunk_final = 85

Run:
    cd "Fraud-Shield-AI-main (2)\\Fraud-Shield-AI-main"
    python verify_timing_v2.py
"""

import sys, os, io, wave, math, struct, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from core.live_call import process_chunk, end_call, get_detection_stats, HIGH_RISK_THRESHOLD

NUM_CHUNKS     = 5
CHUNK_INTERVAL = 2   # seconds between chunks

# ─────────────────────────────────────────────────────────────────────────────
# Comb signal: N harmonics at f0*k  (k=1..N) with equal amplitude
# Designed to trigger ALL 5 deepfake markers
# ─────────────────────────────────────────────────────────────────────────────
def make_comb_wav(dur=5.0, sr=16000, f0=200.0, n_harmonics=20) -> bytes:
    """
    Spectral comb: sum of N equal-amplitude cosines at f0, 2*f0, ..., N*f0.

    Properties vs deepfake_detection thresholds:
      flatness > 0.35   : YES  (energy spread uniformly across N frequency bins)
      zcr_std  < 0.005  : YES  (the comb pattern repeats identically each period)
      mfcc_var < 3      : YES  (stable spectral envelope = stable MFCCs over time)
      f0_jitter < 0.5 Hz: YES  (mathematically exact F0 = 0 jitter)
      centroid_std < 80 : YES  (weighted centroid of fixed harmonic series is constant)
    => d_score = 25+20+20+20+15 = 100 → capped at 80 → deepfake_locked → chunk=85
    """
    n = int(dur * sr)
    amp = 1.0 / n_harmonics          # equal amplitude per harmonic, sum ≤ 1.0
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            t = i / sr
            sample = sum(amp * math.cos(2 * math.pi * (k * f0) * t)
                         for k in range(1, n_harmonics + 1))
            frames += struct.pack("<h", max(-32767, min(32767, int(32767 * sample))))
        wf.writeframes(bytes(frames))
    return buf.getvalue()


def make_safe_wav(dur=5.0, sr=16000) -> bytes:
    """Chirp + noise: natural variation, avoids all deepfake markers."""
    import random; rng = random.Random(42)
    n = int(dur * sr)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            t = i / sr
            f = 80 + 2720 * t / dur
            sig = (0.5 * math.sin(2 * math.pi * f * t)
                 + 0.25 * math.sin(2 * math.pi * f * 2.0 * t + 0.5)
                 + 0.15 * math.sin(2 * math.pi * f * 3.1 * t + 1.2)
                 + 0.10 * (rng.random() * 2 - 1))
            frames += struct.pack("<h", max(-32767, min(32767, int(16000 * sig))))
        wf.writeframes(bytes(frames))
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Pre-warm librosa / Whisper so elapsed_seconds is accurate
# (in production these are loaded at startup; here we load them once before
#  any call is created so the model-load time is not counted as call elapsed)
# ─────────────────────────────────────────────────────────────────────────────
def prewarm(wav_bytes: bytes):
    print("[PRE-WARM] Loading librosa + Whisper tiny model...")
    t0 = time.time()
    try:
        from detectors.voice_detector import deepfake_detection, acoustic_analysis
        deepfake_detection(wav_bytes, "prewarm.wav")
        acoustic_analysis(wav_bytes, "prewarm.wav")
    except Exception:
        pass
    try:
        from core.live_call import transcribe_fast
        transcribe_fast(wav_bytes, "prewarm.wav")
    except Exception:
        pass
    print(f"[PRE-WARM] Done in {time.time()-t0:.1f}s — models cached\n")


# ─────────────────────────────────────────────────────────────────────────────
# Run a simulated call
# ─────────────────────────────────────────────────────────────────────────────
def run_call(call_id: str, wav: bytes, label: str) -> dict:
    print(f"\n{'='*65}")
    print(f"TEST {label}")
    print(f"{'='*65}")
    print(f"  call_id : {call_id}")
    print(f"  audio   : {len(wav):,} bytes per chunk")
    print()
    print(f"  {'Chunk':<6} {'Elapsed(s)':>11}  {'Score':>7}  {'Verdict':<12}  {'HighRisk?':<13} {'TimeToAlert'}")
    print(f"  {'-----':<6} {'-'*11}  {'-'*7}  {'-'*12}  {'-'*13} {'-'*11}")

    results = []
    trigger_count = 0
    trigger_chunks = []
    max_score = 0.0
    all_elapsed = []

    for i in range(1, NUM_CHUNKS + 1):
        r = process_chunk(call_id, wav, vector_db=None)
        e   = r.get("elapsed_seconds", 0)
        s   = r.get("current_score", 0.0)
        v   = r.get("verdict", "?")
        trig = r.get("high_risk_triggered", False)
        tta  = r.get("time_to_alert_seconds")

        results.append(r)
        all_elapsed.append(e)
        max_score = max(max_score, s)
        if trig:
            trigger_count += 1
            trigger_chunks.append(i)

        trig_str = "YES <-- FIRST CROSSING!" if trig else "no"
        tta_str  = f"{tta:.2f}s" if tta is not None else "None"
        print(f"  {i:<6} {e:>11.2f}  {s:>7.1f}  {v:<12}  {trig_str:<28} {tta_str}")

        if i < NUM_CHUNKS:
            time.sleep(CHUNK_INTERVAL)

    state = end_call(call_id)
    tta_state = state.time_to_first_alert if state else None
    trigger_tta = next((r.get("time_to_alert_seconds") for r in results if r.get("high_risk_triggered")), None)

    return dict(
        results=results,
        trigger_count=trigger_count,
        trigger_chunks=trigger_chunks,
        max_score=max_score,
        e0=all_elapsed[0], en=all_elapsed[-1],
        elapsed_grew=(all_elapsed[-1] - all_elapsed[0]) >= (CHUNK_INTERVAL * (NUM_CHUNKS - 1) * 0.8),
        tta_state=tta_state,
        trigger_tta=trigger_tta,
    )


def verdict(ok: bool, label: str, detail: str = "") -> bool:
    mark = "[PASS]" if ok else "[FAIL]"
    line = f"  {mark}  {label}"
    if detail: line += f"  | {detail}"
    print(line)
    return ok


# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "="*65)
    print("  Fraud Shield AI -- Timing System Verification v2")
    print(f"  HIGH_RISK_THRESHOLD = {HIGH_RISK_THRESHOLD}")
    print("="*65)

    comb_wav = make_comb_wav()
    safe_wav = make_safe_wav()
    print(f"\n  comb_wav : {len(comb_wav):,} bytes (20-harmonic comb, 200..4000 Hz)")
    print(f"  safe_wav : {len(safe_wav):,} bytes (chirp+noise)")

    # Pre-warm so model load time is NOT charged to the call
    prewarm(comb_wav)

    # Run calls
    A = run_call("verify2-comb-001", comb_wav, "A -- DEEPFAKE-LIKE (spectral comb)")
    B = run_call("verify2-safe-001", safe_wav, "B -- SAFE / CLEAN  (chirp+noise)")

    stats = get_detection_stats()

    print(f"\n{'='*65}")
    print("DETECTION STATS  (raw JSON)")
    print(f"{'='*65}")
    print(stats)

    print(f"\n{'='*65}")
    print("PASS / FAIL VERDICTS")
    print(f"{'='*65}")

    all_ok = True

    print("\n  -- Test A (deepfake/comb audio) --")
    all_ok &= verdict(A["max_score"] >= 70, "A1  current_score crossed 70",
                      f"highest = {A['max_score']:.1f}")
    all_ok &= verdict(A["trigger_count"] >= 1, "A2  high_risk_triggered fired",
                      f"fired {A['trigger_count']}x on chunk(s) {A['trigger_chunks']}")
    all_ok &= verdict(A["trigger_count"] == 1, "A3  fired EXACTLY once (no re-fire)",
                      f"chunks: {A['trigger_chunks']}")
    all_ok &= verdict(A["tta_state"] is not None and A["tta_state"] <= 10.0,
                      "A4  time_to_alert_seconds <= 10s",
                      f"tta = {A['tta_state']}")
    all_ok &= verdict(
        A["trigger_tta"] is not None and A["tta_state"] is not None
        and abs(A["trigger_tta"] - A["tta_state"]) < 0.05,
        "A4b result-dict tta matches state.time_to_first_alert",
        f"result={A['trigger_tta']}, state={A['tta_state']}")
    all_ok &= verdict(A["elapsed_grew"], "A5  elapsed_seconds grew correctly",
                      f"chunk1={A['e0']:.2f}s -> chunk{NUM_CHUNKS}={A['en']:.2f}s")

    print("\n  -- Test B (safe audio) --")
    all_ok &= verdict(B["trigger_count"] == 0, "B1  high_risk_triggered never fired",
                      f"fired {B['trigger_count']}x, max_score = {B['max_score']:.1f}")
    all_ok &= verdict(B["tta_state"] is None, "B2  time_to_alert_seconds stayed None",
                      f"tta_final = {B['tta_state']}")
    all_ok &= verdict(B["elapsed_grew"], "B3  elapsed_seconds grew in safe call",
                      f"chunk1={B['e0']:.2f}s -> chunk{NUM_CHUNKS}={B['en']:.2f}s")

    print("\n  -- Detection Stats --")
    all_ok &= verdict(stats["total_calls"] >= 2, "C1  total_calls >= 2",
                      str(stats["total_calls"]))
    all_ok &= verdict(stats["total_flagged"] >= 1, "C2  total_flagged >= 1",
                      str(stats["total_flagged"]))
    all_ok &= verdict(stats["avg_time_to_alert"] is not None,
                      "C3  avg_time_to_alert is a real number",
                      str(stats["avg_time_to_alert"]))
    all_ok &= verdict(stats["calls_flagged_under_10s"] >= 1,
                      "C4  calls_flagged_under_10s >= 1",
                      str(stats["calls_flagged_under_10s"]))

    print(f"\n  {'─'*60}")
    if all_ok:
        print("  >>> ALL CHECKS PASSED <<<")
    else:
        print("  >>> SOME CHECKS FAILED -- see FAIL items above <<<")
    print(f"  {'─'*60}")

    # Show reason chains for transparency
    print(f"\n{'='*65}")
    print("REASON CHAINS -- call A, last chunk")
    print(f"{'='*65}")
    for r in A["results"][-1].get("reasons", []):
        print(f"  * {r}")

    print(f"\n{'='*65}")
    print("REASON CHAINS -- call B, last chunk")
    print(f"{'='*65}")
    for r in B["results"][-1].get("reasons", []):
        print(f"  * {r}")


if __name__ == "__main__":
    main()

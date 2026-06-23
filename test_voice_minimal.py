"""
MINIMAL Voice Threat Scorer — uses ONLY stdlib wave + numpy
No librosa, no whisper, no heavy deps.
Should run in < 3 seconds.
"""
import sys
import os
import wave
import struct

print("=" * 60)
print("  FRAUD SHIELD AI — Voice Threat Score (Minimal Test)")
print("=" * 60)

# ── Find WAV ──────────────────────────────────────────────────
WAV_FILES = [
    r"Fraud_Detection_shield\temp.wav",
    r"test_voice\4cd7-c6a1-4064-b842-cc10c89c4e1e.wav",
]
base = os.path.dirname(os.path.abspath(__file__))
wav_path = None
for f in WAV_FILES:
    p = os.path.join(base, f)
    if os.path.exists(p):
        wav_path = p
        break

if not wav_path:
    print("\n❌  No WAV file found!")
    sys.exit(1)

print(f"\n  File   : {os.path.basename(wav_path)}")
print(f"  Size   : {os.path.getsize(wav_path):,} bytes")

# ── Load WAV with stdlib ──────────────────────────────────────
try:
    with wave.open(wav_path, 'rb') as wf:
        n_channels   = wf.getnchannels()
        sampwidth    = wf.getsampwidth()
        framerate    = wf.getframerate()
        n_frames     = wf.getnframes()
        raw_data     = wf.readframes(n_frames)

    print(f"  Channels: {n_channels}  |  Sample rate: {framerate} Hz  |  Duration: {n_frames/framerate:.1f}s")
except Exception as e:
    print(f"\n❌  Failed to open WAV: {e}")
    sys.exit(1)

# ── Convert to float samples ──────────────────────────────────
try:
    import numpy as np
    if sampwidth == 2:
        samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 1:
        samples = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
    else:
        samples = np.frombuffer(raw_data, dtype=np.int32).astype(np.float32) / 2147483648.0

    # Only use first channel if stereo
    if n_channels == 2:
        samples = samples[::2]
    HAS_NUMPY = True
except ImportError:
    # Pure Python fallback
    HAS_NUMPY = False
    count = len(raw_data) // 2
    samples_raw = struct.unpack(f"{count}h", raw_data[:count*2])
    samples = [s / 32768.0 for s in samples_raw]

print(f"  Samples : {len(samples):,}")

# ── Compute metrics ───────────────────────────────────────────
print("\n  Analyzing...")

if HAS_NUMPY:
    import numpy as np
    arr = np.array(samples)

    # RMS energy
    rms = float(np.sqrt(np.mean(arr**2)))

    # Silence ratio (samples < 2% amplitude)
    silence_ratio = float(np.sum(np.abs(arr) < 0.02) / len(arr))

    # Zero crossing rate (manual)
    signs = np.sign(arr)
    crossings = np.sum(np.diff(signs) != 0)
    zcr = float(crossings) / len(arr)

    # Peak amplitude
    peak = float(np.max(np.abs(arr)))

    # Energy variance (scripted calls are unnaturally uniform)
    chunk = max(1, len(arr) // 100)
    chunks = [arr[i:i+chunk] for i in range(0, len(arr)-chunk, chunk)]
    rms_per_chunk = [float(np.sqrt(np.mean(c**2))) for c in chunks if len(c) > 0]
    energy_variance = float(np.std(rms_per_chunk))

else:
    # Pure Python fallback
    n = len(samples)
    rms = (sum(s**2 for s in samples) / n) ** 0.5
    silence_ratio = sum(1 for s in samples if abs(s) < 0.02) / n
    crossings = sum(1 for i in range(1, n) if (samples[i] >= 0) != (samples[i-1] >= 0))
    zcr = crossings / n
    peak = max(abs(s) for s in samples)
    energy_variance = 0.05  # fallback

# ── Score calculation ─────────────────────────────────────────
score = 0
reasons = []

# Check 1: Silence ratio
if silence_ratio < 0.05:
    score += 15
    reasons.append(f"Very low pauses ({silence_ratio:.1%}) — possible scripted robocall")
elif silence_ratio > 0.70:
    score += 8
    reasons.append(f"Excessive silence ({silence_ratio:.1%}) — possible recorded message")

# Check 2: RMS energy (pressure/shouting)
if rms > 0.15:
    score += 10
    reasons.append(f"High energy (RMS={rms:.3f}) — pressure tactics or shouting detected")

# Check 3: Zero-crossing rate (deepfake signal)
if zcr < 0.01:
    score += 25
    reasons.append(f"Very low ZCR ({zcr:.4f}) — AI/TTS voice lacks natural micro-fluctuations")
elif zcr > 0.25:
    score += 10
    reasons.append(f"Abnormally high ZCR ({zcr:.4f}) — noisy/distorted audio")

# Check 4: Peak amplitude (clipping from compressed/phone audio)
if peak > 0.98:
    score += 10
    reasons.append(f"Audio clipping detected (peak={peak:.3f}) — heavily processed audio")

# Check 5: Energy variance (uniform = scripted/TTS)
if energy_variance < 0.02:
    score += 20
    reasons.append(f"Very uniform energy ({energy_variance:.4f}) — unnaturally steady voice (TTS/scripted)")
elif energy_variance > 0.2:
    score += 5
    reasons.append(f"High energy variance — possibly emotional/high-stress call")

# Cap
score = min(score, 100)

# ── Risk verdict ──────────────────────────────────────────────
if score >= 60:
    risk = "HIGH"; verdict = "🔴  LIKELY SCAM or DEEPFAKE!"
elif score >= 35:
    risk = "MEDIUM"; verdict = "🟡  SUSPICIOUS — Review carefully"
elif score >= 15:
    risk = "LOW"; verdict = "🟢  Minor indicators — probably safe"
else:
    risk = "CLEAR"; verdict = "🟢  Clean audio — no fraud signals"

# ── Print results ─────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"  🎯  THREAT SCORE : {score} / 100")
print(f"  🚨  RISK LEVEL   : {risk}")
print(f"  📋  VERDICT      : {verdict}")

print("\n  📊 RAW METRICS:")
print(f"      RMS Energy     : {rms:.4f}")
print(f"      Silence Ratio  : {silence_ratio:.2%}")
print(f"      Zero-Cross Rate: {zcr:.4f}")
print(f"      Peak Amplitude : {peak:.4f}")
print(f"      Energy Variance: {energy_variance:.4f}")

print("\n  ⚠️  FLAGS:")
if reasons:
    for r in reasons:
        print(f"      • {r}")
else:
    print("      • None — audio appears clean")

print("=" * 60)

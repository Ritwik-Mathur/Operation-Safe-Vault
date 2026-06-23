"""
FAST Voice Threat Scorer — NO Whisper required
Uses librosa for acoustic analysis only.
Runs in ~5 seconds.
"""
import sys
import os

WAV_FILES = [
    r"Fraud_Detection_shield\temp.wav",
    r"test_voice\4cd7-c6a1-4064-b842-cc10c89c4e1e.wav",
]

print("=" * 60)
print("  FRAUD SHIELD AI — Voice Acoustic Analysis")
print("  (Fast mode: no Whisper / no STT)")
print("=" * 60)

# ── Find WAV ──────────────────────────────────────────────────
wav_path = None
for f in WAV_FILES:
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), f)
    if os.path.exists(p):
        wav_path = p
        print(f"\n  Audio file : {f}")
        print(f"  Size       : {os.path.getsize(p):,} bytes")
        break

if not wav_path:
    print("\n❌  No WAV file found!")
    print("    Put a test WAV at: Fraud_Detection_shield/temp.wav")
    sys.exit(1)

# ── Load audio with librosa ───────────────────────────────────
print("\n  Loading audio...")
try:
    import librosa
    import numpy as np
    audio, sr = librosa.load(wav_path, sr=None)
    duration = len(audio) / sr
    print(f"  Sample rate: {sr} Hz")
    print(f"  Duration   : {duration:.2f}s")
except ImportError:
    print("\n❌  librosa not installed!")
    print("    Run:  pip install librosa")
    sys.exit(1)

# ── Acoustic Analysis ─────────────────────────────────────────
print("\n  Analyzing acoustic features...")

score = 0
reasons = []
indicators = {}

# 1) Silence ratio (robocall detection)
silence_mask = np.abs(audio) < 0.01
silence_ratio = np.sum(silence_mask) / len(audio)
indicators["Silence ratio"] = f"{silence_ratio:.2%}"
if silence_ratio < 0.05:
    score += 15
    reasons.append("Very low pauses — possible robocall/scripted call")
elif silence_ratio > 0.6:
    score += 5
    reasons.append("Excessive silence — possible dead air / recorded message")

# 2) RMS energy (shouting/pressure detection)
rms = float(np.sqrt(np.mean(audio**2)))
indicators["RMS Energy"] = f"{rms:.4f}"
if rms > 0.1:
    score += 10
    reasons.append("High energy — possible pressure tactics/shouting")

# 3) Pitch variance via zero-crossing rate (deepfake signal)
zcr = float(np.mean(librosa.feature.zero_crossing_rate(audio)))
indicators["Zero-Crossing Rate"] = f"{zcr:.4f}"
if zcr < 0.02:
    score += 20
    reasons.append("Low ZCR — possible AI/synthetic voice (no natural breath disruption)")
elif zcr > 0.2:
    score += 10
    reasons.append("Extremely high ZCR — noisy or compressed audio")

# 4) Spectral flatness (deepfake — AI voices are unnaturally flat)
spec_flat = float(np.mean(librosa.feature.spectral_flatness(y=audio)))
indicators["Spectral Flatness"] = f"{spec_flat:.6f}"
if spec_flat > 0.3:
    score += 25
    reasons.append("High spectral flatness — AI-generated / TTS voice detected")
elif spec_flat < 0.001:
    score += 10
    reasons.append("Near-zero spectral flatness — suspicious pure-tone audio")

# 5) MFCC variance (deepfake signal — AI has low variance)
mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
mfcc_var = float(np.mean(np.var(mfccs, axis=1)))
indicators["MFCC Variance"] = f"{mfcc_var:.2f}"
if mfcc_var < 10.0:
    score += 20
    reasons.append("Low MFCC variance — voice lacks natural human articulation variation")

# 6) Speaking rate via beat tempo
tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
indicators["Tempo (BPM)"] = f"{float(tempo):.1f}"
if float(tempo) > 150:
    score += 15
    reasons.append("Very fast speaking rate (>150 BPM) — scripted scam reading detected")

# Cap at 100
score = min(score, 100)

# ── Risk classification ───────────────────────────────────────
if score >= 70:
    risk = "HIGH"
    verdict = "🔴 LIKELY SCAM / DEEPFAKE"
elif score >= 40:
    risk = "MEDIUM"
    verdict = "🟡 SUSPICIOUS — Review carefully"
elif score >= 20:
    risk = "LOW"
    verdict = "🟢 Probably safe"
else:
    risk = "MINIMAL"
    verdict = "🟢 Clean audio — no fraud signals"

# ── Print results ─────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"  🎯  THREAT SCORE : {score} / 100")
print(f"  🚨  RISK LEVEL   : {risk}")
print(f"  📋  VERDICT      : {verdict}")

print("\n  📊 ACOUSTIC INDICATORS:")
for k, v in indicators.items():
    print(f"      {k:<25} → {v}")

print("\n  ⚠️  REASONS FLAGGED:")
if reasons:
    for r in reasons:
        print(f"      • {r}")
else:
    print("      • None — audio appears clean")

print("=" * 60)
print("\n  NOTE: Add Whisper STT for full semantic analysis.")
print("        Run: pip install openai-whisper")
print("        Then use the full voice_module/detector.py")
print("=" * 60)

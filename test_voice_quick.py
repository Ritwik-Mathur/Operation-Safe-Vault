"""
Quick standalone test for the voice module.
Tests directly without FastAPI — just runs analyze_voice on the test WAV file.
"""
import sys
import os

# Add Fraud_Detection_shield to path so voice_module imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Fraud_Detection_shield"))

print("=" * 60)
print("FRAUD SHIELD AI — Voice Module Test")
print("=" * 60)

# ── Step 1: Check deps ────────────────────────────────────────
print("\n[1/4] Checking dependencies...")
missing = []
try:
    import whisper
    print("  ✅ whisper OK")
except ImportError:
    print("  ❌ whisper MISSING  →  pip install openai-whisper")
    missing.append("openai-whisper")

try:
    import librosa
    print("  ✅ librosa OK")
except ImportError:
    print("  ❌ librosa MISSING  →  pip install librosa")
    missing.append("librosa")

try:
    import numpy
    print("  ✅ numpy OK")
except ImportError:
    print("  ❌ numpy MISSING  →  pip install numpy")
    missing.append("numpy")

if missing:
    print(f"\n⚠️  Install missing packages first:")
    print(f"    pip install {' '.join(missing)}")
    sys.exit(1)

# ── Step 2: Find WAV file ─────────────────────────────────────
print("\n[2/4] Looking for test audio file...")
candidates = [
    r"Fraud_Detection_shield\temp.wav",
    r"test_voice\4cd7-c6a1-4064-b842-cc10c89c4e1e.wav",
]
wav_path = None
for c in candidates:
    full = os.path.join(os.path.dirname(__file__), c)
    if os.path.exists(full):
        wav_path = full
        print(f"  ✅ Found: {c}")
        break

if not wav_path:
    print("  ❌ No .wav file found. Add a test WAV to Fraud_Detection_shield/temp.wav")
    sys.exit(1)

# ── Step 3: Run analysis ──────────────────────────────────────
print("\n[3/4] Running voice analysis (Whisper loading — may take 30s)...")
from voice_module.detector import analyze_voice

result = analyze_voice(wav_path)

# ── Step 4: Show results ──────────────────────────────────────
print("\n[4/4] RESULTS:")
print("=" * 60)
print(f"  🎯 THREAT SCORE : {result['score']} / 100")
print(f"  🚨 RISK LEVEL   : {result['risk']}")
print(f"\n  📝 TRANSCRIPT:")
print(f"     {result['text'] if result['text'].strip() else '[No speech detected]'}")
print(f"\n  ⚠️  REASONS:")
if result["reason"]:
    for r in result["reason"]:
        print(f"     • {r}")
else:
    print("     • No fraud indicators detected")
print("=" * 60)

if result["score"] > 60:
    print("  🔴 VERDICT: HIGH RISK — Likely scam call!")
elif result["score"] > 30:
    print("  🟡 VERDICT: MEDIUM RISK — Suspicious, review carefully")
else:
    print("  🟢 VERDICT: LOW RISK — Appears safe")
print("=" * 60)

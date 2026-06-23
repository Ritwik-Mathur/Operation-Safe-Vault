"""
test_spectrogram_endpoint.py
────────────────────────────
End-to-end test of the spectrogram generator with the real temp.wav file.
Prints the full data URI so you can paste it into a browser to see the image.

Usage:
    cd "Fraud-Shield-AI-main (2)\\Fraud-Shield-AI-main"
    python test_spectrogram_endpoint.py
"""
import sys, time, os, base64
sys.path.insert(0, 'backend')

WAV_PATH = os.path.join("Fraud_Detection_shield", "temp.wav")

# ── Warmup (mirrors server startup) ──────────────────────────────────────────
print("=" * 60)
print("Warming up – simulates server startup import")
print("=" * 60)
t0 = time.time()
from core.spectrogram_generator import generate_spectrogram_image
print(f"  Startup import : {time.time()-t0:.2f}s")

# ── Real-file test ────────────────────────────────────────────────────────────
print()
print("=" * 60)
print(f"Testing with real WAV: {WAV_PATH}")
print("=" * 60)

if not os.path.exists(WAV_PATH):
    print(f"  [SKIP] File not found: {WAV_PATH}")
    print("  Using synthetic 440 Hz sine instead...")
    import io, wave, math, struct
    def sine_wav(dur=5.0, sr=16000):
        n = int(dur * sr)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            frames = bytearray()
            for i in range(n):
                frames += struct.pack('<h', int(32767 * math.sin(2 * math.pi * 440 * i / sr)))
            wf.writeframes(bytes(frames))
        return buf.getvalue()
    audio_bytes = sine_wav()
    fname = "synthetic.wav"
else:
    with open(WAV_PATH, 'rb') as f:
        audio_bytes = f.read()
    fname = "temp.wav"

print(f"  File size : {len(audio_bytes):,} bytes")

# Warm call
t0 = time.time()
result = generate_spectrogram_image(audio_bytes, fname)
elapsed = time.time() - t0

if result and result.startswith("data:image/png;base64,"):
    raw_b64  = result[len("data:image/png;base64,"):]
    png_data = base64.b64decode(raw_b64)
    png_magic = png_data[:8]
    is_valid  = png_magic[:4] == b"\x89PNG"

    print(f"  [PASS] generate_spectrogram_image() returned a valid data URI")
    print(f"  Elapsed     : {elapsed:.3f}s  (target < 1s)")
    print(f"  URI length  : {len(result):,} chars")
    print(f"  PNG bytes   : {len(png_data):,}")
    print(f"  PNG magic   : {png_magic[:4].hex()}  (89504e47 = valid PNG)")
    print(f"  Valid PNG   : {is_valid}")
else:
    print(f"  [FAIL] result={repr(result)[:200]}")
    sys.exit(1)

# ── Second call timing ────────────────────────────────────────────────────────
print()
print("=" * 60)
print("Second call (fully warm)")
print("=" * 60)
t0 = time.time()
generate_spectrogram_image(audio_bytes, fname)
elapsed2 = time.time() - t0
print(f"  Elapsed : {elapsed2:.3f}s")
if elapsed2 < 1.0:
    print("  [PASS] Under 1 second")
else:
    print("  [WARN] Still over 1s on warm call")

# ── Print full data URI ───────────────────────────────────────────────────────
print()
print("=" * 60)
print("FULL DATA URI  (paste into browser address bar to see image)")
print("=" * 60)
print()
print(result)
print()

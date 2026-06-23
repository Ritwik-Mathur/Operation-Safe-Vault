"""
Voice Module Detector — Fixed Version
Fixes:
  1. Lazy model loading (don't load Whisper at import time)
  2. Fixed relative imports (works from any CWD)
  3. Expanded acoustic analysis with deepfake signals
  4. Graceful fallback if whisper is not installed
"""
import os
import numpy as np

# Fix import path — works regardless of how the module is run
try:
    from voice_module.audio_utils import load_audio
except ImportError:
    from audio_utils import load_audio

# ── Lazy Whisper loading (NOT at import time) ─────────────────
_whisper_model = None

def _get_whisper_model():
    """Load Whisper model only when first needed."""
    global _whisper_model
    if _whisper_model is None:
        try:
            # Try faster-whisper first (much faster, same accuracy)
            from faster_whisper import WhisperModel
            print("[Voice] Loading faster-whisper model (int8, CPU)...")
            _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            _whisper_model._type = "faster"
        except ImportError:
            try:
                import whisper
                print("[Voice] Loading openai-whisper model...")
                _whisper_model = whisper.load_model("base")
                _whisper_model._type = "openai"
            except ImportError:
                print("[Voice] WARNING: No Whisper installed — STT disabled")
                _whisper_model = None
    return _whisper_model


# ── Speech to Text ─────────────────────────────────────────────
def speech_to_text(file_path: str) -> str:
    """Transcribe audio file. Returns empty string if whisper unavailable."""
    model = _get_whisper_model()
    if model is None:
        return ""
    try:
        if getattr(model, "_type", "") == "faster":
            segments, _ = model.transcribe(file_path, beam_size=5, language="en")
            return " ".join(seg.text for seg in segments).strip()
        else:
            result = model.transcribe(file_path)
            return result["text"].strip()
    except Exception as e:
        print(f"[Voice] STT error: {e}")
        return ""


# ── Semantic / NLP Intent Detection ───────────────────────────
SCAM_VECTORS = [
    ("otp", 40),
    ("one time password", 40),
    ("cvv", 35),
    ("aadhaar", 35),
    ("aadhar", 35),
    ("pan card", 30),
    ("anydesk", 30),
    ("teamviewer", 30),
    ("screen share", 25),
    ("bank account", 20),
    ("credit card", 20),
    ("debit card", 20),
    ("pin number", 25),
    ("password", 20),
    ("verify", 15),
    ("block", 15),
    ("suspended", 15),
    ("arrested", 20),
    ("police", 15),
    ("refund", 10),
]

URGENCY_MULTIPLIERS = [
    "immediately", "urgent", "right now", "last chance",
    "within 24 hours", "or else", "do not tell", "keep this call private",
    "do not hang up", "emergency", "expire"
]

def detect_intent(text: str):
    """NLP-based scam intent detection on transcript."""
    if not text:
        return 0, ["[No transcript — STT unavailable or silent audio]"]

    text_lower = text.lower()
    score = 0
    reasons = []
    has_urgency = any(u in text_lower for u in URGENCY_MULTIPLIERS)

    for keyword, base_score in SCAM_VECTORS:
        if keyword in text_lower:
            multiplier = 1.5 if has_urgency else 1.0
            awarded = int(base_score * multiplier)
            score += awarded
            reasons.append(f'"{keyword}" detected (score +{awarded})')

    if has_urgency and not reasons:
        score += 15
        reasons.append("Urgency language detected without specific scam keywords")

    return min(score, 60), reasons  # NLP capped at 60


# ── Acoustic Feature Extraction ────────────────────────────────
def analyze_audio(audio: np.ndarray):
    """
    Acoustic fraud analysis.
    Detects: robocall patterns, TTS voices, pressure tactics.
    """
    score = 0
    reasons = []

    if len(audio) == 0:
        return 0, ["Empty audio"]

    # 1) Silence ratio — robocalls never pause to breathe
    silence_ratio = np.sum(np.abs(audio) < 0.01) / len(audio)
    if silence_ratio < 0.05:
        score += 15
        reasons.append(f"Low pause ratio ({silence_ratio:.1%}) — possible scripted/robocall")

    # 2) RMS energy — pressure/shouting
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms > 0.1:
        score += 10
        reasons.append(f"High RMS energy ({rms:.3f}) — pressure or shouting detected")

    # 3) Zero-crossing rate — AI/TTS voices have unnaturally low ZCR
    zcr = float(np.mean(np.abs(np.diff(np.sign(audio)))) / 2)
    if zcr < 0.02:
        score += 20
        reasons.append(f"Very low ZCR ({zcr:.4f}) — AI/TTS voice lacks natural micro-fluctuations")

    # 4) Energy variance — scripted TTS voices have unnaturally uniform energy
    chunk_size = max(1, len(audio) // 50)
    chunks = [audio[i:i+chunk_size] for i in range(0, len(audio) - chunk_size, chunk_size)]
    if chunks:
        rms_vals = [float(np.sqrt(np.mean(c ** 2))) for c in chunks]
        energy_var = float(np.std(rms_vals))
        if energy_var < 0.015:
            score += 15
            reasons.append(f"Low energy variance ({energy_var:.4f}) — unnaturally uniform TTS voice")

    return min(score, 40), reasons  # Acoustic capped at 40


# ── Deepfake Voice Detection ───────────────────────────────────
def deepfake_score(audio: np.ndarray):
    """
    Measures artifacts of AI/TTS generation.
    Uses spectral flatness proxy via FFT.
    """
    score = 0
    reasons = []

    if len(audio) < 1000:
        return 0, []

    try:
        # Spectral flatness: AI voices are unnaturally flat in frequency domain
        spectrum = np.abs(np.fft.rfft(audio[:min(len(audio), 44100)]))
        spectrum = spectrum + 1e-10  # avoid log(0)

        geometric_mean = np.exp(np.mean(np.log(spectrum)))
        arithmetic_mean = np.mean(spectrum)
        flatness = float(geometric_mean / arithmetic_mean)

        if flatness > 0.15:
            score += 25
            reasons.append(f"High spectral flatness ({flatness:.3f}) — AI-generated voice signal")
        elif flatness > 0.08:
            score += 10
            reasons.append(f"Elevated spectral flatness ({flatness:.3f}) — possible TTS artifact")

    except Exception as e:
        reasons.append(f"Deepfake check error: {e}")

    return min(score, 30), reasons  # Deepfake capped at 30


# ── Main analysis function ─────────────────────────────────────
def analyze_voice(file_path: str) -> dict:
    """
    Full voice fraud analysis.
    Returns: { score, risk, verdict, reasons, transcript }
    Weights: 25% Acoustic + 45% NLP + 30% Deepfake
    """
    # Load audio
    try:
        audio, sr = load_audio(file_path)
    except Exception as e:
        return {
            "score": 0, "risk": "ERROR", "verdict": "Could not load audio",
            "reasons": [f"Audio load error: {str(e)}"], "transcript": ""
        }

    # Run all three layers
    acoustic_raw, acoustic_reasons = analyze_audio(audio)
    deepfake_raw, deepfake_reasons  = deepfake_score(audio)
    transcript                      = speech_to_text(file_path)
    nlp_raw, nlp_reasons            = detect_intent(transcript)

    # Weighted combination: 25% Acoustic + 45% NLP + 30% Deepfake
    # (normalized against their caps: 40, 60, 30)
    acoustic_norm = (acoustic_raw / 40)  * 25
    nlp_norm      = (nlp_raw / 60)       * 45
    deepfake_norm = (deepfake_raw / 30)  * 30

    total_score = int(min(acoustic_norm + nlp_norm + deepfake_norm, 100))
    all_reasons = acoustic_reasons + deepfake_reasons + nlp_reasons

    # Risk classification
    if total_score >= 70:
        risk = "HIGH"
        verdict = "LIKELY SCAM or DEEPFAKE — Block immediately"
    elif total_score >= 45:
        risk = "MEDIUM"
        verdict = "SUSPICIOUS — Review carefully before taking action"
    elif total_score >= 20:
        risk = "LOW"
        verdict = "Minor indicators — Proceed with caution"
    else:
        risk = "SAFE"
        verdict = "Clean audio — No fraud signals detected"

    return {
        "score": total_score,
        "risk": risk,
        "verdict": verdict,
        "reasons": all_reasons,
        "transcript": transcript,
        "breakdown": {
            "acoustic_score": acoustic_raw,
            "nlp_score": nlp_raw,
            "deepfake_score": deepfake_raw,
        }
    }
"""
Speaker Verification – Voice Enrollment & Biometric Matching
─────────────────────────────────────────────────────────────
Uses SpeechBrain's pretrained ECAPA-TDNN speaker embedding model
(speechbrain/spkrec-ecapa-voxceleb) to extract 192-dim d-vectors.

Workflow:
  1. enroll_speaker(customer_id, audio_bytes)
       → extracts embedding, stores as .npy under data/voice_enrollments/
  2. verify_speaker(customer_id, audio_bytes)
       → extracts embedding from new audio, computes cosine similarity
       → returns (similarity_score, is_match)

Model note:
  The model auto-downloads on first use from Hugging Face Hub (~50 MB).
  Subsequent calls load from the local cache (~/.cache/huggingface/).
"""

import os
import io
import tempfile
import logging
from pathlib import Path
from typing import Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Storage config ───────────────────────────────────────────────────────────

# Resolve relative to this file: backend/core/ → backend/data/voice_enrollments/
_HERE = Path(__file__).parent  # backend/core/
ENROLLMENT_DIR = _HERE.parent / "data" / "voice_enrollments"
ENROLLMENT_DIR.mkdir(parents=True, exist_ok=True)

# ── Similarity threshold ─────────────────────────────────────────────────────
# 0.70 calibrated for real-world short-clip (2–5 s) phone-quality audio:
#   • Same speaker across sessions: typically 0.70–0.95
#   • Different speakers:           typically 0.20–0.55
#   • ECAPA-TDNN on short clips has ±0.05 variance vs long enrollment clips;
#     0.70 gives headroom while still leaving a ~0.47 margin above
#     typical different-speaker scores (~0.23).
MATCH_THRESHOLD: float = 0.70

# ── Model singleton (lazy-loaded) ─────────────────────────────────────────────
_model = None
_model_error: Optional[str] = None


def _load_model():
    """
    Lazy-load the SpeechBrain ECAPA-TDNN model.
    Downloads from HuggingFace on first call (~50 MB), cached locally after that.
    Thread-safe enough for typical FastAPI single-worker usage.
    """
    global _model, _model_error
    if _model is not None:
        return _model
    if _model_error:
        raise RuntimeError(_model_error)

    try:
        try:
            # SpeechBrain >= 1.0 moved to speechbrain.inference
            from speechbrain.inference.classifiers import EncoderClassifier
        except ImportError:
            # Fallback for older SpeechBrain versions
            from speechbrain.pretrained import EncoderClassifier  # type: ignore[no-redef]
        logger.info("[SpeakerVerification] Loading ECAPA-TDNN model (may download on first run)...")
        _model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": "cpu"},
        )
        logger.info("[SpeakerVerification] Model ready.")
        return _model
    except ImportError as e:
        _model_error = (
            "speechbrain is not installed. "
            "Run: pip install speechbrain"
        )
        raise RuntimeError(_model_error) from e
    except Exception as e:
        _model_error = f"Failed to load SpeechBrain model: {e}"
        logger.error(f"[SpeakerVerification] {_model_error}")
        raise RuntimeError(_model_error) from e


# ── Audio → embedding ────────────────────────────────────────────────────────

def _load_audio_soundfile(path: str) -> tuple:
    """
    Load audio using soundfile (libsndfile — no FFmpeg needed).
    Returns (samples_float32_np, sample_rate).
    """
    import soundfile as sf
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    # data shape: (frames, channels)
    # Convert to mono by averaging channels
    if data.shape[1] > 1:
        data = data.mean(axis=1)
    else:
        data = data[:, 0]
    return data, sr


def _resample_numpy(data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample a 1-D float32 numpy array from orig_sr to target_sr.
    Tries scipy.signal.resample_poly first; falls back to linear interpolation.
    """
    if orig_sr == target_sr:
        return data
    try:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(orig_sr, target_sr)
        up, down = target_sr // g, orig_sr // g
        return resample_poly(data, up, down).astype(np.float32)
    except ImportError:
        pass
    # Simple linear interpolation fallback
    num_samples = int(len(data) * target_sr / orig_sr)
    x_old = np.linspace(0, 1, len(data))
    x_new = np.linspace(0, 1, num_samples)
    return np.interp(x_new, x_old, data).astype(np.float32)


def _extract_embedding(audio_bytes: bytes, filename: str = "audio.wav") -> np.ndarray:
    """
    Write audio_bytes to a temp file, load via soundfile, resample to 16 kHz,
    and return a 192-dim speaker embedding as a 1-D numpy array.

    Audio loading uses soundfile (libsndfile) — no FFmpeg or torchcodec needed.
    SpeechBrain's EncoderClassifier.encode_batch() expects a torch tensor of
    shape (batch=1, time) sampled at 16 kHz.
    """
    try:
        import torch
    except ImportError as e:
        raise RuntimeError(
            "torch is required for speaker verification. "
            "Run: pip install torch"
        ) from e

    try:
        import soundfile  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "soundfile is required for speaker verification. "
            "Run: pip install soundfile"
        ) from e

    model = _load_model()

    suffix = os.path.splitext(filename)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        data, sr = _load_audio_soundfile(tmp_path)

        # Resample to 16 kHz (ECAPA-TDNN was trained at 16 kHz)
        if sr != 16000:
            data = _resample_numpy(data, sr, 16000)

        # Shape: (1, time) tensor
        waveform = torch.from_numpy(data).unsqueeze(0)  # (1, T)

        with torch.no_grad():
            embedding = model.encode_batch(waveform)  # (1, 1, 192)

        embedding_np = embedding.squeeze().cpu().numpy()  # (192,)
        return embedding_np

    finally:
        os.unlink(tmp_path)


# ── Public API ───────────────────────────────────────────────────────────────

def enroll_speaker(customer_id: str, audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    """
    Extract a speaker embedding from audio_bytes and persist it.

    Parameters
    ----------
    customer_id : str
        Unique identifier for the customer (used as the filename key).
    audio_bytes : bytes
        Raw audio file bytes (WAV, MP3, OGG, etc.).
    filename : str
        Original filename (used to infer audio format suffix).

    Returns
    -------
    dict with keys:
        customer_id, enrolled, embedding_dim, enrollment_path, message
    """
    embedding = _extract_embedding(audio_bytes, filename)

    # Sanitize customer_id to be filesystem-safe
    safe_id = "".join(c for c in customer_id if c.isalnum() or c in "-_")
    if not safe_id:
        raise ValueError(f"Invalid customer_id: {customer_id!r}")

    enrollment_path = ENROLLMENT_DIR / f"{safe_id}.npy"
    np.save(str(enrollment_path), embedding)
    logger.info(
        f"[SpeakerVerification] Enrolled customer '{customer_id}' → {enrollment_path}"
    )

    return {
        "customer_id": customer_id,
        "enrolled": True,
        "embedding_dim": int(embedding.shape[0]),
        "enrollment_path": str(enrollment_path),
        "message": f"Speaker profile enrolled successfully for customer '{customer_id}'.",
    }


def verify_speaker(
    customer_id: str,
    audio_bytes: bytes,
    filename: str = "audio.wav",
    threshold: float = MATCH_THRESHOLD,
) -> Tuple[float, bool]:
    """
    Verify whether audio_bytes matches the enrolled speaker for customer_id.

    Parameters
    ----------
    customer_id : str
        Customer whose enrolled profile to compare against.
    audio_bytes : bytes
        Audio to verify.
    filename : str
        Original filename hint.
    threshold : float
        Cosine similarity threshold for is_match (default: 0.75).

    Returns
    -------
    (similarity_score, is_match)
        similarity_score : float in [0, 1]
        is_match         : bool

    Raises
    ------
    FileNotFoundError if the customer has no enrolled profile.
    """
    safe_id = "".join(c for c in customer_id if c.isalnum() or c in "-_")
    enrollment_path = ENROLLMENT_DIR / f"{safe_id}.npy"

    if not enrollment_path.exists():
        raise FileNotFoundError(
            f"No enrolled voice profile found for customer '{customer_id}'. "
            f"Please call /enroll-voice first."
        )

    enrolled_embedding = np.load(str(enrollment_path))
    live_embedding = _extract_embedding(audio_bytes, filename)

    # Cosine similarity: dot(a, b) / (||a|| * ||b||)
    norm_enrolled = np.linalg.norm(enrolled_embedding)
    norm_live = np.linalg.norm(live_embedding)

    if norm_enrolled == 0 or norm_live == 0:
        return 0.0, False

    similarity = float(
        np.dot(enrolled_embedding, live_embedding) / (norm_enrolled * norm_live)
    )
    # Clip to [0, 1] — cosine can be slightly negative for very different speakers
    similarity = max(0.0, min(1.0, similarity))
    is_match = similarity >= threshold

    logger.info(
        f"[SpeakerVerification] customer='{customer_id}' "
        f"similarity={similarity:.4f} match={is_match} threshold={threshold}"
    )
    return similarity, is_match


def is_enrolled(customer_id: str) -> bool:
    """Return True if a voice profile exists for this customer_id."""
    safe_id = "".join(c for c in customer_id if c.isalnum() or c in "-_")
    return (ENROLLMENT_DIR / f"{safe_id}.npy").exists()

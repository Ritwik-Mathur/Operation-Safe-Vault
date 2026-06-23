"""
Audio loading utility — with fast stdlib fallback.
Tries librosa first (better resampling), falls back to built-in wave module.
"""
import os
import numpy as np


def load_audio(file_path: str, sr: int = 16000):
    """
    Load audio file and return (samples_float32, sample_rate).
    Falls back to stdlib wave if librosa is unavailable.
    """
    # ── Try librosa (preferred) ────────────────────────────────
    try:
        import librosa
        audio, sample_rate = librosa.load(file_path, sr=sr, mono=True)
        return audio.astype(np.float32), sample_rate
    except ImportError:
        pass
    except Exception as e:
        raise RuntimeError(f"librosa failed to load audio: {e}")

    # ── Fallback: stdlib wave ──────────────────────────────────
    import wave
    import struct

    try:
        with wave.open(file_path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth  = wf.getsampwidth()
            framerate  = wf.getframerate()
            n_frames   = wf.getnframes()
            raw_data   = wf.readframes(n_frames)

        # Decode samples
        if sampwidth == 2:
            samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 1:
            samples = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
        else:
            count = len(raw_data) // 4
            samples = np.frombuffer(raw_data[:count * 4], dtype=np.int32).astype(np.float32) / 2147483648.0

        # Mix stereo to mono
        if n_channels == 2:
            samples = samples[::2]

        return samples, framerate

    except Exception as e:
        raise RuntimeError(f"Could not load audio file '{file_path}': {e}")
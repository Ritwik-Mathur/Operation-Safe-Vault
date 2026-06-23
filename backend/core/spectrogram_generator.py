"""
spectrogram_generator.py
════════════════════════
Fast mel-spectrogram PNG → base64 data URI.

Uses matplotlib's non-GUI 'Agg' backend (safe on headless servers).
Target: < 1 second for a 5-10 second audio clip at 6×3 inches / 80 dpi.
"""

import base64
import io
import os
import tempfile
from typing import Optional

# Force non-GUI Agg backend BEFORE any other matplotlib import
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


def generate_spectrogram_image(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    colormap: str = "magma",
    fig_width: float = 6.0,
    fig_height: float = 3.0,
    dpi: int = 80,
    n_mels: int = 64,
) -> Optional[str]:
    """
    Compute a mel-spectrogram from raw audio bytes and return it as a
    base64-encoded PNG data URI (``data:image/png;base64,...``).

    Parameters
    ----------
    audio_bytes : bytes
        Raw audio file content (any format librosa can load: WAV, MP3, …).
    filename : str
        Original filename — used only to infer format suffix for the temp file.
    colormap : str
        Matplotlib colormap.  'magma' or 'inferno' give strong visual contrast.
    fig_width, fig_height : float
        Figure dimensions in inches (kept small for speed).
    dpi : int
        Render resolution.  80 is plenty for a dashboard thumbnail.
    n_mels : int
        Number of mel frequency bins.  64 is fast; 128 for higher resolution.

    Returns
    -------
    str | None
        ``"data:image/png;base64,<encoded>"`` on success, or ``None`` if
        librosa / matplotlib are unavailable or the audio can't be loaded.
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        return None

    try:
        # ── Load audio ────────────────────────────────────────────────────────
        suffix = os.path.splitext(filename)[-1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        y, sr = librosa.load(tmp_path, sr=None, mono=True)
        os.unlink(tmp_path)

        # Resample to 16 kHz for consistency (matches the rest of the pipeline)
        if sr != 16_000:
            y = librosa.resample(y, orig_sr=sr, target_sr=16_000)
            sr = 16_000

        # ── Mel-spectrogram ───────────────────────────────────────────────────
        S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels, fmax=8_000)
        S_db = librosa.power_to_db(S, ref=np.max)

        # ── Render ────────────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        fig.patch.set_facecolor("#131313")   # match dashboard bg
        ax.set_facecolor("#131313")

        img = librosa.display.specshow(
            S_db,
            sr=sr,
            x_axis="time",
            y_axis="mel",
            fmax=8_000,
            cmap=colormap,
            ax=ax,
        )

        # Colorbar
        cbar = fig.colorbar(img, ax=ax, format="%+2.0f dB", pad=0.02)
        cbar.ax.yaxis.set_tick_params(color="white", labelsize=7)
        plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="white")
        cbar.outline.set_edgecolor("none")

        # Axis style
        ax.set_xlabel("Time (s)", color="#9e9e9e", fontsize=7)
        ax.set_ylabel("Hz (mel)", color="#9e9e9e", fontsize=7)
        ax.tick_params(colors="#9e9e9e", labelsize=6)
        for spine in ax.spines.values():
            spine.set_visible(False)

        plt.tight_layout(pad=0.4)

        # ── Encode to base64 PNG ──────────────────────────────────────────────
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)

        encoded = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    except Exception:
        # Never crash the main analysis pipeline over a visualization
        return None

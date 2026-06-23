"""
Video Deepfake Detector – Phase 1 Implementation
──────────────────────────────────────────────────
Three-layer pipeline (no trained model needed):

  1. Temporal Consistency Analysis
     AI-generated videos have unnaturally consistent pixel patterns
     between frames — real videos have natural micro-variations.

  2. Facial Region Artifact Detection
     GAN-generated faces leave compression artifacts and unnatural
     smoothness in facial regions detectable via frequency analysis.

  3. Audio-Video Sync Analysis
     Deepfake videos often have subtle lip-sync mismatch —
     audio energy peaks don't align with mouth movement regions.

Libraries: OpenCV (cv2), numpy — no trained model needed.
"""

import os
import tempfile
from typing import Dict, Any, List, Tuple

import numpy as np

from core.threat_score import ThreatScore


# ── Layer 1: Temporal Consistency Analysis ──────────────────────────────────

def temporal_analysis(frames: list) -> Tuple[float, List[str]]:
    """
    Real videos have natural frame-to-frame variation.
    AI/GAN-generated videos have unnaturally consistent pixel patterns.

    Method: compute per-pixel variance across consecutive frame pairs.
    Low variance = unnaturally smooth = deepfake signal.
    """
    score = 0.0
    reasons = []

    if len(frames) < 6:
        return 0.0, ["Not enough frames for temporal analysis"]

    try:
        # Compute frame-to-frame absolute differences
        diffs = []
        for i in range(1, len(frames)):
            diff = np.abs(frames[i].astype(np.float32) - frames[i-1].astype(np.float32))
            diffs.append(diff.mean())

        mean_diff   = float(np.mean(diffs))
        std_diff    = float(np.std(diffs))
        cv          = std_diff / (mean_diff + 1e-6)  # coefficient of variation

        # Real videos: mean_diff > 2.0, cv > 0.3
        # AI videos: unnaturally low diff and low cv (too smooth between frames)

        if mean_diff < 1.5:
            score += 30
            reasons.append(
                f"Unnaturally low frame-to-frame variation (mean diff: {mean_diff:.2f}) — "
                f"AI-generated video frames lack natural motion noise"
            )
        elif mean_diff < 3.0:
            score += 15
            reasons.append(
                f"Low frame variation ({mean_diff:.2f}) — possible synthetic video"
            )

        if cv < 0.2 and len(diffs) > 10:
            score += 20
            reasons.append(
                f"Unnaturally consistent inter-frame transitions (CV: {cv:.3f}) — "
                f"real videos have variable motion patterns"
            )

        # Check for frozen regions — deepfakes often have static background
        # while only the face region changes
        if len(frames) >= 10:
            sample_frames = frames[::max(1, len(frames)//10)][:10]
            region_vars = []
            h, w = sample_frames[0].shape[:2]
            # Sample 9 regions
            for ry in [0.1, 0.5, 0.8]:
                for rx in [0.1, 0.5, 0.8]:
                    y1, y2 = int(h*ry), int(h*(ry+0.15))
                    x1, x2 = int(w*rx), int(w*(rx+0.15))
                    region_pixels = [f[y1:y2, x1:x2].mean() for f in sample_frames]
                    region_vars.append(float(np.std(region_pixels)))

            frozen_regions = sum(1 for v in region_vars if v < 0.5)
            if frozen_regions >= 6:
                score += 15
                reasons.append(
                    f"{frozen_regions}/9 spatial regions show near-zero variance — "
                    f"frozen background pattern typical of face-swap deepfakes"
                )

    except Exception as e:
        reasons.append(f"Temporal analysis error: {str(e)[:80]}")

    return min(score, 60.0), reasons


# ── Layer 2: Facial Artifact Detection ──────────────────────────────────────

def artifact_analysis(frames: list) -> Tuple[float, List[str]]:
    """
    GAN-generated faces leave characteristic artifacts:
    - Unnatural frequency smoothness in facial regions (high-freq suppression)
    - Spectral flatness in DCT domain
    - Overly uniform skin texture (missing natural noise)
    """
    score = 0.0
    reasons = []

    if len(frames) < 3:
        return 0.0, []

    try:
        # Sample frames evenly
        sample = frames[::max(1, len(frames)//8)][:8]
        h, w   = sample[0].shape[:2]

        # Focus on center region (likely face area)
        cy, cx = h // 2, w // 2
        face_h, face_w = h // 3, w // 3
        y1, y2 = cy - face_h//2, cy + face_h//2
        x1, x2 = cx - face_w//2, cx + face_w//2

        flatness_vals = []
        texture_vars  = []

        for frame in sample:
            # Convert to grayscale for frequency analysis
            if len(frame.shape) == 3:
                gray = np.mean(frame[y1:y2, x1:x2], axis=2)
            else:
                gray = frame[y1:y2, x1:x2].astype(np.float32)

            if gray.size == 0:
                continue

            # FFT-based spectral flatness of face region
            spectrum   = np.abs(np.fft.fft2(gray)).flatten()
            spectrum   = spectrum + 1e-10
            geo_mean   = np.exp(np.mean(np.log(spectrum)))
            arith_mean = np.mean(spectrum)
            flatness   = float(geo_mean / arith_mean)
            flatness_vals.append(flatness)

            # Texture variance — GAN faces are too smooth
            texture_vars.append(float(gray.var()))

        if flatness_vals:
            mean_flat = float(np.mean(flatness_vals))
            if mean_flat > 0.12:
                score += 25
                reasons.append(
                    f"High spectral flatness in face region ({mean_flat:.4f}) — "
                    f"GAN-generated skin texture lacks natural high-frequency noise"
                )
            elif mean_flat > 0.07:
                score += 12
                reasons.append(
                    f"Elevated face region spectral flatness ({mean_flat:.4f}) — "
                    f"possible AI-generated facial texture"
                )

        if texture_vars:
            mean_tex = float(np.mean(texture_vars))
            if mean_tex < 50:
                score += 20
                reasons.append(
                    f"Unnaturally smooth face region (texture variance: {mean_tex:.1f}) — "
                    f"real faces have natural skin texture variation"
                )

    except Exception as e:
        reasons.append(f"Artifact analysis error: {str(e)[:80]}")

    return min(score, 50.0), reasons


# ── Layer 3: Audio-Video Sync Analysis ──────────────────────────────────────

def av_sync_analysis(video_path: str, frames: list) -> Tuple[float, List[str]]:
    """
    Deepfake videos often have subtle audio-video desynchronization.
    Method: compare audio energy peaks with mouth-region motion peaks.
    If they don't align temporally, it's a desync signal.
    """
    score = 0.0
    reasons = []

    try:
        import librosa

        # Extract audio from video using librosa (works on most formats)
        try:
            audio, sr = librosa.load(video_path, sr=16000, mono=True)
        except Exception:
            return 0.0, ["Could not extract audio from video"]

        if len(audio) < sr:
            return 0.0, ["Audio too short for sync analysis"]

        # Audio energy over time (frames)
        hop_length   = sr // 25  # ~25fps alignment
        rms          = librosa.feature.rms(y=audio, hop_length=hop_length)[0]
        audio_peaks  = _find_peaks(rms)

        # Mouth region motion (bottom-center of frame = mouth area)
        h, w = frames[0].shape[:2]
        mouth_y1, mouth_y2 = int(h * 0.65), int(h * 0.85)
        mouth_x1, mouth_x2 = int(w * 0.35), int(w * 0.65)

        mouth_motion = []
        for i in range(1, len(frames)):
            prev = frames[i-1][mouth_y1:mouth_y2, mouth_x1:mouth_x2].astype(np.float32)
            curr = frames[i  ][mouth_y1:mouth_y2, mouth_x1:mouth_x2].astype(np.float32)
            mouth_motion.append(float(np.abs(curr - prev).mean()))

        video_peaks = _find_peaks(np.array(mouth_motion))

        # Compare peak alignment
        if len(audio_peaks) > 2 and len(video_peaks) > 2:
            # Normalize to [0,1] range for comparison
            a_norm = np.array(audio_peaks) / max(len(rms), 1)
            v_norm = np.array(video_peaks) / max(len(frames), 1)

            # Find minimum distance between peak sets
            if len(a_norm) > 0 and len(v_norm) > 0:
                desync_scores = []
                for ap in a_norm[:5]:
                    distances = np.abs(v_norm - ap)
                    desync_scores.append(float(distances.min()))
                mean_desync = float(np.mean(desync_scores))

                if mean_desync > 0.15:
                    score += 30
                    reasons.append(
                        f"Audio-video desynchronization detected (desync score: {mean_desync:.3f}) — "
                        f"mouth movement doesn't align with speech energy peaks"
                    )
                elif mean_desync > 0.08:
                    score += 15
                    reasons.append(
                        f"Mild audio-video desync ({mean_desync:.3f}) — possible lip-sync mismatch"
                    )

    except ImportError:
        reasons.append("librosa not installed — AV sync check skipped")
    except Exception as e:
        reasons.append(f"AV sync error: {str(e)[:80]}")

    return min(score, 40.0), reasons


def _find_peaks(signal: np.ndarray, threshold_factor: float = 1.3) -> list:
    """Simple peak detection above mean threshold."""
    if len(signal) == 0:
        return []
    threshold = signal.mean() * threshold_factor
    peaks = [i for i in range(1, len(signal)-1)
             if signal[i] > threshold and signal[i] >= signal[i-1] and signal[i] >= signal[i+1]]
    return peaks


# ── Frame Extractor ──────────────────────────────────────────────────────────

def extract_frames(video_path: str, max_frames: int = 60) -> list:
    """Extract frames from video using OpenCV."""
    try:
        import cv2
    except ImportError:
        raise ImportError("opencv-python not installed — run: py -m pip install opencv-python")

    cap    = cv2.VideoCapture(video_path)
    frames = []

    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 25
    step   = max(1, total // max_frames)

    frame_idx = 0
    while len(frames) < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break
        # Resize to standard size for consistent analysis
        frame = cv2.resize(frame, (320, 240))
        frames.append(frame)
        frame_idx += step

    cap.release()
    return frames


# ── Main Detector ────────────────────────────────────────────────────────────

class VideoDetector:
    def analyze(self, video_bytes: bytes, filename: str) -> Dict[str, Any]:
        reasons = []

        # Save to temp file (OpenCV needs a file path)
        suffix = os.path.splitext(filename)[-1] or ".mp4"
        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(video_bytes)
                tmp_path = tmp.name

            # Extract frames
            try:
                frames = extract_frames(tmp_path)
            except ImportError as e:
                return ThreatScore.build(
                    score=0.0,
                    reasons=[str(e)],
                    source="video",
                    raw={"error": "opencv not installed", "frames_analyzed": 0}
                )

            if len(frames) < 3:
                return ThreatScore.build(
                    score=0.0,
                    reasons=["Could not extract frames from video"],
                    source="video",
                    raw={"frames_analyzed": 0}
                )

            # Layer 1 – Temporal consistency
            t_score, t_reasons = temporal_analysis(frames)
            reasons.extend(t_reasons)

            # Layer 2 – Facial artifact detection
            a_score, a_reasons = artifact_analysis(frames)
            reasons.extend(a_reasons)

            # Layer 3 – Audio-video sync
            s_score, s_reasons = av_sync_analysis(tmp_path, frames)
            reasons.extend(s_reasons)

            # Weighted combination
            # Temporal: 40%, Artifact: 35%, AV Sync: 25%
            final = (t_score * 0.40) + (a_score * 0.35) + (s_score * 0.25)

            # Override: if temporal + artifact both very high → force HIGH RISK
            is_deepfake = final > 50
            if t_score > 45 and a_score > 35:
                final = max(final, 80.0)
                reasons.insert(0,
                    "OVERRIDE: Both temporal inconsistency and facial artifacts "
                    "indicate AI-generated video — HIGH RISK"
                )

            return ThreatScore.build(
                score=final,
                reasons=reasons,
                source="video",
                raw={
                    "frames_analyzed": len(frames),
                    "temporal_score":  round(t_score, 1),
                    "artifact_score":  round(a_score, 1),
                    "av_sync_score":   round(s_score, 1),
                    "is_deepfake":     is_deepfake,
                }
            )

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

# Day 1 — Fraud Shield / Voice Guard (what we did)

## Run the Voice Guard API

From this folder (`Fraud_Detection_shield`):

```bash
python -m uvicorn voice_module.main:app --host 0.0.0.0 --port 8001 --reload
```

- Root: `http://127.0.0.1:8001`
- Health: `GET /health`
- Swagger: `http://127.0.0.1:8001/docs`
- Analyze audio: `POST /analyze_voice` (upload a `.wav` file)

Note: Prefer `python -m uvicorn voice_module.main:app` from this directory so imports resolve. Running `python voice_module/main.py` alone can mis-resolve the app name.

---

## What we verified

- End-to-end pipeline on sample audio (`temp.wav`): load audio → acoustic checks → spectral “deepfake” heuristic → Whisper transcript → keyword-based NLP → weighted **threat score** + **risk** label + **reasons** + **breakdown**.

---

## Recording scripts (for demos)

| File | Purpose |
|------|--------|
| `HIGH_THREAT_RECORDING_SCRIPT.txt` | Read aloud to aim for **high** NLP hits (many listed scam/urgency phrases). |
| `LOW_THREAT_RECORDING_SCRIPT.txt` | Short + two variants (coffee / ramen) to aim for **low** NLP; avoids trigger substrings. |
| `LOW_THREAT_RECORDING_SCRIPT_HI.txt` | Hindi low-threat script; notes on Whisper + English keyword list. |

---

## How the threat score works (simple)

Final **0–100** score blends three parts (see `voice_module/detector.py`):

1. **NLP (text)** — Whisper transcript; substring match on a **fixed English keyword list** + **urgency** phrases. Capped and weighted into the total.
2. **Acoustic** — pause ratio, loudness (RMS), zero-crossing rate, energy variance (robocall/TTS-style hints).
3. **Deepfake / spectral** — spectral flatness on FFT (heuristic, not a trained deepfake classifier).

**Risk bands (approx.):** SAFE → LOW → MEDIUM → HIGH (thresholds in code).

**Important:** Words like **“bank details”** or **“bank” alone** are **not** the same as the phrase **`bank account`** in the list — matching is literal substring on listed phrases. Words like **“scam”** may **not** be in the list unless added. Hindi transcripts won’t match English keywords unless Whisper outputs those English strings.

---

## Git / GitHub

- Remote: `https://github.com/lubdhak123/cadhackathon`
- We **committed and pushed** the recording scripts above.
- We **pulled** later remote updates (backend, `PROJECT_SUMMARY.md`, `test_voice.py`, assets, etc.) so local `main` matches `origin/main`.

---

## Limits (honest)

- NLP is **keyword/urgency rules**, not full “understand the sentence.”
- Spectral / acoustic parts are **heuristics** — false positives/negatives are possible.
- For strong “AI vs human” claims, you’d usually add **dedicated** anti-spoofing / deepfake models, not only flatness + simple stats.

---

*Day 1 log — session work consolidated in one place.*

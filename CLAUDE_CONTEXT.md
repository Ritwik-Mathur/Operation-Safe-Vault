# Fraud Shield AI (Zora AI Evolution) - Development Context & Handoff
**Last Updated:** April 2, 2026
**Team:** Phish Police
**Project Status:** Backend (100%), Live Call Integration (100%), Frontend UI (Polished)

## 1. Core Mission & Blueprint
The project is "Fraud Shield AI," an evolved, superior version of the "Zora AI" concept. It is a multi-agent orchestration layer designed to stop state-of-the-art "Sovereign AI Agents" (deepfakes, bespoke spear-phishing traps). Legacy security relies on Known Bad Lists; this project uses a hierarchical defense pipeline to analyze inputs in real-time.

*   **Ingestion:** Plugins, UI Dashboard, IMAP scanning, Live Phone Calls via Twilio Media Streams.
*   **Classifier:** Routes threats to specific scanners (Regex, NER, XGBoost, Llama 3, Whisper, Librosa, Yara).
*   **Security Gateway:** Shadow Guard (blocks prompt injection) and DLP Guard (prevents data leaks).
*   **Scoring:** A unified Threat Score (0-100) combining Text, URL, Voice, File, and Email assessments, refined by a precise Human-in-the-Loop feedback mechanism.

## 2. What Has Been Completed

### Session 1 (April 1, 2026)
1.  **Read the Pitch Deck:** Extracted and fully analyzed `ppt_cad.pdf`. Mapped the 16-slide pitch against the codebase.
2.  **Backend Dependencies Setup:** Generated `backend/requirements.txt` with all deep-tech libraries (FastAPI, `xgboost`, `faster-whisper`, `librosa`, `yara-python`, `playwright`, `chromadb`, etc.).
3.  **Environment Variables Template:** Generated `backend/.env.example` mapping Anthropic, IMAP, and VirusTotal keys.
4.  **Frontend "WOW" UI Overhaul:** Glassmorphism dark-mode aesthetic in `frontend/src/index.css` — neon cyans/reds, Outfit font, backdrop blur.

### Session 2 (April 2, 2026) — Major Feature: Live Call Analysis
5.  **Switched NLP from Claude/Gemini → Groq Llama 3.3 70B**
    - Gemini free tier hit 429 RESOURCE_EXHAUSTED on all keys
    - Replaced in `backend/detectors/voice_detector.py` — `from groq import Groq`
    - Model: `llama-3.3-70b-versatile`, max_tokens=200
    - GROQ_API_KEY in `.env`: see `backend/.env` (do not commit)
    - NLP multiplier increased from 0.3 → 0.5 for better scoring

6.  **Hindi/Urdu/Punjabi Translation**
    - Whisper detects language — if `hi/ur/pa`, re-transcribes with `task="translate"` to English
    - Ensures keyword matching and NLP both work on English text regardless of call language

7.  **Live Call Pipeline — `backend/core/live_call.py`** (NEW FILE)
    - `RiskState` dataclass: persists across 5s audio chunks per call
    - Weighted rolling score: recent chunks count more (sliding window)
    - `process_chunk()`: runs acoustic + transcription + keyword NLP + deepfake per chunk
    - `run_nlp_async()`: Groq NLP runs in background via `asyncio.ensure_future()` — doesn't block chunk pipeline
    - `transcribe_fast()`: uses Whisper `tiny` model (4x faster than `base`) for live calls
    - `keyword_score_rolling()`: scores on full rolling transcript, not just current chunk

8.  **Twilio Media Streams — `backend/core/twilio_stream.py`** (NEW FILE)
    - Receives mulaw G.711 8kHz audio from Twilio over WebSocket
    - `mulaw_to_wav()`: converts mulaw → PCM 16-bit → upsamples 8kHz → 16kHz via `audioop.ratecv()`
    - Accumulates 5-second chunks (40,000 samples) before analysis
    - Pushes results to frontend WebSocket (`/ws/dashboard/{call_id}`) in real time

9.  **New WebSocket Endpoints in `backend/main.py`**
    - `/ws/live-call/{call_id}` — direct WebSocket (client sends binary WAV chunks)
    - `/ws/dashboard/{call_id}` — frontend browser connects here for live score updates
    - `/ws/twilio-stream/{call_id}` — Twilio Media Streams connects here
    - `/twilio/voice-webhook` — returns TwiML to fork call audio to our stream

10. **Twilio Phone Number:** +1 762 339 3419
    - Purchased Georgia (US) number (India numbers unavailable on trial)
    - Voice URL set to: `https://cladocarpous-edwardo-unsolubly.ngrok-free.dev/twilio/voice-webhook`

11. **ngrok Setup**
    - URL: `https://cladocarpous-edwardo-unsolubly.ngrok-free.dev`
    - Auth token: `3BnFxp8XQG94PO0pOOB5YQg4nQn_3VEGYiom5YKZ4F3c3WWt2`
    - Run command: `ngrok http 8000`

12. **5 Bug Fixes Applied to Live Call Pipeline**
    - **Fix 1:** Groq NLP runs async — doesn't block chunk pipeline (`asyncio.ensure_future`)
    - **Fix 2:** Whisper `tiny` model for live calls (4x faster than `base`)
    - **Fix 3:** mulaw audio upsampled 8kHz → 16kHz before Whisper (better accuracy)
    - **Fix 4:** Keyword scoring on full rolling transcript, not just latest chunk
    - **Fix 5:** ABNORMAL_CLOSURE 1006 handled as normal call end, not error

13. **Phone Audio Calibration — Deepfake & Acoustic Thresholds**
    - Problem: thresholds were set for studio audio — caused false positives on real phone calls
    - mulaw 8kHz GSM codec naturally destroys spectral features that deepfake detection relies on
    - Fixed thresholds in `backend/detectors/voice_detector.py`:

    | Feature | Old Threshold | New Threshold | Why |
    |---|---|---|---|
    | Pitch variance | > 80 Hz | > 150 Hz | Phone speech naturally has high variance |
    | Average pitch | > 300 Hz | > 500 Hz | GSM compression inflates readings |
    | Speaking rate | > 6.0 syl/sec | > 7.5 syl/sec | Normal fast speech was triggering |
    | Spectral flatness | > 0.15 | > 0.35 | mulaw is naturally flat |
    | ZCR std | < 0.01 | < 0.005 | Phone audio has low ZCR variation |
    | MFCC variance | < 10 | < 3 | 8kHz compression reduces MFCC |
    | F0 jitter | < 2.0 Hz | < 0.5 Hz | GSM stabilizes pitch — real voices looked fake |
    | Centroid std | < 200 Hz | < 80 Hz | 8kHz bandwidth narrows centroids |

## 3. The Live Voice Guard Pipeline (Deep Dive)

### Layer 1: Acoustic Feature Extraction (How it's said)
Uses `librosa` to analyze human emotional/physiological markers:
*   **Pitch Variance (`piptrack`):** Detects stress/agitation. Threshold: > 150 Hz (phone-calibrated).
*   **Speaking Rate (`onset_detect`):** Flags rapid scripted delivery. Threshold: > 7.5 syl/sec.
*   **RMS Energy Variance:** Detects pressure tactics & shouting.
*   **Silence Ratio:** Flags automated robocalls that never pause.
*   **Boiler Room Detection:** 200-800 Hz band noise ratio > 2.5 = call center environment.

### Layer 2: Semantic Check / NLP (What is said)
*   **Live calls:** `faster-whisper` `tiny` model, int8 CPU, for speed.
*   **File uploads:** `faster-whisper` `base` model for better accuracy.
*   **Keyword scoring:** 400+ weighted phrases (English + Hindi + Hinglish + Devanagari).
*   **Urgency multiplier:** 1.5x all scores if urgency phrases detected ("right now", "abhi karo").
*   **Vector DB:** ChromaDB with 90+ known scam transcripts — semantic similarity scoring.
*   **Groq NLP:** Llama 3.3 70B classifies intent (banking_fraud, government_impersonation, etc.).
*   **Intent progression:** Tracks how scam unfolds across chunks over time.

### Layer 3: Deepfake Voice Detection (Is it human?)
Physics-based spectral analysis — no training dataset needed:
*   **Spectral Flatness:** AI voices are unnaturally smooth. Threshold: > 0.35 (phone-calibrated).
*   **ZCR Std:** AI has unnaturally consistent zero-crossings. Threshold: < 0.005.
*   **MFCC Variance:** AI lacks natural speech texture. Threshold: < 3.
*   **F0 Jitter:** AI pitch is unnaturally stable. Threshold: < 0.5 Hz (human baseline: 4-8 Hz).
*   **Spectral Centroid Std:** AI repeats spectral patterns. Threshold: < 80 Hz.
*   **Override rule:** If deepfake score > 70 → force final score to 85+ (HIGH RISK).

**Scoring weights:** 25% Acoustic + 45% NLP + 30% Deepfake

## 4. Environment Setup

### Starting the Backend
```bash
cd "C:\Users\kanis\OneDrive\Desktop\comeback hackathon\backend"
set TRANSFORMERS_OFFLINE=1
py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Note: `TRANSFORMERS_OFFLINE=1` prevents HuggingFace from trying to download models on startup.

### Starting the Frontend
```bash
cd "C:\Users\kanis\OneDrive\Desktop\comeback hackathon\frontend"
npm run dev
```

### Starting ngrok (required for Twilio)
```bash
ngrok http 8000
```
Then verify the URL matches `NGROK_URL` in `backend/.env`.

### Downloading Whisper Models (one-time)
```bash
py -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"
py -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
```

## 5. API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check |
| `/analyze/text` | POST | SMS/chat scam detection |
| `/analyze/url` | POST | URL sandbox + WHOIS analysis |
| `/analyze/voice` | POST | Upload audio file for analysis |
| `/analyze/video` | POST | Video deepfake detection |
| `/analyze/file` | POST | YARA + VirusTotal file scan |
| `/analyze/email` | POST | Email header + body analysis |
| `/analyze/full` | POST | Run all detectors combined |
| `/email/scan-inbox` | POST | IMAP inbox scan |
| `/feedback` | POST | Submit human verdict on analysis |
| `/feedback/stats` | GET | Accuracy statistics |
| `/ws/live-call/{call_id}` | WebSocket | Direct audio chunk streaming |
| `/ws/dashboard/{call_id}` | WebSocket | Frontend live score feed |
| `/ws/twilio-stream/{call_id}` | WebSocket | Twilio Media Streams input |
| `/twilio/voice-webhook` | POST | Twilio TwiML webhook |

## 6. Keys & Credentials (in backend/.env)
- `GROQ_API_KEY` — Llama 3.3 70B NLP
- `GEMINI_API_KEY` — backup (currently rate-limited)
- `NGROK_URL` — public URL for Twilio webhook
- `TWILIO_ACCOUNT_SID` — see `backend/.env` (do not commit)
- `TWILIO_AUTH_TOKEN` — in .env

## 7. Known Issues & Limitations
- **Score builds slowly:** First 1-2 chunks score low (no transcript yet). Need 30+ seconds of scam content to hit 80+.
- **Async NLP lag:** Groq result available on the *next* chunk, not current — inherent 5s delay.
- **No caller ID spoofing detection** — Twilio gives `From` number but no carrier lookup implemented yet.
- **Deepfake model is heuristic** — physics-based, not ML-trained. Calibrated for phone audio but still not as accurate as a trained model.

## 8. Pending / Future Work
- Frontend live dashboard (risk meter, transcript, alert UI during live call)
- Caller number spoofing check via Twilio Lookup API
- ML-based deepfake detection (speechbrain ASVspoof model) — post-hackathon
- 3 canned demo inputs for hackathon presentation

# FRAUD SHIELD AI — Complete Project Summary
### Status as of April 2, 2026

---

## What Is Built

### Backend (100% Complete)
| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app — all routes, startup, middleware wiring. Loads .env via python-dotenv |
| `backend/core/classifier.py` | Central brain — routes inputs to right detectors |
| `backend/core/threat_score.py` | Unified 0-100 scoring engine with fidelity ranking |
| `backend/core/vector_db.py` | ChromaDB vector database — 55 seeded scam templates (expanded from 24) |
| `backend/core/feedback.py` | Human-in-the-loop feedback storage + accuracy stats |
| `backend/middleware/shadow_guard.py` | Blocks prompt injection — FIXED to skip multipart body (was breaking file uploads) |
| `backend/middleware/dlp_guard.py` | Prevents sensitive data leaks in API responses |
| `backend/detectors/text_detector.py` | NLP (Claude) + Stylometry + Vector + AI-gen detection |
| `backend/detectors/credential_detector.py` | Regex + NER + Entropy analysis |
| `backend/detectors/url_detector.py` | Heuristics + SSL + WHOIS + Playwright sandbox + VirusTotal |
| `backend/detectors/voice_detector.py` | Full rewrite — see Voice Pipeline section below |
| `backend/detectors/video_detector.py` | NEW — Video deepfake detection (3 layers, no trained model needed) |
| `backend/detectors/file_detector.py` | YARA rules + ClamAV + VirusTotal hash lookup |
| `backend/detectors/email_detector.py` | IMAP integration + SPF/DKIM/DMARC header analysis |
| `backend/.env` | API keys file — add ANTHROPIC_API_KEY here |

### Frontend (Built, needs API key test)
| File | Purpose |
|------|---------|
| `frontend/src/App.jsx` | Main app shell — 3 tabs (Analyze / Inbox / Feedback) |
| `frontend/src/context/ApiContext.jsx` | API online status polling, post/get helpers |
| `frontend/src/components/Sidebar.jsx` | Nav tabs, API status dot |
| `frontend/src/components/Topbar.jsx` | Page title, LIVE badge |
| `frontend/src/components/AnalyzeTab.jsx` | 5 input modes: text/url/voice/file/email with drag-drop |
| `frontend/src/components/ScoreRing.jsx` | Animated SVG score ring, color by severity |
| `frontend/src/components/ResultPanel.jsx` | Score display, component bars, feedback buttons |
| `frontend/src/components/InboxTab.jsx` | IMAP inbox scanner UI |
| `frontend/src/components/FeedbackTab.jsx` | Stats grid + feedback history table |
| `frontend/src/index.css` | Glassmorphism theme — Outfit font, cyber-cyan #00f2fe, radial gradient |

### Test Scripts
| File | Purpose |
|------|---------|
| `test_voice.py` | Tests `/analyze/voice` and `/analyze/video` endpoints using requests library |

---

## Voice Detection Pipeline (Full Detail)

Three weighted layers:
- **Acoustic** (25%) — librosa signal analysis
- **Semantic/NLP** (45%) — Whisper STT + keyword + Vector DB + Claude Haiku
- **Deepfake** (30%) — spectral physics, no dataset needed

### Layer 1: Acoustic Analysis
- Pitch variance > 80Hz → emotional agitation (+15)
- Average pitch > 300Hz → stress indicator (+10)
- Speaking rate > 6 syllables/sec → scripted call (+10)
- RMS energy variance > 0.8 → shouting/pressure (+10)
- Silence ratio < 5% on calls > 10s → automated/scripted (+10)
- **Boiler room detection**: 200-800Hz band ratio > 2.5 → call center environment (+15)
- GSM preprocessing: normalize + resample to 16kHz before analysis (avoids false positives)
- Max acoustic score: 55

### Layer 2: Semantic / NLP
- **Whisper** `base` model, `language=None` → auto-detects Hindi/Urdu/English
- Keyword matching with **weighted scores per phrase** (OTP=40, CVV=35, Aadhaar=35...)
- **Urgency multiplier**: 1.5x on all keyword scores if urgency phrases present
- **PII scrubbing** before sending transcript to Claude (Aadhaar, PAN, card numbers, phone, OTP, email)
- **Vector DB similarity**: top match > 55% adds up to 30 points
- **Claude Haiku** intent classification: banking_fraud / government_impersonation / tech_support / kyc_scam / prize_scam / job_scam / family_emergency_impersonation
- Max NLP score: 85

### Phrase Coverage
- English: banking fraud, government impersonation, family emergency/voice cloning
- Hindi/Hinglish (Romanized): 35+ phrases covering all scam types
- **Devanagari**: OTP, CBI, Aadhaar, arrest, police, transfer, KYC, lottery, digital arrest etc.
- **Urdu script**: Whisper detects Urdu audio → Claude handles Urdu semantics (needs API key)

### Layer 3: Deepfake Detection
- **Spectral flatness** > 0.15 → synthetic voice (+25)
- **ZCR std** < 0.01 → unnaturally consistent zero-crossing (+20)
- **MFCC variance** < 10 → lacks natural speech texture (+20)
- **F0 jitter** < 2.0Hz → unnaturally stable pitch, human baseline 4-8Hz (+20)
- **Spectral envelope consistency**: centroid std < 200Hz → voice cloning artifact (+15)
- **Override rule**: deepfake score > 70 → force final score ≥ 85 (legitimate callers never use cloned voices)
- Max deepfake score: 80

### Known Limitation
- Physics-based deepfake detection catches obvious AI voices but may miss high-quality ElevenLabs/Microsoft clones
- Proper fix: AASIST model (state-of-the-art, 1MB) on RTX 3060 — postponed, not enough time for hackathon
- Frame as "Phase 1 heuristic baseline, Phase 2 = ASVspoof-trained AASIST model"

---

## Video Deepfake Detection Pipeline

Three weighted layers:
- **Temporal consistency** (40%) — frame-to-frame pixel variance
- **Facial artifact detection** (35%) — FFT spectral flatness of face region
- **AV sync analysis** (25%) — audio energy peaks vs mouth motion alignment

### Layer 1: Temporal Consistency
- Low mean frame diff < 1.5 → unnaturally smooth (+30)
- Low CV < 0.2 → consistent transitions (+20)
- Frozen spatial regions ≥ 6/9 → face-swap background freeze (+15)
- Max: 60

### Layer 2: Facial Artifact Detection
- High spectral flatness > 0.12 → GAN skin texture (+25)
- Low texture variance < 50 → unnaturally smooth face (+20)
- Max: 50

### Layer 3: AV Sync
- Mean desync > 0.15 → mouth doesn't match speech (+30)
- Mild desync > 0.08 → possible lip-sync mismatch (+15)
- Max: 40

### Override
- Temporal > 45 AND artifact > 35 → force final ≥ 80

---

## Vector DB (ChromaDB)

55 seeded scam templates covering:
- Banking impersonation calls (English + Hindi/Hinglish)
- Government impersonation (CBI, RBI, IT department, CBDT)
- Tech support scams
- KYC/UPI scams
- Loan/job scams
- Prize/lottery scams
- Family emergency / voice cloning scripts (English + Hindi)
- SMS phishing templates
- Email phishing templates

---

## API Endpoints

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| GET | `/` | Health check + feature list |
| POST | `/analyze/text` | SMS / Email scam detection |
| POST | `/analyze/url` | Full URL sandbox + WHOIS + SSL |
| POST | `/analyze/voice` | Voice call + deepfake detection |
| POST | `/analyze/video` | Video deepfake detection |
| POST | `/analyze/file` | Malware + YARA scan |
| POST | `/analyze/email` | Raw email + header forensics |
| POST | `/analyze/full` | ALL detectors combined |
| POST | `/email/scan-inbox` | Connect IMAP and scan inbox |
| POST | `/feedback` | Submit human verdict on a result |
| GET | `/feedback/stats` | Accuracy stats from user feedback |
| GET | `/feedback/recent` | Recent feedback entries |

---

## How to Run

### Backend
```bash
cd "comeback hackathon/backend"
py -m uvicorn main:app --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs  (NOTE: use test_voice.py for file uploads, not Swagger)
```

### Frontend
```bash
cd "comeback hackathon/frontend"
npm run dev
# UI: http://localhost:5173
```

### Test Voice/Video
```bash
# Edit test_voice.py to set file path, then:
py test_voice.py
```

---

## Environment Setup

Create `backend/.env`:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx   # Get from console.anthropic.com
```

Without API key: Claude NLP skipped, score relies on keyword + Vector DB only
With API key: Full Claude Haiku intent classification active — handles English, Hindi, Urdu, Hinglish

---

## Known Issues / Workarounds

| Issue | Cause | Fix |
|-------|-------|-----|
| 422 error on /analyze/voice in Swagger | Swagger can't do file uploads properly | Use test_voice.py instead |
| `python` not found | Windows uses `py` not `python` | Always use `py` command |
| Backend "Can not import module main" | Wrong directory | `cd backend` first, then uvicorn |
| Urdu audio scores low (23.6) | Whisper outputs Urdu script, keywords don't match | Fixed by Devanagari phrases + Claude API key needed for full Urdu support |
| librosa/faster-whisper not installed | Missing deps | `py -m pip install librosa faster-whisper opencv-python` |
| HuggingFace UNEXPECTED warning | sentence-transformers version mismatch | Harmless, ignore it |

---

## Test Results

### English scam call (WhatsApp Audio 2026-04-02 at 00.27.28.wav)
- Score: **52 — UNCERTAIN/MEDIUM**
- Transcript: "This is urgent, I am calling about your bank account, your account is suspended..."
- Signals: boiler room ratio 15.2, 90% vector DB match, urgency multiplier active, bank account/verify/blocked/suspended detected

### Urdu/Hindi scam call (WhatsApp Audio 2026-04-02 at 00.56.22.wav)
- Score: **23.6 — SAFE** (INCORRECT — Claude API key needed)
- Detected language: Urdu
- Signals fired: boiler room ratio 12.7, 62% match to "Bhai sahab, main CBI officer bol raha hoon"
- Problem: Urdu script keywords not in weighted dict, Claude NLP not active (no API key)
- Fix: Set ANTHROPIC_API_KEY in .env → Claude will read Urdu and score correctly

---

## What Makes This Different From Zora AI & Fraud Shield

| Feature | Zora AI | Fraud Shield | OURS |
|---------|---------|--------------|------|
| NLP Intent | Claude/custom | LLM | Claude Haiku |
| Stylometry | Yes | Yes | Yes |
| Vector DB | Yes | No | ChromaDB (55 templates) |
| Credential Detection | No | NER | Regex + NER + Entropy |
| URL Sandbox | Docker | Playwright | Playwright |
| SSL Check | TLS | Yes | Yes |
| WHOIS Lookup | No | No | Yes |
| Voice Analysis | Acoustic + STT | Yes | Acoustic + STT + Deepfake |
| Deepfake Voice Detection | No (planned) | No | YES — 5 signals |
| Video Deepfake Detection | No | No | YES — 3 layers |
| AI-Generated Text Detection | No | No | YES |
| File Scanning | YARA + ClamAV | Yes | YARA + ClamAV + VT |
| Email IMAP | SMTP only | Mentioned | Full IMAP |
| SPF/DKIM/DMARC | No | No | YES |
| Hindi/Urdu Support | No | No | YES — Whisper auto-detect |
| Shadow Guard | Yes | Yes | Yes (fixed multipart bug) |
| DLP Guard | No | Yes | Yes |
| Human Feedback Loop | No | Yes | Yes |
| Urgency Multiplier | No | No | YES — 1.5x on scam scores |
| Boiler Room Detection | No | No | YES — 200-800Hz band |
| PII Scrubbing | No | No | YES — before Claude API |
| GSM Preprocessing | No | No | YES — normalize + resample |

---

## Pending Before Hackathon (April 6)

- [ ] Set ANTHROPIC_API_KEY in backend/.env → enables Claude NLP for all languages
- [ ] Test frontend end-to-end (npm run dev + backend running)
- [ ] Prepare 3 canned demo inputs: scam SMS, phishing URL, scam call WAV
- [ ] Add video input tab to frontend AnalyzeTab
- [ ] Write backend/requirements.txt

## Timeline

| Date | Task |
|------|------|
| March 30 | Backend complete, PPT content drafted |
| April 1 | PPT submission deadline (Unstop) |
| April 2 | Voice pipeline tested, Hindi/Urdu support added, video deepfake built |
| April 4 | Shortlist announced |
| April 6-7 | Offline hackathon — build + demo |

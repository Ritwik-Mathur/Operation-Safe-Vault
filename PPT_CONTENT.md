# FRAUD SHIELD AI — PPT Slide Content
### Copy-paste each section into the Canva template

---

## SLIDE 1 — TITLE

**Big Title:**
FRAUD SHIELD AI

**Subtitle:**
AI-Powered Multi-Layer Scam Detection Suite

**Tagline (small, italic):**
"Because the next scam won't come from a human — it'll come from an AI."

**Bottom:**
[Your Team Name] | [Hackathon Name] 2026

---

## SLIDE 2 — PROBLEM STATEMENT

**Title:**
THE PROBLEM

**Heading:**
Fraud Is No Longer Manual — It's AI-Driven

**Stat 1 (big number):**
1,200%+
AI phishing surge since 2023

**Stat 2 (big number):**
$12.5B
Lost to online fraud in 2025

**Stat 3 (big number):**
54%
Click rate on AI-generated phishing vs 12% on human-written

**Stat 4 (big number):**
300%
Rise in voice cloning scams in India (2024-25)

**Bottom quote:**
"A single AI-generated scam call convinced a victim to share a ₹45,000 credit card OTP — existing tools detected nothing because they weren't listening."

---

## SLIDE 3 — WHY EXISTING TOOLS FAIL

**Title:**
THE GAP

**Column 1 — Current Tools:**
- Truecaller: Blocks known spam numbers. Fails on new numbers.
- Gmail Spam Filter: Pattern matching. AI-written emails bypass it.
- Bank Alerts: Post-fraud notifications. Damage already done.
- Antivirus: Scans files. Ignores voice calls and SMS.

**Column 2 — What's Missing:**
- No real-time voice analysis during calls
- No deepfake voice detection
- No AI-generated text identification
- No behavioral URL sandbox
- No unified system covering ALL attack surfaces

**Bottom line (bold):**
"Every tool today solves ONE piece. No one solves all six."

---

## SLIDE 4 — OUR SOLUTION

**Title:**
FRAUD SHIELD AI

**One-liner (large):**
One AI system that detects scams across SMS, Email, URLs, Voice Calls, and Files — in real time.

**Six boxes/icons:**

1. TEXT ANALYSIS
   NLP + Stylometry + Semantic Similarity
   "Understands what the message means, not just what it says"

2. CREDENTIAL DETECTION
   Regex + NER + Entropy Analysis
   "Catches hidden requests for OTPs, passwords, Aadhaar"

3. URL SANDBOX
   SSL + WHOIS + Playwright Browser Sandbox
   "Opens links safely to watch what they actually do"

4. VOICE ANALYSIS
   Acoustics + Speech-to-Text + Deepfake Detection
   "Analyzes calls in real-time — even catches AI-cloned voices"

5. FILE SCANNER
   YARA Rules + ClamAV + VirusTotal
   "Detects hidden scripts and malware in attachments"

6. EMAIL SHIELD
   IMAP + SPF/DKIM/DMARC + Header Forensics
   "Connects to your inbox and catches forged emails"

---

## SLIDE 5 — KEY DIFFERENTIATORS

**Title:**
WHAT MAKES US DIFFERENT

**Feature 1:**
AI-Generated Text Detection
"Detects if a phishing email was written by ChatGPT or similar AI — something no existing tool does."

**Feature 2:**
Deepfake Voice Detection
"Spectral analysis identifies synthetic/cloned voices on phone calls using F0 jitter, MFCC variance, and spectral flatness."

**Feature 3:**
Shadow Guard + DLP Guard
"Our AI protects itself. Shadow Guard blocks prompt injection attacks. DLP Guard prevents sensitive data leaks in responses."

**Feature 4:**
Human-in-the-Loop Feedback
"Users confirm or deny results. Every feedback improves the system. False positive rate drops over time."

**Feature 5:**
Threat Score with Reasoning
"Not a binary Yes/No. A 0-100 score with severity, confidence, fidelity ranking, and a full chain of reasoning."

---

## SLIDE 6 — SYSTEM ARCHITECTURE

**Title:**
SYSTEM ARCHITECTURE

**Use this as a flowchart layout:**

INPUT SOURCES
├── Web Dashboard
├── IMAP Email Hook
├── WhatsApp Bot (planned)
└── Browser Plugin (planned)
        │
        ▼
SECURITY LAYER
├── Shadow Guard (blocks prompt injection)
└── DLP Guard (prevents data leaks)
        │
        ▼
CENTRAL CLASSIFIER
Routes data to the right detectors
        │
        ▼
DETECTION ENGINE
┌─────────────────────────────────────┐
│  Text       │  Credential  │  URL   │
│  (NLP +     │  (Regex +    │  (SSL +│
│  Vector DB) │  NER +       │  WHOIS+│
│             │  Entropy)    │  Sand- │
│             │              │  box)  │
├─────────────┼──────────────┼────────┤
│  Voice      │  File        │  Email │
│  (STT +     │  (YARA +     │  (IMAP+│
│  Deepfake)  │  ClamAV)     │  SPF/  │
│             │              │  DKIM) │
└─────────────────────────────────────┘
        │
        ▼
RISK SCORING ENGINE
Weighted score + Fidelity ranking + Reasoning chain
        │
        ▼
HUMAN FEEDBACK LOOP
User confirms/denies → feeds back into Vector DB

---

## SLIDE 7 — HOW IT WORKS (DEMO FLOW)

**Title:**
HOW IT WORKS

**Step 1:**
User forwards suspicious SMS or pastes email into dashboard
→ Icon: message bubble

**Step 2:**
Central Classifier routes to Text + Credential + URL detectors
→ Icon: branching arrows

**Step 3:**
Each detector scores independently
→ Icon: gauge meters

**Step 4:**
Risk Scoring Engine combines all scores with weighted average
→ Icon: shield with score

**Step 5:**
User sees: Threat Score (0-100) + Verdict + Full Reasoning
→ Icon: report card

**Step 6:**
User gives feedback (Scam / Safe / Unsure) → system learns
→ Icon: thumbs up/down

---

## SLIDE 8 — TECH STACK

**Title:**
TECH STACK

**Layout: Grid of logos with labels**

| Tool | Purpose |
|------|---------|
| Python | Core language |
| FastAPI | API backend |
| Claude API (Anthropic) | NLP intent analysis + AI-text detection |
| ChromaDB | Vector database for semantic similarity |
| Sentence Transformers | Text embeddings (MiniLM-L6-v2) |
| Playwright | Headless browser URL sandbox |
| Whisper (faster-whisper) | Speech-to-text for voice calls |
| librosa | Audio acoustic analysis + deepfake detection |
| YARA | Malware rule engine for file scanning |
| ClamAV | Antivirus signature database |
| VirusTotal API | Community threat intelligence |
| Docker | URL sandbox isolation |

---

## SLIDE 9 — TARGET MARKET

**Title:**
WHO IS THIS FOR?

**Segment 1: Banks & Financial Institutions**
"Integrate via API to protect customers from phishing and voice fraud"
Market: 75+ Indian banks, ₹2,000 Cr digital fraud annually

**Segment 2: Telecom Companies**
"Pre-screen SMS before delivery. Flag scam calls in real-time."
Market: Jio, Airtel, Vi — 1.2B mobile subscribers

**Segment 3: Individual Consumers**
"WhatsApp bot + browser extension for personal protection"
Market: 800M+ internet users in India

**Segment 4: Government & Regulators**
"CERT-In, RBI, TRAI compliance tool for fraud monitoring"

---

## SLIDE 10 — MARKET SIZE

**Title:**
MARKET OPPORTUNITY

**TAM (Total Addressable Market):**
$15.2B — Global anti-fraud technology market (2025)

**SAM (Serviceable Available Market):**
$1.8B — India digital fraud prevention

**SOM (Serviceable Obtainable Market):**
$50M — AI-powered scam detection for Indian banks and telecom (Year 1 target segment)

**Growth:**
Anti-fraud market growing at 22% CAGR through 2030

---

## SLIDE 11 — COMPETITOR COMPARISON

**Title:**
COMPETITORS

**Table layout:**

| Feature | Truecaller | Gmail | Norton | Zora AI | FRAUD SHIELD AI |
|---------|-----------|-------|--------|---------|-----------------|
| SMS Scam Detection | Blocklist only | No | No | NLP + Vector | NLP + Vector + NER |
| Email Phishing | No | Pattern match | Basic | NLP | NLP + SPF/DKIM + IMAP |
| URL Analysis | No | Blocklist | Blocklist | Sandbox | Sandbox + SSL + WHOIS |
| Voice Call Analysis | Caller ID | No | No | Acoustic + STT | Acoustic + STT + Deepfake |
| File Scanning | No | Basic | Signature | YARA + ClamAV | YARA + ClamAV + VT |
| AI-Text Detection | No | No | No | No | YES |
| Deepfake Detection | No | No | No | No | YES |
| Prompt Injection Guard | No | No | No | Yes | Yes + DLP |
| Human Feedback Loop | Report spam | Report | No | No | YES |
| Real-time | No | No | No | Partial | YES |

---

## SLIDE 12 — OUR ADVANTAGE

**Title:**
WHY WE WIN

**Point 1:**
"They check blocklists. We analyze behavior."
→ Static databases become outdated the moment a new scam is created.

**Point 2:**
"They detect known threats. We catch unknown ones."
→ Vector similarity + NLP means even a brand-new scam template gets flagged.

**Point 3:**
"They work after the attack. We work during it."
→ Real-time voice analysis catches scams while the call is happening.

**Point 4:**
"They're siloed tools. We're one unified shield."
→ One API, one score, six detection layers.

---

## SLIDE 13 — FEASIBILITY

**Title:**
FEASIBILITY & BUILDABILITY

**What's Already Built (Backend):**
- Complete FastAPI backend with all 6 detectors
- Shadow Guard + DLP Guard middleware
- ChromaDB vector database seeded with 24 scam templates
- Threat scoring engine with fidelity ranking
- Human feedback storage system

**Buildable in 24hr Hackathon:**
- Frontend dashboard (HTML/CSS/JS — no build step)
- WhatsApp bot integration (Twilio API)
- Live demo with sample scam messages, URLs, and audio

**Post-Hackathon Scale:**
- Browser extension (Chrome)
- pip install fraud-shield-ai (developer SDK)
- Bank API integration

**Key Insight:**
"Every component uses established, production-ready libraries. No experimental research — just smart engineering."

---

## SLIDE 14 — EXPECTED IMPACT

**Title:**
EXPECTED IMPACT

**Metric 1:**
95%+ detection rate on known scam patterns
(via vector similarity + NLP)

**Metric 2:**
First-ever real-time deepfake voice detection for phone calls
(spectral + MFCC analysis)

**Metric 3:**
< 2 second analysis time per message
(lightweight models, no GPU required)

**Metric 4:**
Self-improving system via human feedback loop
(false positive rate decreases with every user interaction)

**Impact statement:**
"If deployed across one Indian telecom network, Fraud Shield AI could prevent an estimated ₹500 Cr in fraud losses annually."

---

## SLIDE 15 — ROADMAP

**Title:**
ROADMAP

**Phase 1 — Hackathon (April 2026):**
- Complete working prototype
- Live demo: SMS + URL + Voice + File analysis
- WhatsApp bot demo

**Phase 2 — Post-Hackathon (Q2 2026):**
- Chrome browser extension
- pip install fraud-shield-ai SDK
- Bank pilot integration

**Phase 3 — Scale (Q3-Q4 2026):**
- Video call deepfake detection
- Telecom carrier integration
- Multi-language support (Hindi, Tamil, Telugu)
- CERT-In / RBI compliance module

---

## SLIDE 16 — TEAM

**Title:**
THE TEAM

[Member 1 Name]
Role: Backend + AI/ML
"Experience with..."

[Member 2 Name]
Role: Frontend + Design
"Experience with..."

[Member 3 Name]
Role: Security + Infrastructure
"Experience with..."

[Member 4 Name]
Role: Research + Presentation
"Experience with..."

**Bottom:**
"We don't just detect scams — we build the shield that protects itself."

---

## NOTES FOR CANVA

- Use the BLUE/PURPLE gradient from your template for most slides
- Use RED accent for the Problem Statement slide (urgency)
- Use GREEN accent for Solution and Impact slides (positive)
- Keep text minimal — big numbers, short bullets, icons
- Architecture slide: use Canva's flowchart elements
- Competitor table: use Canva's table element with checkmarks (✓) and crosses (✗)
- Add the logos of tools in the Tech Stack slide (search Canva for "Python logo", "Docker logo", etc.)

"""
Voice Detector – Enhanced Real-Time Call Analysis
──────────────────────────────────────────────────
Four-layer pipeline:
  1. Acoustic analysis      (librosa) – tone, pitch, energy, boiler room noise
  2. Speech-to-Text + NLP   (Whisper + keyword + vector + Claude)
  3. Deepfake detection     (spectral physics — no dataset needed)
  4. Speaker verification   (SpeechBrain ECAPA-TDNN — optional, requires enrollment)

Extras:
  - GSM preprocessing       (normalize + resample before spectral analysis)
  - PII redaction           (scrub before sending transcript to Claude)
  - Deepfake override       (if deepfake score > 70 → force HIGH RISK)
  - Voice cloning detection (family impersonation via spectral envelope analysis)
  - Impersonation detection (if enrolled voice doesn't match live caller → raises risk)
"""

import os
import io
import re
import json
import tempfile
from typing import Dict, Any, List, Tuple

from groq import Groq

from core.threat_score import ThreatScore
from core.vector_db import VectorDB


# ── PII Scrubber (runs before transcript hits Claude) ───────────────────────

def scrub_pii(text: str) -> str:
    """Redact sensitive identifiers before sending to external LLM API."""
    text = re.sub(r'\b\d{12}\b', '[AADHAAR]', text)                     # Aadhaar
    text = re.sub(r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN]', text)             # PAN card
    text = re.sub(r'\b\d{16}\b', '[CARD_NUMBER]', text)                  # Credit/debit card
    text = re.sub(r'\b\d{9,11}\b', '[PHONE]', text)                      # Phone numbers
    text = re.sub(r'\b\d{6}\b', '[OTP_OR_PIN]', text)                    # OTP / PIN
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL]', text)            # Email addresses
    text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
                  '[CARD_NUMBER]', text)                                  # Card with spaces
    return text


# ── GSM Audio Preprocessor ──────────────────────────────────────────────────

def preprocess_audio(y, sr):
    """
    Normalize and resample audio for telephonic recordings.
    Phone calls use GSM codec — cuts frequencies above 3.4 kHz,
    which can cause false positives in MFCC/spectral flatness analysis.
    """
    try:
        import librosa
        import numpy as np
        # Normalize amplitude
        y = librosa.util.normalize(y)
        # Resample to 16kHz (standard for speech processing)
        if sr != 16000:
            y = librosa.resample(y, orig_sr=sr, target_sr=16000)
            sr = 16000
        return y, sr
    except Exception:
        return y, sr


# ── Layer 1: Acoustic Analysis ──────────────────────────────────────────────

def acoustic_analysis(audio_bytes: bytes, filename: str) -> Tuple[float, List[str]]:
    try:
        import librosa
        import numpy as np
    except ImportError:
        return 0.0, ["librosa not installed – acoustic analysis skipped"]

    reasons = []
    score = 0.0

    try:
        suffix = os.path.splitext(filename)[-1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        y, sr = librosa.load(tmp_path, sr=None, mono=True)
        os.unlink(tmp_path)

        # Preprocess for telephonic audio
        y, sr = preprocess_audio(y, sr)
        duration = librosa.get_duration(y=y, sr=sr)

        # Pitch variance – rapid changes = agitation / pressure
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_vals = pitches[magnitudes > magnitudes.mean()]
        if len(pitch_vals) > 0:
            pitch_std = float(pitch_vals.std())
            pitch_mean = float(pitch_vals[pitch_vals > 0].mean()) if (pitch_vals > 0).any() else 0
            if pitch_std > 150:  # phone audio calibrated (was 80 — too sensitive for GSM)
                score += 15
                reasons.append(f"High pitch variance ({pitch_std:.0f} Hz) – emotional agitation")
            if pitch_mean > 500:  # phone audio calibrated (was 300)
                score += 10
                reasons.append(f"Elevated average pitch ({pitch_mean:.0f} Hz) – stress indicator")

        # Speaking rate via onset detection (more accurate than beat_track for speech)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        if duration > 0:
            syllable_rate = len(onset_frames) / duration
            if syllable_rate > 7.5:  # phone audio calibrated (was 6.0 — too sensitive)
                score += 10
                reasons.append(f"High speaking rate ({syllable_rate:.1f} syllables/sec) – scripted call pattern")

        # RMS energy – shouting / pressure
        rms = librosa.feature.rms(y=y)[0]
        rms_std = float(rms.std())
        rms_mean = float(rms.mean())
        if rms_mean > 0 and rms_std / rms_mean > 0.8:
            score += 10
            reasons.append("High energy variance – shouting/pressure pattern")

        # Silence ratio – scripted calls have little silence
        silent_frames = (rms < 0.01).sum()
        silence_ratio = silent_frames / max(len(rms), 1)
        if silence_ratio < 0.05 and duration > 10:
            score += 10
            reasons.append("Very low silence ratio – automated/scripted call")

        # Boiler room background noise detection
        # Call centers have a characteristic ambient frequency profile (200-800 Hz band noise)
        if duration > 5:
            stft = np.abs(librosa.stft(y))
            freqs = librosa.fft_frequencies(sr=sr)
            boiler_band = stft[(freqs >= 200) & (freqs <= 800), :]
            background_band = stft[(freqs > 800), :]
            if background_band.mean() > 0:
                boiler_ratio = boiler_band.mean() / background_band.mean()
                if boiler_ratio > 2.5:
                    score += 15
                    reasons.append(
                        f"Background noise profile matches call center environment "
                        f"(boiler room ratio: {boiler_ratio:.1f})"
                    )

    except Exception as e:
        reasons.append(f"Acoustic error: {str(e)[:80]}")

    return min(score, 55.0), reasons


# ── Layer 2: Speech-to-Text + NLP ───────────────────────────────────────────

SCAM_PHRASES = [
    # English — banking / financial
    "otp", "one time password", "share your otp", "verify your account",
    "bank account", "credit card", "debit card", "cvv", "pin number",
    "arrested", "police", "legal action", "income tax", "aadhaar",
    "transfer money", "send money", "remote access", "teamviewer", "anydesk",
    "lottery", "prize", "won", "lucky draw", "customs", "parcel",
    "kyc", "update kyc", "suspended", "blocked", "expire",
    "government scheme", "subsidy", "refund", "insurance claim",
    "social security", "warrant", "fraud department",

    # English — family emergency / voice cloning scam
    "i'm in trouble", "i need help", "don't tell mom", "don't tell dad",
    "i had an accident", "i'm at the police station", "bail money",
    "new number", "lost my phone", "send money urgently", "i got arrested",
    "please don't tell anyone", "i'm in jail", "hospital emergency",

    # Hindi / Hinglish — banking
    "otp batao", "otp share karo", "otp bata do", "otp dena hoga",
    "aadhaar number do", "aadhaar card bhejo", "pan card number do",
    "account band ho jayega", "account block ho jayega", "account suspend ho jayega",
    "police aa jayegi", "police bhej denge", "arrest ho jaoge", "giraftari hogi",
    "court notice", "legal notice bheja hai", "case darj ho gaya",
    "kyc update karo", "kyc incomplete hai", "kyc verify karo",
    "paisa transfer karo", "paise bhejo", "turant transfer karo",
    "inaam mila hai", "lucky draw mein naam aaya", "inam jeeta hai",
    "customs department", "customs mein parcel hai", "cbdt notice",
    "rbi se call", "rbi bol raha hoon", "rbi ka notice",
    "sbi se bol raha hoon", "hdfc se call", "bank manager bol raha hoon",
    "sim band ho jayega", "number block ho jayega",
    "abhi karo warna", "ek ghante mein", "turant karo",
    "kisi ko mat batana", "call mat kato", "line pe raho",
    "ghar pe akele ho", "parivaar ko mat batana",
    "digital arrest", "cyber crime department",

    # Hindi / Hinglish — family emergency / voice cloning
    "main musibat mein hoon", "mujhe paison ki zaroorat hai",
    "accident ho gaya", "hospital mein hoon", "police station pe hoon",
    "bail chahiye", "naya number hai mera", "phone kho gaya",
    "kisi ko mat batana", "please help karo", "emergency hai",
    "ghar pe kisi ko mat batana", "abhi transfer karo",

    # Devanagari — Whisper outputs native script for Hindi audio
    "ओटीपी", "ओटीपी बताओ", "ओटीपी शेयर करो", "ओटीपी दो",
    "आधार", "आधार नंबर", "पैन कार्ड",
    "बैंक अकाउंट", "खाता बंद", "खाता ब्लॉक", "अकाउंट सस्पेंड",
    "पैसे ट्रांसफर करो", "अभी ट्रांसफर करो", "तुरंत करो",
    "पुलिस आ जाएगी", "गिरफ्तारी होगी", "केस दर्ज",
    "केवाईसी", "केवाईसी अपडेट", "केवाईसी वेरीफाई",
    "कस्टम विभाग", "पार्सल", "लॉटरी", "इनाम",
    "किसी को मत बताना", "लाइन पे रहो", "फोन मत काटना",
    "डिजिटल अरेस्ट", "साइबर क्राइम",
    "मुसीबत में हूं", "पैसों की जरूरत है", "एक्सीडेंट हो गया",
    "बेल चाहिए", "नया नंबर है", "इमरजेंसी है",
]

URGENCY_PHRASES = [
    # English
    "immediately", "urgent", "right now", "quickly", "hurry", "within one hour",
    "last chance", "don't hang up", "stay on the line",
    # Hindi / Hinglish
    "abhi karo", "turant karo", "jaldi karo", "ek ghante mein",
    "aaj hi", "der mat karo", "phone mat katna", "line pe raho",
    "warna action liya jayega", "warna case hoga",
    # Devanagari urgency
    "अभी करो", "तुरंत करो", "जल्दी करो", "एक घंटे में",
    "आज ही", "देर मत करो", "फोन मत काटना", "लाइन पे रहो",
    "वरना एक्शन", "वरना केस होगा", "अभी नहीं तो",
]


def transcribe(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio — multilingual (en + hi) for Hindi/Hinglish support."""
    try:
        from faster_whisper import WhisperModel
        suffix = os.path.splitext(filename)[-1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        # base model for better accuracy on Indian-accented English + Hindi
        model = WhisperModel("base", device="cpu", compute_type="int8")
        # Try auto-detect first, then retry with Hindi if non-Latin script detected
        segments_list, info = model.transcribe(tmp_path, language=None)
        transcript = " ".join(s.text for s in segments_list)
        # If detected language is Hindi/Urdu, re-transcribe with translate to English
        # so keyword matching and NLP both work on readable text
        if info.language in ("hi", "ur", "pa"):
            segments_list, _ = model.transcribe(tmp_path, language=info.language, task="translate")
            transcript = " ".join(s.text for s in segments_list)
        os.unlink(tmp_path)
        return transcript
    except ImportError:
        pass

    # Fallback: OpenAI Whisper API
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            buf = io.BytesIO(audio_bytes)
            buf.name = filename
            result = client.audio.transcriptions.create(model="whisper-1", file=buf)
            return result.text
        except Exception:
            pass

    return ""


VOICE_NLP_SYSTEM = """You are a scam call detection engine. Analyze this phone call transcript and return ONLY valid JSON:
{
  "is_scam": true/false,
  "confidence": 0-100,
  "intent": "banking_fraud|government_impersonation|tech_support|kyc_scam|prize_scam|job_scam|family_emergency_impersonation|legitimate|unknown",
  "reasoning": "one sentence"
}
Focus on:
- Requests for OTP, passwords, card details, Aadhaar, PAN
- Impersonating banks, RBI, CBI, police, government departments
- Threats of arrest, account suspension, legal action
- Urgency pressure and isolation tactics (don't tell anyone)
- Family emergency claims + urgent money requests (voice cloning pattern)
- Caller claims to be a family member from a new number in distress"""


def nlp_on_transcript(transcript: str, vector_db: VectorDB = None) -> Tuple[float, List[str]]:
    if not transcript:
        return 0.0, ["Could not transcribe audio"]

    lower = transcript.lower()
    reasons = []
    score = 0.0

    # ── Keyword baseline with urgency multiplier ────────────────────────────
    # Weighted scores per keyword — higher risk phrases score more
    SCAM_WEIGHTS = {
        # ── English: OTP / Credentials (highest risk) ──────────────────────
        "otp": 40, "one time password": 40, "share your otp": 40,
        "enter your otp": 40, "give me your otp": 40, "read your otp": 40,
        "cvv": 40, "cvv number": 40, "card number": 40, "card details": 40,
        "card verification": 40, "security code": 35,
        "bank details": 40, "account details": 40, "forward your bank": 40,
        "give your bank details": 40, "share your bank details": 40,
        "account number": 35, "routing number": 35, "sort code": 35, "ifsc": 30,
        "aadhaar": 35, "aadhar": 35, "aadhaar number": 40, "aadhaar card": 35,
        "pan card": 35, "pan number": 35, "pan details": 35,
        "passport number": 30, "driving licence": 25, "voter id": 25,
        "anydesk": 40, "teamviewer": 40, "remote access": 40,
        "screen share": 35, "screen sharing": 35, "remote desktop": 40,
        "ultraviewer": 40, "airdroid": 35, "quick support": 35,
        "pin number": 35, "pin code": 35, "atm pin": 40, "atm card": 30,
        "net banking": 30, "internet banking": 30, "mobile banking": 30,
        "banking password": 40, "login password": 35, "account password": 35,
        "upi pin": 40, "upi id": 25, "upi number": 25,
        "google pay": 20, "phonepe": 20, "paytm": 20, "bhim": 20,
        "neft": 25, "rtgs": 25, "imps": 25,
        "username": 25, "user id": 25, "login id": 25,

        # ── English: Impersonation / Authority Threats ──────────────────────
        "arrested": 25, "arrest": 25, "digital arrest": 40,
        "warrant": 30, "arrest warrant": 40, "non-bailable warrant": 40,
        "fir": 25, "fir registered": 30, "case registered": 30,
        "police": 15, "police officer": 25, "police station": 20,
        "cbi": 30, "cbi officer": 35, "central bureau": 35,
        "ib officer": 35, "intelligence bureau": 35,
        "income tax": 25, "income tax officer": 35, "income tax department": 35,
        "it department": 25, "it notice": 30, "tax evasion": 35,
        "enforcement directorate": 35, "ed officer": 35,
        "rbi": 25, "reserve bank": 25, "rbi governor": 30,
        "sebi": 25, "trai": 25, "dot": 20,
        "customs": 20, "customs officer": 30, "customs department": 30,
        "court notice": 30, "legal notice": 25, "summons": 30,
        "case filed": 25, "complaint filed": 25, "chargesheet": 30,
        "money laundering": 35, "hawala": 35,
        "narcotics": 30, "drug case": 30, "drugs found": 35,
        "terrorism": 30, "terror funding": 35,
        "cybercrime": 25, "cyber crime department": 30, "cyber cell": 25,
        "fraud department": 25, "fraud investigation": 25,
        "social security": 25, "social security number": 35,
        "medicare": 20, "irs": 30, "tax refund": 25,

        # ── English: Account Suspension ─────────────────────────────────────
        "bank account": 20, "account suspended": 30, "account blocked": 30,
        "account frozen": 30, "account closed": 25, "account deactivated": 25,
        "account terminated": 25, "account on hold": 25,
        "kyc": 20, "kyc update": 25, "kyc incomplete": 25, "kyc expired": 25,
        "kyc verification": 25, "kyc pending": 20,
        "verify your account": 25, "verify your details": 30,
        "verify immediately": 35, "verify your identity": 30,
        "blocked": 15, "suspended": 15, "expired": 15, "deactivated": 20,
        "sim blocked": 30, "sim suspended": 30, "number blocked": 25,
        "sim card": 20, "mobile number": 15,

        # ── English: Money Transfer ──────────────────────────────────────────
        "transfer money": 35, "send money": 35, "wire transfer": 35,
        "money transfer": 35, "transfer funds": 35, "send funds": 35,
        "deposit money": 30, "deposit cash": 30, "deposit amount": 30,
        "gift card": 30, "itunes card": 35, "google play card": 35,
        "amazon gift card": 35, "steam card": 35, "voucher code": 30,
        "western union": 35, "money gram": 35, "crypto": 25,
        "bitcoin": 30, "cryptocurrency": 30, "wallet address": 35,
        "safe account": 40, "safety account": 40, "secure account": 35,
        "government account": 35, "rbi account": 40,

        # ── English: Social Engineering / Isolation ──────────────────────────
        "don't tell anyone": 30, "do not tell anyone": 30,
        "don't tell your family": 30, "don't tell your wife": 30,
        "don't tell your husband": 30, "keep this confidential": 25,
        "keep this secret": 25, "this is confidential": 25,
        "stay on the line": 20, "don't hang up": 20, "do not hang up": 20,
        "don't call back": 25, "do not call anyone": 30,
        "don't contact your bank": 30, "don't go to the bank": 25,
        "we are monitoring": 20, "your call is being recorded": 15,
        "this is your last chance": 30, "final warning": 25,
        "within 24 hours": 25, "within one hour": 30, "within 30 minutes": 35,
        "immediately": 20, "right now": 20, "urgent": 15, "emergency": 15,

        # ── English: Prize / Lottery / Job Scams ────────────────────────────
        "lottery": 20, "lucky draw": 20, "prize money": 25,
        "you have won": 25, "you are selected": 20, "congratulations": 10,
        "claim your prize": 25, "claim your reward": 25,
        "processing fee": 25, "registration fee": 20, "advance fee": 30,
        "job offer": 15, "work from home": 15, "easy money": 20,
        "investment opportunity": 20, "guaranteed returns": 25,
        "double your money": 30, "high returns": 20,
        "refund": 15, "insurance claim": 15, "government scheme": 15, "subsidy": 15,
        "parcel": 15, "package": 10, "prize": 15,

        # ── English: Family Emergency / Voice Cloning ────────────────────────
        "i'm in trouble": 30, "i am in trouble": 30,
        "i had an accident": 35, "i got arrested": 35,
        "i'm at the police station": 35, "i am at the police station": 35,
        "i need bail money": 40, "bail money": 40, "bail amount": 35,
        "don't tell mom": 30, "don't tell dad": 30,
        "new number": 15, "lost my phone": 15, "i'm in hospital": 30,
        "send money urgently": 40, "please send money": 35,

        # ── English: Tech Support Scams ──────────────────────────────────────
        "virus detected": 25, "malware detected": 25, "hacked": 20,
        "your account is hacked": 30, "microsoft support": 30,
        "windows support": 30, "apple support": 30,
        "technical support": 20, "tech support": 20,
        "overpaid": 20, "accidental transfer": 25,
        "password": 20, "credit card": 20, "debit card": 20,

        # ── Devanagari: Credentials ──────────────────────────────────────────
        "ओटीपी": 40, "ओटीपी बताएं": 40, "ओटीपी दीजिए": 40,
        "पिन": 35, "एटीएम पिन": 40, "पासवर्ड": 35,
        "आधार": 35, "आधार नंबर": 40, "आधार कार्ड": 35,
        "पैन कार्ड": 35, "पैन नंबर": 35,
        "बैंक डिटेल्स": 40, "खाता नंबर": 35, "अकाउंट नंबर": 35,
        "नेट बैंकिंग": 30, "यूपीआई पिन": 40, "यूपीआई आईडी": 25,

        # ── Devanagari: Impersonation / Threats ─────────────────────────────
        "सीबीआई": 35, "सीबीआई अधिकारी": 40, "आयकर": 30,
        "प्रवर्तन निदेशालय": 35, "ईडी": 30,
        "गिरफ्तार": 30, "गिरफ्तारी": 30, "अरेस्ट": 30, "डिजिटल अरेस्ट": 40,
        "पुलिस": 20, "पुलिस अधिकारी": 25, "थाना": 20,
        "केस दर्ज": 25, "एफआईआर": 25, "वारंट": 30,
        "कोर्ट नोटिस": 30, "कानूनी नोटिस": 25,
        "मनी लॉन्ड्रिंग": 35, "नशीले पदार्थ": 30,
        "साइबर क्राइम": 25, "साइबर सेल": 25,
        "आरबीआई": 25, "रिजर्व बैंक": 25,
        "ट्राई": 20, "दूरसंचार विभाग": 20,

        # ── Devanagari: Account / Transfer ──────────────────────────────────
        "बैंक अकाउंट": 20, "खाता बंद": 25, "खाता ब्लॉक": 25,
        "केवाईसी": 20, "केवाईसी अपडेट": 25, "केवाईसी वेरीफाई": 25,
        "पैसे ट्रांसफर": 35, "ट्रांसफर करो": 30, "पैसे भेजो": 35,
        "सुरक्षित खाता": 40, "सेफ अकाउंट": 40,
        "सिम बंद": 30, "नंबर ब्लॉक": 25,

        # ── Devanagari: Social Engineering ──────────────────────────────────
        "किसी को मत बताना": 30, "परिवार को मत बताना": 30,
        "लाइन पे रहो": 20, "फोन मत काटना": 20,
        "अभी करो": 25, "तुरंत करो": 25, "जल्दी करो": 20,
        "आखिरी मौका": 30, "अंतिम चेतावनी": 25,
        "कस्टम": 20, "पार्सल": 15, "इनाम": 15, "लॉटरी": 20,
        "एसबीआई": 20, "बैंक मैनेजर": 20,
        "इमरजेंसी": 15, "मुसीबत": 15, "बेल": 20,

        # ── Hinglish (Romanized) ─────────────────────────────────────────────
        "otp batao": 40, "otp share karo": 40, "otp bata do": 40,
        "pin batao": 35, "password batao": 35, "details batao": 30,
        "account band ho jayega": 30, "account block ho jayega": 30,
        "kyc update karo": 25, "kyc verify karo": 25,
        "paisa transfer karo": 35, "paise bhejo": 35, "abhi transfer karo": 40,
        "giraftari hogi": 30, "arrest ho jaoge": 30, "police aa jayegi": 25,
        "case darj ho gaya": 25, "fir darj": 25,
        "rbi se call": 25, "cbi se call": 35, "bank manager bol raha hoon": 25,
        "kisi ko mat batana": 30, "line pe raho": 20, "phone mat katna": 20,
        "safe account mein transfer": 40, "government account mein daalo": 35,
    }

    has_urgency = any(u in lower for u in URGENCY_PHRASES)
    # 1.5x multiplier on all scam scores if urgency is present
    urgency_multiplier = 1.5 if has_urgency else 1.0

    keyword_score = 0
    keyword_hits = []
    for phrase, base in SCAM_WEIGHTS.items():
        if phrase in lower:
            awarded = int(base * urgency_multiplier)
            keyword_score += awarded
            keyword_hits.append(f"{phrase}(+{awarded})")

    # Also catch any phrases not in weighted dict
    extra_hits = [p for p in SCAM_PHRASES if p not in SCAM_WEIGHTS and p in lower]
    if extra_hits:
        extra = int(8 * urgency_multiplier)
        keyword_score += len(extra_hits) * extra
        keyword_hits.extend(extra_hits[:3])

    if keyword_hits:
        score += min(45, keyword_score)
        reasons.append(f"Scam phrases detected: {', '.join(keyword_hits[:5])}")

    if has_urgency:
        u_hits = [w for w in URGENCY_PHRASES if w in lower]
        score += min(15, len(u_hits) * 5)
        reasons.append(f"Urgency pressure (1.5x multiplier active): {', '.join(u_hits[:3])}")

    # ── Vector DB similarity ────────────────────────────────────────────────
    if vector_db:
        try:
            similar = vector_db.query_similarity(transcript, n_results=3)
            if similar:
                top = similar[0]
                sim_pct = top["similarity_pct"]
                if sim_pct > 55:
                    score += min(30, sim_pct * 0.4)
                    reasons.append(
                        f"Matches known scam transcript ({sim_pct:.0f}% similar): "
                        f"\"{top['template'][:60]}...\""
                    )
        except Exception:
            pass

    # ── PII scrub before sending to Claude ─────────────────────────────────
    safe_transcript = scrub_pii(transcript[:1000])

    # ── Groq Llama intent classification ─────────────────────────────────────
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            client = Groq(api_key=groq_key)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=200,
                messages=[
                    {"role": "system", "content": VOICE_NLP_SYSTEM},
                    {"role": "user", "content": f"Analyze this call transcript:\n\n{safe_transcript}"},
                ],
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0]
            data = json.loads(raw)
            nlp_score = float(data.get("confidence", 0))
            if data.get("is_scam") or nlp_score > 30:
                score += min(40, nlp_score * 0.5)
                intent = data.get("intent", "unknown")
                reasoning = data.get("reasoning", "")
                reasons.append(f"[NLP] {intent.replace('_', ' ').title()}: {reasoning}")
        except Exception as e:
            reasons.append(f"NLP skipped: {str(e)[:60]}")

    return min(score, 85.0), reasons


# ── Layer 3: Deepfake Voice Detection ───────────────────────────────────────

def deepfake_detection(audio_bytes: bytes, filename: str) -> Tuple[float, List[str]]:
    """
    Spectral physics analysis — no training dataset needed.
    AI/cloned voices physically cannot replicate:
    - Natural spectral noise (spectral flatness)
    - Micro pitch instability (F0 jitter)
    - Chaotic speech texture (MFCC variance)
    - Natural zero-crossing fluctuation (ZCR std)

    Also catches voice cloning (3-second clone):
    - Cloned voices have overly consistent spectral envelopes
    - Lack the natural pitch shifts a distressed real person would have
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        return 0.0, ["librosa not installed – deepfake detection skipped"]

    reasons = []
    score = 0.0

    try:
        suffix = os.path.splitext(filename)[-1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        y, sr = librosa.load(tmp_path, sr=None, mono=True)
        os.unlink(tmp_path)

        # Preprocess to avoid false positives from GSM compression
        y, sr = preprocess_audio(y, sr)

        # Spectral flatness – AI voices are too spectrally smooth
        # Phone audio (8kHz mulaw) is naturally flat — threshold raised significantly
        flatness = librosa.feature.spectral_flatness(y=y)[0]
        mean_flatness = float(flatness.mean())
        if mean_flatness > 0.35:  # calibrated for phone audio (was 0.15 — caused false positives)
            score += 25
            reasons.append(
                f"High spectral flatness ({mean_flatness:.3f}) – synthetic/cloned voice indicator"
            )

        # ZCR std – AI voices have unnaturally consistent zero-crossings
        # Phone audio naturally has lower ZCR variation — threshold tightened
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        zcr_std = float(zcr.std())
        if zcr_std < 0.005:  # calibrated for phone audio (was 0.01)
            score += 20
            reasons.append("Unnaturally consistent zero-crossing rate – deepfake marker")

        # MFCC variance – AI voices lack natural speech texture
        # 8kHz audio has compressed MFCC naturally — threshold lowered
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_var = float(mfccs.var(axis=1).mean())
        if mfcc_var < 3:  # calibrated for phone audio (was 10 — flagged all phone calls)
            score += 20
            reasons.append(f"Low MFCC variance ({mfcc_var:.1f}) – lacks natural speech texture")

        # F0 jitter – natural voices wobble slightly every pitch cycle
        # Voice clones are unnaturally stable even when "distressed"
        f0, _, _ = librosa.pyin(
            y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7')
        )
        f0_clean = f0[~np.isnan(f0)]
        if len(f0_clean) > 10:
            jitter = float(np.diff(f0_clean).std())
            if jitter < 0.5:  # calibrated for phone audio (was 2.0 — too sensitive on GSM)
                score += 20
                reasons.append(
                    f"Very low F0 jitter ({jitter:.2f} Hz) – unnaturally stable pitch "
                    f"(human baseline: 4-8 Hz) — voice clone marker"
                )

        # Spectral envelope consistency — 3-second clones repeat spectral patterns
        # Phone audio centroids naturally narrow due to 8kHz bandwidth limit
        spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        centroid_std = float(spec_centroid.std())
        if centroid_std < 80 and len(spec_centroid) > 20:  # calibrated (was 200 — wrong for phone)
            score += 15
            reasons.append(
                f"Unnaturally consistent spectral envelope (std: {centroid_std:.0f} Hz) – "
                f"voice cloning artifact"
            )

    except Exception as e:
        reasons.append(f"Deepfake detection error: {str(e)[:80]}")

    return min(score, 80.0), reasons


# ── Main Detector ───────────────────────────────────────────────────────────

class VoiceDetector:
    def __init__(self, vector_db: VectorDB = None):
        self.vector_db = vector_db

    def analyze(
        self,
        audio_bytes: bytes,
        filename: str,
        customer_id: str = None,
        include_spectrogram: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the four-layer voice analysis pipeline.

        Parameters
        ----------
        audio_bytes : bytes
            Raw audio file bytes.
        filename : str
            Original filename (used for format detection).
        customer_id : str, optional
            If provided, run speaker verification (Layer 4) against the
            enrolled voice profile for this customer.  A low similarity
            score (possible impersonation) raises the final risk score.
        include_spectrogram : bool, optional (default True)
            When True, generates a mel-spectrogram PNG and embeds it as a
            base64 data URI in the response under ``spectrogram_image``.
            Set to False for high-throughput pipelines (e.g. live call chunks)
            where speed matters more than visualization.
        """
        reasons = []

        # Layer 1 – Acoustics (includes boiler room + GSM preprocessing)
        a_score, a_reasons = acoustic_analysis(audio_bytes, filename)
        reasons.extend(a_reasons)

        # Layer 2 – Transcript → keyword + vector + PII scrub + Claude NLP
        transcript = transcribe(audio_bytes, filename)
        n_score, n_reasons = nlp_on_transcript(transcript, vector_db=self.vector_db)
        reasons.extend(n_reasons)

        # Layer 3 – Deepfake / voice clone detection
        d_score, d_reasons = deepfake_detection(audio_bytes, filename)
        reasons.extend(d_reasons)

        # Weighted combination (speaker verification score blended in below)
        final = (a_score * 0.25) + (n_score * 0.45) + (d_score * 0.30)

        # ── Deepfake Override Rule ───────────────────────────────────────────
        # If spectral analysis is highly confident this is AI-generated/cloned,
        # override the final score to HIGH RISK regardless of semantic layer.
        # A legitimate caller will NEVER use a cloned voice.
        is_deepfake = d_score > 40
        if d_score > 70:
            final = max(final, 85.0)
            reasons.insert(0,
                "OVERRIDE: High-confidence AI voice clone detected — "
                "automatic HIGH RISK (spectral physics confirm synthetic generation)"
            )

        # ── Layer 4 – Speaker Verification (optional) ────────────────────────
        speaker_match_score: float = None
        speaker_verified: bool = None
        speaker_error: str = None

        if customer_id:
            try:
                from core.speaker_verification import verify_speaker, is_enrolled

                if not is_enrolled(customer_id):
                    speaker_error = (
                        f"No enrolled voice profile found for customer '{customer_id}'. "
                        f"Enroll via POST /enroll-voice first."
                    )
                    reasons.append(f"[Speaker] {speaker_error}")
                else:
                    similarity, is_match = verify_speaker(
                        customer_id, audio_bytes, filename
                    )
                    speaker_match_score = round(similarity, 4)
                    speaker_verified = is_match

                    if not is_match:
                        # Dissimilar voice = possible impersonation risk.
                        # Weight: inverse of similarity scaled to [0, 40] range.
                        # At similarity=0.0 → adds 40 pts; at 0.74 → adds ~1 pt.
                        impersonation_penalty = round(
                            (1.0 - similarity) * 40.0, 1
                        )
                        final = min(100.0, final + impersonation_penalty)
                        reasons.append(
                            f"Voice does not match enrolled customer profile "
                            f"(similarity: {similarity * 100:.1f}%) — "
                            f"possible impersonation (+{impersonation_penalty:.0f} risk pts)"
                        )
                    else:
                        reasons.append(
                            f"Voice matches enrolled customer profile "
                            f"(similarity: {similarity * 100:.1f}%) — identity confirmed"
                        )

            except FileNotFoundError as e:
                speaker_error = str(e)
                reasons.append(f"[Speaker] {speaker_error}")
            except RuntimeError as e:
                # Model not installed / load failure — don't crash the pipeline
                speaker_error = str(e)
                reasons.append(f"[Speaker] Verification unavailable: {speaker_error[:120]}")
            except Exception as e:
                speaker_error = f"Unexpected error in speaker verification: {str(e)[:120]}"
                reasons.append(f"[Speaker] {speaker_error}")

        raw: Dict[str, Any] = {
            "transcript": transcript[:500] if transcript else "",
            "acoustic_score": round(a_score, 1),
            "nlp_score": round(n_score, 1),
            "deepfake_score": round(d_score, 1),
            "is_deepfake": is_deepfake,
            "deepfake_override": d_score > 70,
        }

        if customer_id is not None:
            raw["customer_id"] = customer_id
            raw["speaker_match_score"] = speaker_match_score
            raw["speaker_verified"] = speaker_verified
            if speaker_error:
                raw["speaker_error"] = speaker_error

        result = ThreatScore.build(
            score=final,
            reasons=reasons,
            source="voice",
            raw=raw,
        )

        # ── Spectrogram visualization (optional) ─────────────────────────────
        # Generated AFTER scoring so it never affects the risk calculation.
        if include_spectrogram:
            try:
                from core.spectrogram_generator import generate_spectrogram_image
                result["spectrogram_image"] = generate_spectrogram_image(
                    audio_bytes, filename
                )
            except Exception:
                result["spectrogram_image"] = None
        else:
            result["spectrogram_image"] = None

        return result
